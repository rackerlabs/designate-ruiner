from ruiner.common import utils
from ruiner.test import base
from ruiner.common.ini import IniFile

LOG = utils.create_logger(__name__)


class TestZonePerTenantQuota(base.BaseDesignateTest):

    def configure_designate_conf(self):
        super(TestZonePerTenantQuota, self).configure_designate_conf()

        self.quota_zones = 3

        conf = IniFile(self.designate_conf)
        conf.set("DEFAULT", "quota_zones", self.quota_zones)

    def test_quota_zones(self):
        # create enough zones to reach, but not exceed, the quota
        zones = []
        for _ in range(self.quota_zones):
            zones.append(self.create_zone())
        for zone in zones:
            self.wait_for_zone_to_active(*zone)

        # create an additional zone. check that it 413s.
        resp = self.api.create_zone()
        self.log.debug(utils.resp_to_string(resp))
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.json()["code"], 413)
        self.assertEqual(resp.json()["type"], "over_quota")
