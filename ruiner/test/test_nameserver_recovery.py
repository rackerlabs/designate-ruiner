from ruiner.common import utils
from ruiner.common.ini import IniFile
from ruiner.test import base

LOG = utils.create_logger(__name__)


class TestNameserverRecovery(base.BaseTest):

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


class TestThresholdPercentage(base.BaseTest):

    def configure_designate_conf(self):
        super(TestThresholdPercentage, self).configure_designate_conf()

        # with the threshold at 49%, only 1 of 2 nameservers needs a change
        # for the resource to go ACTIVE.
        self.threshold_percentage = 49

        conf = IniFile(self.designate_conf)
        conf.set("service:worker", "threshold_percentage",
                 self.threshold_percentage)
        conf.set("service:pool_manager", "threshold_percentage",
                 self.threshold_percentage)

    def test_recovery_of_zone_create_with_low_threshold_percentage(self):
        """Create a zone while a nameserver is down. Check that the zone gets
        to one nameserver and goes to active (due to the threshold percentage).
        Restore the nameserver. Check the zone gets to the second nameserver.
        """
        self.kill_nameserver('bind-2')

        # check that a zone goes to active and is really queryable on bind-1
        name, zid = self.create_zone()
        self.wait_for_zone_to_active(name, zid)
        self.wait_for_name_on_nameserver(name, 'bind-1')

        # restart the other nameserver. check the zone shows up there.
        self.restart_nameserver('bind-2')
        self.wait_for_name_on_nameserver(name, 'bind-2')

        # check the zone is still active
        LOG.info("checking the zone is (still) active")
        resp = self.get_zone(name, zid)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ACTIVE')

    def test_recovery_of_recordset_create_with_low_threshold_percentage(self):
        """Create a recordset while a nameserver is down. Check the recordset
        gets to the live nameserver and goes active (due to threshold
        percentage). Restart the nameserver. Check the recordset is on the
        nameserver.
        """
        zname, zid = self._create_zone()

        # kill a nameserver. check that a create goes to active.
        self.kill_nameserver('bind-2')
        rrname, rrid = self.create_recordset(zname, zid)
        self.wait_for_zone_to_active(zname, zid)
        self.wait_for_name_on_nameserver(rrname, 'bind-1')

        # restart the nameserver. the record must be found on all nameservers.
        self.restart_nameserver('bind-2')
        self.wait_for_name_on_nameserver(rrname, 'bind-2')

    def test_recovery_of_zone_delete_with_low_threshold_percentage(self):
        """Delete an active zone while a nameserver is down. Check the zone is
        removed from another nameserver but that zone 404s (due to the
        threshold percentage). Restore the nameserver. Check the zone is
        removed from the remaining nameservers."""
        name, zid = self._create_zone()

        # kill a nameserver. check that a delete leads to 404.
        self.kill_nameserver('bind-2')
        self.delete_zone(name, zid)
        self.wait_for_zone_to_404(name, zid)
        self.wait_for_name_removed_from_nameserver(name, 'bind-1')

        # restart the nameserver. the zone must be removed from all nameservers
        # (within our timeout)
        self.restart_nameserver('bind-2')
        self.wait_for_name_removed_from_nameserver(name, 'bind-2')

    def _create_zone(self):
        # create a zone
        name, zid = self.create_zone()
        self.wait_for_zone_to_active(name, zid)
        self.wait_for_name_on_nameserver(name, 'bind-1')
        self.wait_for_name_on_nameserver(name, 'bind-2')
        return name, zid
