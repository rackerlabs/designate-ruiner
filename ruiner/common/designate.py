import json
import requests

import utils

LOG = utils.create_logger(__name__)


class API(object):

    JSON_HEADERS = {
        "Content-type": "application/json",
        "Accept": "application/json",
    }

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def list_zones(self):
        return requests.get(
            "%s/v2/zones" % self.endpoint, headers=self.JSON_HEADERS,
        )

    def get_zone(self, zid):
        return requests.get(
            "%s/v2/zones/%s" % (self.endpoint, zid), headers=self.JSON_HEADERS,
        )

    def create_zone(self):
        body = json.dumps(dict(
            name=utils.random_zone(), email="joe@poo.com",
        ))
        url = "%s/v2/zones" % self.endpoint
        return requests.post(url, data=body, headers=self.JSON_HEADERS)

    def delete_zone(self, zid):
        return requests.delete(
            "%s/v2/zones/%s" % (self.endpoint, zid), headers=self.JSON_HEADERS,
        )

    def update_pool(self, hostname="ns1.example.com.",
                    pool_id='794ccc2c-d751-44fe-b57f-8894c9f5c842'):
        body = json.dumps({
            "ns_records": [{
                "hostname": hostname,
                "priority": 1,
            }]
        })
        url = "%s/v2/pools/%s" % (self.endpoint, pool_id)
        return requests.patch(url, data=body, headers=self.JSON_HEADERS)
