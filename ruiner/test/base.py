import unittest

import dns.exception

import designate
import docker
import utils
import waiters

LOG = utils.create_logger(__name__)


class BaseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        LOG.info("======== base class setup ========")
        super(BaseTest, cls).setUpClass()
        cls.docker_composer = docker.DockerComposer()

        cls.api = designate.API(
            "http://%s" % cls.docker_composer.get_host("api", 9001)
        )
        LOG.info("api: %s", cls.api.endpoint)

        cls.bind1 = cls.docker_composer.get_host("bind-1", 53, "udp")
        LOG.info("bind-1: %s", cls.bind1)

        cls.bind2 = cls.docker_composer.get_host("bind-2", 53, "udp")
        LOG.info("bind-2: %s", cls.bind2)

    @classmethod
    def prechecks(cls):
        """Do quick checks of the api + nameservers"""
        LOG.info("======== checking environment preconditions ========")
        LOG.info("checking the api by listing zones")
        resp = cls.api.list_zones()
        LOG.debug(utils.resp_to_string(resp))
        assert resp.ok

        # these raise exceptions on timeouts
        LOG.info("checking bind-1 by digging it")
        utils.dig("poo.com.", cls.bind1, "ANY")

        LOG.info("checking bind-2 by digging it")
        utils.dig("poo.com.", cls.bind2, "ANY")

        LOG.info("all prechecks have passed!")

    def kill_nameserver(self):
        """Stop a nameservers, causing new operations to go to error"""
        self.docker_composer.pause("bind-2")

        LOG.debug("checking bind-2 is down")
        try:
            resp = utils.dig("poo.com.", self.bind2, "ANY")
        except dns.exception.Timeout as e:
            LOG.debug("verified bind-2 is down (query timed out)")
        else:
            self.fail("failed to pause container bind-2")

    def restart_nameserver(self):
        utils.require_success(self.docker_composer.unpause("bind-2"))

    def create_zone(self):
        """Create a zone. Return (name, zone_id) on success, or self.fail()"""
        LOG.info("creating a zone")
        resp = self.api.create_zone()
        LOG.debug(utils.resp_to_string(resp))
        if resp.status_code != 202:
            self.fail("failed to create zone (got status %s)" % resp.status_code)
        return resp.json()["name"], resp.json()["id"]

    def delete_zone(self, name, zid):
        """Delete a zone. Calls self.fail() if the delete fails"""
        LOG.info("deleting zone %s", name)
        resp = self.api.delete_zone(zid)
        if not resp.ok:
            self.fail("failed to delete zone %s", name)
        LOG.debug(utils.resp_to_string(resp))

    def wait_for_zone_to_error(self, name, zid, timeout=30):
        """Wait for the given zone to go to ERROR. Fail the test if we fail to
        timeout before seeing an ERROR status.
        """
        LOG.info("waiting for zone %s to go to ERROR...", name)
        resp = waiters.wait_for_status(
            lambda: self.api.get_zone(zid), ["ERROR", "ACTIVE"], timeout,
        )
        LOG.info("...done waiting for zone %s", name)
        LOG.debug(utils.resp_to_string(resp))
        if resp.json()["status"] != "ERROR":
            self.fail("zone %s failed to go to ERROR" % name)

    def wait_for_zone_to_active(self, name, zid, timeout=30):
        """Wait for the given zone to go to ACTIVE. Fail the test if we timeout
        before seeing an ACTIVE status.
        """
        LOG.info("waiting for zone %s to go to ACTIVE...", name)
        resp = waiters.wait_for_status(
            lambda: self.api.get_zone(zid), ["ACTIVE"], timeout,
        )
        LOG.info("...done waiting for zone %s", name)
        LOG.debug(utils.resp_to_string(resp))
        if resp.json()["status"] != "ACTIVE":
            self.fail("zone %s failed to go to ACTIVE" % name)

    def wait_for_zone_to_404(self, name, zid, timeout=30):
        """Wait for the given zone to return a 404. Fail the test if we timeout
        before seeing a 404 status code.
        """
        LOG.info("waiting for zone %s to 404...", name)
        resp = waiters.wait_for_404(lambda: self.api.get_zone(zid), timeout=60)
        LOG.info("...done waiting for zone %s", name)
        LOG.debug(utils.resp_to_string(resp))
        assert resp.status_code == 404
        if resp.status_code != 404:
            LOG.warning("resp.status_code is %s", resp.status_code)
            self.fail("zone %s failed to eventually 404" % name)
