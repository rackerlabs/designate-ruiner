import json
import requests

import docker
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
        return requests.post(
            "%s/v2/zones" % self.endpoint, data=body, headers=self.JSON_HEADERS,
        )

    def delete_zone(self, zid):
        return requests.delete(
            "%s/v2/zones/%s" % (self.endpoint, zid), headers=self.JSON_HEADERS,
        )
