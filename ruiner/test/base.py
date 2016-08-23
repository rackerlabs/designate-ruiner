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


class DockerComposeYamlTemplate(object):
    """A tool to generate a designate.yml for docker-compose"""

    def __init__(self, logger, tag=None):
        self.log = logger
        self.source_template = './ruiner/templates/designate.yml.jinja2'
        self.output_file = utils.new_temp_file(self._filetag(tag), ".yml")
        self.log.debug("using designate.yml generated at %s", self.output_file)

    def render(self, **kwargs):
        templ = jinja2.Template(open(self.source_template).read())
        content = templ.render(**kwargs)
        with open(self.output_file, 'w') as f:
            f.write(content)
        self.log.debug("%s has content:\n%s", self.output_file, content)

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
        cls.base_log_dir = utils.setup_log_dir()

    def setUp(self):
        super(BaseTest, self).setUp()
        self.log_dir = self.setup_log_dir()
        per_test_log_file = os.path.join(self.log_dir, 'master.log')
        self.log = utils.create_logger(self.id(), per_test_log_file)
        self.log.info("======== base setup ========")

    def setup_log_dir(self):
        log_dir = os.path.join(self.base_log_dir, self.id())
        utils.mkdirs(log_dir)
        return log_dir


class BaseDesignateTest(BaseTest):
    """This class deploys Designate into docker containers on test setup"""

    def setUp(self):
        super(BaseDesignateTest, self).setUp()
        self.log.info("======== base designate test setup ========")

        # a unique tag to ensure unique, per-test filenames
        self.random_tag = utils.random_tag()

        self.carina_dir = docker.discover_designate_carina_dir()
        self.project_name = utils.random_project_name(tag=self.random_tag)

        self.init_tmp_dir()
        self.init_designate_conf()
        self.init_docker_compose_yaml()

        # this can be overridden in subclasses to configure designate however
        self.configure_designate_conf()
        self.show_designate_conf()

        self.docker_composer = docker.DockerComposer(
            logger=self.log,
            compose_files=[
                "base.yml", self.designate_yaml, "envs/slappy-bind/bind.yml",
            ],
            project_name=self.project_name,
            carina_dir=self.carina_dir,
        )

        self.deploy_environment()
        self.services = self.discover_services()
        self.prechecks()

        self.log.info("======== test start ========")

    def tearDown(self):
        self.log.info("======== base designate test teardown ========")
        self.show_docker_logs()
        self.store_configs()
        self.cleanup_environment()
        self.summarize()
        super(BaseTest, self).tearDown()

    def summarize(self):
        self.log.info("======== SUMMARY ========")
        tag = getattr(self, 'random_tag', 'N/A')
        log_dir = getattr(self, 'log_dir', 'N/A')
        services_logfile = getattr(self, 'docker_logs_file', 'N/A')
        designate_git_url = cfg.CONF.ruiner.designate_git_url
        designate_version = cfg.CONF.ruiner.designate_version

        self.log.info("tag . . . . . . . . . . : %s", tag)
        self.log.info("log_dir . . . . . . . . : %s", log_dir)
        self.log.info("service log . . . . . . : %s", services_logfile)
        self.log.info("designate_git_url . . . : %s", designate_git_url)
        self.log.info("designate_version . . . : %s", designate_version)

    def configure_designate_conf(self):
        """This method may be overridden by subclasses. You MUST do all
        customization of self.designate_conf in this method, so that the file
        is prepared before the images are built.
        """
        self.log.info("======== configuring designate.conf ========")
        conf = IniFile(self.designate_conf)
        conf.set("DEFAULT", "debug", True)
        conf.set("service:worker", "poll_timeout", 2)
        conf.set("service:worker", "poll_retry_interval", 2)
        conf.set("service:worker", "poll_max_retries", 2)
        conf.set("service:worker", "poll_delay", 2)

        conf.set("producer_task:worker_periodic_recovery", "interval", 30)

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
        self.log.debug("using designate.conf generated at %s",
                       self.designate_conf)

        # initialize designate.conf to some defaults
        src_path = os.path.join(
            self.carina_dir, "envs/slappy-bind/designate.conf",
        )
        shutil.copyfile(src_path, self.designate_conf)

    def show_designate_conf(self):
        self.log.debug("designate.conf is at %r:\n%s", self.designate_conf,
                       open(self.designate_conf, 'r').read())

    def init_docker_compose_yaml(self):
        # the docker compose yaml does not work with absolute paths
        designate_conf = os.path.relpath(self.designate_conf, self.carina_dir)

        templ = DockerComposeYamlTemplate(self.log, tag=self.random_tag)
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
        """Discover docker service locations (url, host:port) and return a dict
        mapping the docker service name to the location"""
        self.log.info("======== discover service locations ========")
        services = {
            'api': self.discover_api(),
            'bind-1': self.discover_nameserver('bind-1'),
            'bind-2': self.discover_nameserver('bind-2'),
        }
        self.api = designate.API(services['api'])
        return services

    def discover_api(self, service_name='api', port=9001):
        url = "http://%s" % self.docker_composer.get_host(service_name, port)
        self.log.info("%s:%s -> %s", service_name, port, url)
        return url

    def discover_nameserver(self, service_name, port=53, protocol='udp'):
        location = self.docker_composer.get_host(service_name, port, protocol)
        self.log.info("%s:%s/%s -> %s", service_name, port, protocol, location)
        return location

    def deploy_environment(self):
        self.log.info("======== deploying env (%s) ========",
                      self.project_name)
        out, _, ret = self.docker_composer.build()
        self.log.debug("stdout:\n%s", out)
        self.assertEqual(ret, 0)

        out, _, ret = self.docker_composer.up()
        self.log.debug("stdout:\n%s", out)
        self.assertEqual(ret, 0)

        sleep_time = cfg.CONF.ruiner.service_startup_wait_time
        self.log.info("waiting %s seconds for services to start up",
                      sleep_time)
        time.sleep(sleep_time)

    def cleanup_environment(self):
        self.log.info("======== cleaning up env (%s) ========",
                      self.project_name)
        _, _, ret = self.docker_composer.down()
        if ret != 0:
            self.log.error("FAILED TO CLEANUP ENV (project=%s)",
                           self.project_name)
            self.log.error("try `docker-compose -p %s down`",
                           self.project_name)
        self.assertEqual(
            ret, 0, "FAILED TO CLEANUP ENV (project=%s)" % self.project_name
        )

    def prechecks(self):
        """Do quick checks of the api + nameservers"""
        self.log.info("======== checking environment preconditions ========")
        self.log.info("checking the api by listing zones")
        resp = self.api.list_zones()
        self.log.debug(utils.resp_to_string(resp))
        assert resp.ok

        # these queries raise exceptions on timeouts
        for service_name in ('bind-1', 'bind-2'):
            self.log.info("checking %s by digging it", service_name)
            resp = utils.dig("poo.com.", self.services[service_name], "ANY")
            self.log.debug("\n%s", resp)

        self.log.info("all prechecks have passed!")

    def kill_nameserver(self, service_name='bind-2'):
        """Stop a nameserver, causing new operations to go to error"""
        self.docker_composer.kill(service_name)
        if not self.nameserver_is_down(service_name):
            self.log.debug("failed to kill container %s", service_name)

    def restart_nameserver(self, service_name='bind-2'):
        utils.require_success(self.docker_composer.start(service_name))

        # a container (likely) gets a new port when it is restarted
        location = self.discover_nameserver(service_name)
        self.services[service_name] = location

        sleep_time = cfg.CONF.ruiner.service_startup_wait_time
        self.log.info("waiting %s seconds for %s to start up", sleep_time,
                      service_name)
        time.sleep(sleep_time)

    def nameserver_is_down(self, service_name='bind-2'):
        """Return True if the nameserver does not respond to queries"""
        self.log.debug("checking %s is down", service_name)
        host = self.services[service_name]
        try:
            utils.dig("poo.com.", host, "ANY")
        except dns.exception.Timeout:
            self.log.debug("verified %s is down (query to %s timed out)",
                           service_name, host)
            return True
        return False

    def show_docker_logs(self):
        out, err, ret = self.docker_composer.logs()

        self.docker_logs_file = os.path.realpath(
            os.path.join(self.log_dir, 'docker-services.log'),
        )
        self.log.info("writing docker service logs to: %s",
                      self.docker_logs_file)
        with open(self.docker_logs_file, 'w') as f:
            f.write("stdout:\n%s" % utils.strip_ansi(out))
            f.write("stderr:\n%s" % utils.strip_ansi(err))

        if ret != 0:
            self.log.error("failed to get docker logs!")
            self.log.error("stderr: %s", err)

    def store_configs(self):
        shutil.copyfile(self.designate_conf,
                        os.path.join(self.log_dir, 'designate.conf'))
        shutil.copyfile(self.designate_yaml,
                        os.path.join(self.log_dir, 'designate.yaml'))

    def get_zone(self, name, zid):
        """Fetch the zone. Return the response. self.fail() on status >= 500"""
        self.log.info("fetching zone %s (id=%s)", name, zid)
        resp = self.api.get_zone(zid)
        self.log.debug(utils.resp_to_string(resp))
        if resp.status_code >= 500:
            self.fail("failed to fetch zone (status=%s)" % resp.status_code)
        return resp

    def create_zone(self):
        """Create a zone. Return (name, zone_id) on success, or self.fail()"""
        self.log.info("creating a zone")
        resp = self.api.create_zone()
        self.log.debug(utils.resp_to_string(resp))
        if resp.status_code != 202:
            self.fail("failed to create zone (status=%s)" % resp.status_code)
        return resp.json()["name"], resp.json()["id"]

    def delete_zone(self, name, zid):
        """Delete a zone. Calls self.fail() if the delete fails"""
        self.log.info("deleting zone %s", name)
        resp = self.api.delete_zone(zid)
        if not resp.ok:
            self.fail("failed to delete zone %s", name)
        self.log.debug(utils.resp_to_string(resp))

    def create_recordset(self, zname, zid):
        """Create a recordset. Return (rrname, rrid) on success, or else
        self.fail()"""
        self.log.info("creating a recordset")
        resp = self.api.create_recordset(zname, zid)
        self.log.debug(utils.resp_to_string(resp))
        if resp.status_code != 202:
            self.fail("failed to create recordset (status=%s)"
                      % resp.status_code)
        return resp.json()['name'], resp.json()['id']

    def wait_for_zone_to_error(self, name, zid):
        """Wait for the given zone to go to ERROR. Fail the test if we fail to
        timeout before seeing an ERROR status.
        """
        self.log.info("waiting for zone %s to go to ERROR...", name)
        resp = waiters.wait_for_status(
            lambda: self.api.get_zone(zid), ["ERROR", "ACTIVE"], self.interval,
            self.timeout,
        )

        if resp.ok and resp.json()['status'] == 'ERROR':
            self.log.info("...done waiting for zone %s (status = ERROR)", name)
        else:
            self.log.error("...done waiting for zone %s (status != ERROR)",
                           name)

        self.log.debug(utils.resp_to_string(resp))
        self.assertEqual(
            resp.json().get("status"), "ERROR",
            "zone %s failed to go to ERROR (timeout=%s)" % (name, self.timeout)
        )

    def wait_for_zone_to_active(self, name, zid):
        """Wait for the given zone to go to ACTIVE. Fail the test if we timeout
        before seeing an ACTIVE status.
        """
        self.log.info("waiting for zone %s to go to ACTIVE...", name)
        resp = waiters.wait_for_status(
            lambda: self.api.get_zone(zid), ["ACTIVE"], self.interval,
            self.timeout
        )

        if resp.ok and resp.json()['status'] == 'ACTIVE':
            self.log.info("...done waiting for zone %s (status = ACTIVE)",
                          name)
        else:
            self.log.error("...done waiting for zone %s (status != ACTIVE)",
                           name)

        self.log.debug(utils.resp_to_string(resp))
        self.assertEqual(
            resp.json().get("status"), "ACTIVE",
            "zone %s failed to go ACTIVE (timeout=%s)" % (name, self.timeout)
        )

    def wait_for_zone_to_404(self, name, zid):
        """Wait for the given zone to return a 404. Fail the test if we timeout
        before seeing a 404 status code.
        """
        self.log.info("waiting for zone %s to 404...", name)
        resp = waiters.wait_for_404(
            lambda: self.api.get_zone(zid), self.interval, self.timeout,
        )

        if resp.status_code == 404:
            self.log.info("...done waiting for zone %s (status = 404)", name)
        else:
            self.log.error("...done waiting for zone %s (status != 404)", name)

        self.log.debug(utils.resp_to_string(resp))
        self.assertEqual(
            resp.status_code, 404,
            "zone %s failed to 404 (timeout=%s)" % (name, self.timeout)
        )

    def wait_for_name_on_nameserver(self, name, service_name):
        """Wait for a successful, non-empty response from the nameserver"""
        self.log.info("waiting for %s to go live on nameserver %s...", name,
                      service_name)

        host = self.services[service_name]
        resp = waiters.wait_for_name_on_nameserver(
            name, host, self.interval, self.timeout,
        )

        if bool(resp.answer):
            self.log.info("...done waiting for %s on nameserver %s (found)",
                          name, service_name)
        else:
            self.log.error(
                "...done waiting for %s on nameserver %s (not found)",
                name, service_name,
            )
        self.log.debug("\n%s", resp)

        self.assertTrue(
            bool(resp.answer),
            "zone %s never showed up on nameserver %s (timeout=%s)" % (
                name, service_name, self.timeout
            ),
        )

    def wait_for_name_removed_from_nameserver(self, name, service_name):
        self.log.info("waiting for %s to be removed from nameserver %s", name,
                      service_name)

        host = self.services[service_name]
        resp = waiters.wait_for_name_removed_from_nameserver(
            name, host, self.interval, self.timeout,
        )

        if not bool(resp.answer):
            self.log.info(
                "...done waiting for %s to be removed from nameserver %s",
                name, service_name,
            )
        else:
            self.log.error(
                "...done waiting for %s to be removed from nameserver %s"
                " (not removed)", name, service_name,
            )

        self.log.debug("\n%s", resp)
        self.assertFalse(
            bool(resp.answer),
            "zone %s never removed from nameserver %s (timeout=%s)" % (
                name, service_name, self.timeout,
            ),
        )
