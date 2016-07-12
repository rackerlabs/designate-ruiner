import time
import unittest
import tempfile
import os
import shutil

import dns.exception
import jinja2

from ruiner.common import designate
from ruiner.common import docker
from ruiner.common import utils
from ruiner.common import waiters
from ruiner.common.config import cfg
from ruiner.common.ini import IniFile

LOG = utils.create_logger(__name__)


class DockerComposeYamlTemplate(object):
    """A tool to generate a designate.yml for docker-compose"""

    def __init__(self, tag=None):
        self.source_template = './ruiner/templates/designate.yml.jinja2'
        self.output_file = utils.new_temp_file(self._filetag(tag), ".yml")
        LOG.debug("using designate.yml generated at %s", self.output_file)

    def render(self, **kwargs):
        templ = jinja2.Template(open(self.source_template).read())
        content = templ.render(**kwargs)
        with open(self.output_file, 'w') as f:
            f.write(content)
        LOG.debug("%s has content:\n%s", self.output_file, content)

    def _filetag(self, tag):
        if tag:
            return "designate-%s-" % tag
        return "designate-"


class BaseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseTest, cls).setUpClass()
        cls.interval = cfg.CONF.ruiner.interval
        cls.timeout = cfg.CONF.ruiner.timeout

    def setUp(self):
        LOG.info("======== base class setup ========")
        super(BaseTest, self).setUp()

        self.random_tag = utils.random_tag()

        self.setup_log_dir()

        self.carina_dir = docker.discover_designate_carina_dir()
        self.project_name = utils.random_project_name(tag=self.random_tag)

        self.init_tmp_dir()
        self.init_designate_conf()
        self.init_docker_compose_yaml()

        # this can be overridden in subclasses to configure designate however
        self.configure_designate_conf()
        self.show_designate_conf()

        self.docker_composer = docker.DockerComposer(
            compose_files=[
                "base.yml", self.designate_yaml, "envs/slappy-bind/bind.yml",
            ],
            project_name=self.project_name,
            carina_dir=self.carina_dir,
        )

        self.deploy_environment()
        self.discover_services()
        self.prechecks()

    def tearDown(self):
        LOG.info("======== base class teardown ========")
        self.show_docker_logs()
        self.cleanup_environment()
        self.summarize()
        super(BaseTest, self).tearDown()

    def summarize(self):
        LOG.info("======== SUMMARY ========")
        tag = getattr(self, 'random_tag', 'N/A')
        log_dir = getattr(self, 'log_dir', 'N/A')
        services_logfile = getattr(self, 'docker_logs_file', 'N/A')
        designate_git_url = cfg.CONF.ruiner.designate_git_url
        designate_version = cfg.CONF.ruiner.designate_version

        LOG.info("tag . . . . . . . . . . : %s", tag)
        LOG.info("log_dir . . . . . . . . : %s", log_dir)
        LOG.info("service log . . . . . . : %s", services_logfile)
        LOG.info("designate_git_url . . . : %s", designate_git_url)
        LOG.info("designate_version . . . : %s", designate_version)

    def configure_designate_conf(self):
        """This method may be overridden by subclasses. You MUST do all
        customization of self.designate_conf in this method, so that the file
        is prepared before the images are built.
        """
        LOG.info("======== configuring designate.conf ========")
        conf = IniFile(self.designate_conf)
        conf.set("service:worker", "poll_timeout", 2)
        conf.set("service:worker", "poll_retry_interval", 2)
        conf.set("service:worker", "poll_max_retries", 2)
        conf.set("service:worker", "poll_delay", 2)

    def setup_log_dir(self):
        base_dir = os.path.realpath(cfg.CONF.ruiner.log_dir.rstrip('/'))
        self.log_dir = os.path.join(base_dir, self.random_tag)
        utils.mkdirs(self.log_dir)

    def init_tmp_dir(self):
        """There are some docker env config files we'll create dynamically.
        This is a temporary directory to hold all files created by the tests.
        """
        # since COPY in a dockerfile doesn't work with absolute paths, we need
        # to create temp files in a place docker will find them.
        tempfile.tempdir = os.path.join(self.carina_dir, 'tmp')
        try:
            os.mkdir(tempfile.tempdir)
        except OSError:
            pass
        self.tempdir = tempfile.tempdir

    def init_designate_conf(self):
        """Create a designate.conf for use by the current test. This will be a
        randomized filename stored at self.designate_conf.
        """
        filetag = "designate-%s-" % self.random_tag
        self.designate_conf = utils.new_temp_file(filetag, ".conf")
        self.addCleanup(utils.cleanup_file, self.designate_conf)
        LOG.debug("using designate.conf generated at %s", self.designate_conf)

        # initialize designate.conf to some defaults
        src_path = os.path.join(
            self.carina_dir, "envs/slappy-bind/designate.conf",
        )
        shutil.copyfile(src_path, self.designate_conf)

    def show_designate_conf(self):
        LOG.debug("designate.conf is at %r:\n%s", self.designate_conf,
                  open(self.designate_conf, 'r').read())

    def init_docker_compose_yaml(self):
        # the docker compose yaml does not work with absolute paths
        designate_conf = os.path.relpath(self.designate_conf, self.carina_dir)

        templ = DockerComposeYamlTemplate(tag=self.random_tag)
        templ.render(
            DESIGNATE_GIT_URL=cfg.CONF.ruiner.designate_git_url,
            DESIGNATE_VERSION=cfg.CONF.ruiner.designate_version,
            DESIGNATE_CONF=designate_conf,
            POOLS_YAML='envs/slappy-bind/pools.yml',
            RUINER_PROJECT=self.project_name,
        )
        self.designate_yaml = templ.output_file
        self.addCleanup(utils.cleanup_file, self.designate_yaml)

    def discover_services(self):
        LOG.info("======== discover service locations ========")
        self.api = designate.API(
            "http://%s" % self.docker_composer.get_host("api", 9001)
        )
        LOG.info("api: %s", self.api.endpoint)

        self.bind1 = self.docker_composer.get_host("bind-1", 53, "udp")
        LOG.info("bind-1: %s", self.bind1)

        self.bind2 = self.docker_composer.get_host("bind-2", 53, "udp")
        LOG.info("bind-2: %s", self.bind2)

    def deploy_environment(self):
        LOG.info("======== deploying env (%s) ========", self.project_name)
        out, _, ret = self.docker_composer.build()
        LOG.debug("stdout:\n%s", out)
        self.assertEqual(ret, 0)

        out, _, ret = self.docker_composer.up()
        LOG.debug("stdout:\n%s", out)
        self.assertEqual(ret, 0)

        sleep_time = cfg.CONF.ruiner.service_startup_wait_time
        LOG.info("waiting %s seconds for services to start up", sleep_time)
        time.sleep(sleep_time)

    def cleanup_environment(self):
        LOG.info("======== cleaning up env (%s) ========", self.project_name)
        _, _, ret = self.docker_composer.down()
        if ret != 0:
            LOG.error("FAILED TO CLEANUP ENV (project=%s)", self.project_name)
            LOG.error("TRY `docker-compose -p %s down`", self.project_name)
        self.assertEqual(
            ret, 0, "FAILED TO CLEANUP ENV (project=%s)" % self.project_name
        )

    def prechecks(self):
        """Do quick checks of the api + nameservers"""
        LOG.info("======== checking environment preconditions ========")
        LOG.info("checking the api by listing zones")
        resp = self.api.list_zones()
        LOG.debug(utils.resp_to_string(resp))
        assert resp.ok

        # these digs raise exceptions on timeouts
        LOG.info("checking bind-1 by digging it")
        utils.dig("poo.com.", self.bind1, "ANY")

        LOG.info("checking bind-2 by digging it")
        utils.dig("poo.com.", self.bind2, "ANY")

        LOG.info("all prechecks have passed!")

    def kill_nameserver(self):
        """Stop a nameservers, causing new operations to go to error"""
        self.docker_composer.pause("bind-2")

        LOG.debug("checking bind-2 is down")
        try:
            utils.dig("poo.com.", self.bind2, "ANY")
        except dns.exception.Timeout:
            LOG.debug("verified bind-2 is down (query timed out)")
        else:
            self.fail("failed to pause container bind-2")

    def restart_nameserver(self):
        utils.require_success(self.docker_composer.unpause("bind-2"))

    def show_docker_logs(self):
        out, err, ret = self.docker_composer.logs()

        self.docker_logs_file = os.path.realpath(
            os.path.join(self.log_dir, 'docker-services.log'),
        )
        LOG.info("writing docker service logs to: %s", self.docker_logs_file)
        with open(self.docker_logs_file, 'w') as f:
            f.write("stdout:\n%s" % utils.strip_ansi(out))
            f.write("stderr:\n%s" % utils.strip_ansi(err))

        if ret != 0:
            LOG.error("failed to get docker logs!")
            LOG.error("stderr: %s", err)

    def create_zone(self):
        """Create a zone. Return (name, zone_id) on success, or self.fail()"""
        LOG.info("creating a zone")
        resp = self.api.create_zone()
        LOG.debug(utils.resp_to_string(resp))
        if resp.status_code != 202:
            self.fail("failed to create zone (status=%s)" % resp.status_code)
        return resp.json()["name"], resp.json()["id"]

    def delete_zone(self, name, zid):
        """Delete a zone. Calls self.fail() if the delete fails"""
        LOG.info("deleting zone %s", name)
        resp = self.api.delete_zone(zid)
        if not resp.ok:
            self.fail("failed to delete zone %s", name)
        LOG.debug(utils.resp_to_string(resp))

    def create_recordset(self, zname, zid):
        """Create a recordset. Return (rrname, rrid) on success, or else
        self.fail()"""
        LOG.info("creating a recordset")
        resp = self.api.create_recordset(zname, zid)
        LOG.debug(utils.resp_to_string(resp))
        if resp.status_code != 202:
            self.fail("failed to create recordset (status=%s)"
                      % resp.status_code)
        return resp.json()['name'], resp.json()['id']

    def wait_for_zone_to_error(self, name, zid):
        """Wait for the given zone to go to ERROR. Fail the test if we fail to
        timeout before seeing an ERROR status.
        """
        LOG.info("waiting for zone %s to go to ERROR...", name)
        resp = waiters.wait_for_status(
            lambda: self.api.get_zone(zid), ["ERROR", "ACTIVE"], self.interval,
            self.timeout,
        )

        if resp.ok and resp.json()['status'] == 'ERROR':
            LOG.info("...done waiting for zone %s (status = ERROR)", name)
        else:
            LOG.error("...done waiting for zone %s (status != ERROR)", name)

        LOG.debug(utils.resp_to_string(resp))
        self.assertEqual(
            resp.json().get("status"), "ERROR",
            "zone %s failed to go to ERROR (timeout=%s)" % (name, self.timeout)
        )

    def wait_for_zone_to_active(self, name, zid):
        """Wait for the given zone to go to ACTIVE. Fail the test if we timeout
        before seeing an ACTIVE status.
        """
        LOG.info("waiting for zone %s to go to ACTIVE...", name)
        resp = waiters.wait_for_status(
            lambda: self.api.get_zone(zid), ["ACTIVE"], self.interval,
            self.timeout
        )

        if resp.ok and resp.json()['status'] == 'ACTIVE':
            LOG.info("...done waiting for zone %s (status = ACTIVE)", name)
        else:
            LOG.error("...done waiting for zone %s (status != ACTIVE)", name)

        LOG.debug(utils.resp_to_string(resp))
        self.assertEqual(
            resp.json().get("status"), "ACTIVE",
            "zone %s failed to go ACTIVE (timeout=%s)" % (name, self.timeout)
        )

    def wait_for_zone_to_404(self, name, zid):
        """Wait for the given zone to return a 404. Fail the test if we timeout
        before seeing a 404 status code.
        """
        LOG.info("waiting for zone %s to 404...", name)
        resp = waiters.wait_for_404(
            lambda: self.api.get_zone(zid), self.interval, self.timeout,
        )

        if resp.status_code == 404:
            LOG.info("...done waiting for zone %s (status = 404)", name)
        else:
            LOG.error("...done waiting for zone %s (status != 404)", name)

        LOG.debug(utils.resp_to_string(resp))
        self.assertEqual(
            resp.status_code, 404,
            "zone %s failed to 404 (timeout=%s)" % (name, self.timeout)
        )
