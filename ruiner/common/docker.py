import os

import utils

LOG = utils.create_logger(__name__)


def discover_designate_carina_dir():
    d = os.environ.get("DESIGNATE_CARINA_DIR", "./designate-carina")
    if not os.path.exists(d):
        raise Exception(
            "%s not found. Consider setting env var DESIGNATE_CARINA_DIR" % d
        )
    elif not os.path.isdir(d):
        raise Exception(
            "%s is not a dir. Set DESIGNATE_CARINA_DIR to a good location" % d
        )
    return d


class DockerComposer(object):
    """An interface for invoking docker-compose commands"""

    def __init__(self, project_name=None, compose_files=None, carina_dir=None):
        """
        :param project_name: the compose project name to use for all commands
            as in, `docker-compose -p <project_name>`. If None, don't use any
            project name. docker-compose will choose it's own default.
        :param compose_files: a list of docker-compose yaml configs to use.
            as in, `docker-compose -f base.yml -f more.yml -f ... build`.
            If None, don't pass a file. docker-compose will use it's default.
        :param carina_dir: the directory containing designate-carina source.
            see discover_designate_carina_dir()
        """
        self.project_name = project_name
        self.compose_files = compose_files
        self.dir = discover_designate_carina_dir()

    def _run_cmd(self, *cmd):
        cmd = map(str, cmd)
        if self.compose_files is not None:
            for filename in reversed(self.compose_files):
                cmd[1:1] = ["-f", filename]
        if self.project_name is not None:
            cmd[1:1] = ["-p", self.project_name]
        return utils.run_cmd(cmd, workdir=self.dir)

    def build(self):
        LOG.info("building images")
        return self._run_cmd("docker-compose", "build")

    def up(self, detached=True):
        LOG.info("starting docker containers")
        if not detached:
            return self._run_cmd("docker-compose", "up")
        return self._run_cmd("docker-compose", "up", "-d")

    def down(self):
        LOG.info("stopping docker containers")
        return self._run_cmd("docker-compose", "down")

    def pause(self, container):
        LOG.info("pausing container %s", container)
        return self._run_cmd("docker-compose", "pause", container)

    def unpause(self, container):
        LOG.info("unpausing container %s", container)
        return self._run_cmd("docker-compose", "unpause", container)

    def port(self, container, port, protocol=None):
        LOG.info("getting port for %s:%s", container, port)

        if protocol and protocol not in ["udp", "tcp"]:
            raise Exception("invalid protocol %s" % protocol)

        cmd = ["docker-compose", "port", container, port]
        if protocol:
            cmd[2:2] = ["--protocol", protocol]
        return self._run_cmd(*cmd)

    def get_host(self, container, port, protocol=None):
        out, err, ret = self.port(container, port, protocol)
        assert ret == 0

        # dnspython complains sending to 0.0.0.0 but receiving from 127.0.0.1
        result = out.strip()
        return result.replace('0.0.0.0', '127.0.0.1')
