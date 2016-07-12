import json
import requests

import utils

LOG = utils.create_logger(__name__)


class Client(object):

    def __init__(self, endpoint, headers=None, timeout=60):
        self.endpoint = endpoint
        self.timeout = timeout
        self.headers = headers or {}

    def _inject_default_request_args(self, *args, **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        headers = dict(self.headers)
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        return args, kwargs

    def get(self, *args, **kwargs):
        args, kwargs = self._inject_default_request_args(*args, **kwargs)
        return requests.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        args, kwargs = self._inject_default_request_args(*args, **kwargs)
        return requests.post(*args, **kwargs)

    def put(self, *args, **kwargs):
        args, kwargs = self._inject_default_request_args(*args, **kwargs)
        return requests.put(*args, **kwargs)

    def patch(self, *args, **kwargs):
        args, kwargs = self._inject_default_request_args(*args, **kwargs)
        return requests.patch(*args, **kwargs)

    def delete(self, *args, **kwargs):
        args, kwargs = self._inject_default_request_args(*args, **kwargs)
        return requests.delete(*args, **kwargs)


class API(Client):

    JSON_HEADERS = {
        "Content-type": "application/json",
        "Accept": "application/json",
    }

    def __init__(self, endpoint, timeout=60):
        super(API, self).__init__(
            endpoint=endpoint,
            timeout=timeout,
            headers=self.JSON_HEADERS,
        )

    def list_zones(self):
        return self.get(url="%s/v2/zones" % self.endpoint)

    def get_zone(self, zid):
        return self.get(url="%s/v2/zones/%s" % (self.endpoint, zid))

    def create_zone(self):
        body = json.dumps({
            'name': utils.random_zone(),
            'email': 'joe@poo.com',
        })
        return self.post(url="%s/v2/zones" % self.endpoint, data=body)

    def delete_zone(self, zid):
        return self.delete(url="%s/v2/zones/%s" % (self.endpoint, zid))

    def create_recordset(self, zname, zid):
        name = "record-%s.%s" % (utils.random_tag(), zname)
        body = json.dumps({
            'name': name,
            'type': "A",
            'records': [utils.random_ipv4()],
            'ttl': 300,
        })
        url = "%s/v2/zones/%s/recordsets" % (self.endpoint, zid)
        return self.post(url=url, data=body)

    def get_recordset(self, zid, rrid):
        url = "%s/v2/zones/%s/recordsets/%s" % (self.endpoint, zid, rrid)
        return self.get(url=url)
