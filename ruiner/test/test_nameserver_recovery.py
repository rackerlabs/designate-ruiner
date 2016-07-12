from ruiner.common import utils
from ruiner.test import base

LOG = utils.create_logger(__name__)


class TestNameserverRecovery(base.BaseTest):

    def setUp(self):
        super(TestNameserverRecovery, self).setUp()
        LOG.info("======== test start ========")

    def tearDown(self):
        self.docker_composer.unpause("bind-2")
        super(TestNameserverRecovery, self).tearDown()

    def test_create_zone_while_nameserver_is_down(self):
        """Create a zone while a nameserver is down. Check the zone goes to
        ERROR. Bring the nameserver back up. Check the zone goes to ACTIVE.
        """
        self.kill_nameserver()
        name, zid = self.create_zone()
        self.wait_for_zone_to_error(name, zid)
        self.restart_nameserver()
        self.wait_for_zone_to_active(name, zid)

    def test_delete_zone_while_nameserver_is_down(self):
        """Delete a zone while a nameserver is down. Check the zone goes to
        ERROR. Bring the nameserver back up. Check the zone 404s.
        """
        name, zid = self.create_zone()
        self.wait_for_zone_to_active(name, zid)
        self.kill_nameserver()
        self.delete_zone(name, zid)
        self.wait_for_zone_to_error(name, zid)
        self.restart_nameserver()
        self.wait_for_zone_to_404(name, zid)

    def test_create_recordset_while_nameserver_is_down(self):
        """Create a recordset while a nameserver is down. Check the zone goes
        to ERROR. Bring the nameserver up. Check the zone goes to ACTIVE.
        """
        zname, zid = self.create_zone()
        self.wait_for_zone_to_active(zname, zid)
        self.kill_nameserver()
        rrname, rrid = self.create_recordset(zname, zid)
        self.wait_for_zone_to_error(zname, zid)
        self.restart_nameserver()
        self.wait_for_zone_to_active(zname, zid)
