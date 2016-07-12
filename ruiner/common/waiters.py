import time


def wait_for_status(api_call, statuses, interval, timeout):
    """Wait for the zone to show the status

    :param statuses: if the status is in this list, stop polling
    :return resp: the last response received
    """
    end = time.time() + timeout
    while True:
        resp = api_call()

        if not resp.ok:
            break
        if end < time.time():
            break
        if resp.json()["status"] in statuses:
            break
        time.sleep(interval)
    return resp


def wait_for_404(api_call, interval, timeout):
    """Wait for a zone to return a 404"""

    end = time.time() + timeout
    while True:
        resp = api_call()
        if resp.status_code == 404:
            break
        if end < time.time():
            break
        time.sleep(interval)
    return resp
