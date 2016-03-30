import time
import subprocess

import dns.exception

import designate
import docker
import utils
import waiters

LOG = utils.create_logger(__name__)

docker_composer = docker.DockerComposer()

def prechecks(api, bind1, bind2):
    LOG.info("checking the api by listing zones")
    resp = api.list_zones()
    LOG.debug(utils.resp_to_string(resp))

    LOG.info("checking bind-1 by digging it")
    utils.dig("poo.com.", bind1, "ANY")

    LOG.info("checking bind-2 by digging it")
    utils.dig("poo.com.", bind2, "ANY")

    LOG.info("all prechecks have passed!")


def test_one_nameserver_goes_down(api, bind1, bind2):
    utils.require_success(docker_composer.pause("bind-2"))

    LOG.debug("checking bind-2 is down")
    try:
        resp = utils.dig("poo.com.", bind2, "ANY")
    except dns.exception.Timeout as e:
        LOG.debug("verified bind-2 is down (query timed out)")
    else:
        LOG.error("failed to pause container bind-2")
        return

    # create a zone
    LOG.info("creating a zone (expecting ERROR)")
    resp = api.create_zone()
    LOG.debug(utils.resp_to_string(resp))
    if resp.status_code != 202:
        LOG.error("Failed to create zone (got status %s)", resp.status_code)
        docker_composer.unpause("bind-2")
        return

    name, zid = resp.json()["name"], resp.json()["id"]

    # wait for the zone to go to error
    LOG.info("waiting for zone %s to go to ERROR", name)
    resp = waiters.wait_for_status(
        lambda: api.get_zone(zid), ["ERROR", "ACTIVE"], timeout=60,
    )
    if not resp or resp.json()["status"] != "ERROR":
        LOG.error("Zone %s failed to go to ERROR", name)
        docker_composer.unpause("bind-2")
        return
    LOG.debug(utils.resp_to_string(resp))

    # unpause bind-2
    utils.require_success(docker_composer.unpause("bind-2"))

    # check that the zone goes to active
    LOG.info("waiting for zone %s to go to ACTIVE", name)
    resp = waiters.wait_for_status(
        lambda: api.get_zone(zid), ["ACTIVE"], timeout=60,
    )
    if not resp or resp.json()["status"] != "ACTIVE":
        LOG.error("Zone %s failed to go to ACTIVE", name)
        docker_composer.unpause("bind-2")
        return
    LOG.debug(utils.resp_to_string(resp))

    LOG.info("test passed!")
    docker_composer.unpause("bind-2")


if __name__ == '__main__':
    LOG.info("Discovering service locations")
    api = designate.API(endpoint=
        "http://%s" % docker_composer.get_host("api", 9001)
    )
    LOG.info("api: %s", api.endpoint)
    bind1 = docker_composer.get_host("bind-1", 53, "udp")
    LOG.info("bind-1: %s", bind1)
    bind2 = docker_composer.get_host("bind-2", 53, "udp")
    LOG.info("bind-2: %s", bind2)

    # unpause bind-2, in case it was paused by a previous run
    docker_composer.unpause("bind-2")

    prechecks(api, bind1, bind2)
    test_one_nameserver_goes_down(api, bind1, bind2)
