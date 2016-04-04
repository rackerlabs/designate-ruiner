import os

import utils

LOG = utils.create_logger(__name__)


def discover_designate_carina_dir():
    d = os.environ.get("DESIGNATE_CARINA_DIR", "./designate-carina")
    if not os.path.exists(d):
        raise Exception("%s not found. Consider setting env var DESIGNATE_CARINA_DIR" % d)
    elif not os.path.isdir(d):
        raise Exception("%s is not a dir. Set DESIGNATE_CARINA_DIR to a good location" % d)
    return d


class DockerComposer(object):

    def __init__(self, project_name=None):
        self.dir = discover_designate_carina_dir()
        self.project_name = project_name

    def _run_cmd(self, *cmd):
        cmd = map(str, cmd)
        if self.project_name is not None:
            cmd[1:1] = ["-p", self.project_name]
        return utils.run_cmd(cmd, workdir=self.dir)

    def pause(self, container):
        LOG.info("pausing container %s", container)
        return self._run_cmd("docker-compose", "pause", container)

    def unpause(self, container):
        LOG.info("unpausing container %s", container)
        return self._run_cmd("docker-compose", "unpause", container)

    def port(self, container, port, protocol=None):
        LOG.info("getting external port for internal container port %s:%s", container, port)

        if protocol and protocol not in ["udp", "tcp"]:
            raise Exception("invalid protocol %s" % protocol)

        if protocol:
            cmd = ["docker-compose", "port", "--protocol", protocol, container, port]
        else:
            cmd = ["docker-compose", "port", container, port]
        return self._run_cmd(*cmd)

    def get_host(self, container, port, protocol=None):
        out, err, ret = self.port(container, port, protocol)
        assert ret == 0

        # dnspython complains on sending to 0.0.0.0 but receiving from 127.0.0.1
        result = out.strip()
        return result.replace('0.0.0.0', '127.0.0.1')
