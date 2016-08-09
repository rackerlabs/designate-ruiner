import os
import urlparse

import utils


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

    def __init__(self, logger, project_name=None, compose_files=None,
                 carina_dir=None):
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
        self.dir = carina_dir
        self.log = logger

    def _run_cmd(self, *cmd):
        cmd = map(str, cmd)
        if self.compose_files is not None:
            for filename in reversed(self.compose_files):
                cmd[1:1] = ["-f", filename]
        if self.project_name is not None:
            cmd[1:1] = ["-p", self.project_name]
        return utils.run_cmd(cmd, workdir=self.dir)

    def build(self):
        self.log.info("building images")
        return self._run_cmd("docker-compose", "build")

    def up(self, detached=True):
        self.log.info("starting docker containers")
        if not detached:
            return self._run_cmd("docker-compose", "up")
        return self._run_cmd("docker-compose", "up", "-d")

    def down(self):
        self.log.info("stopping docker containers")
        return self._run_cmd("docker-compose", "down")

    def kill(self, container):
        self.log.info("killing container %s", container)
        return self._run_cmd("docker-compose", "kill", container)

    def start(self, container):
        self.log.info("starting container %s", container)
        return self._run_cmd("docker-compose", "start", container)

    def exec_(self, container, cmd):
        self.log.info("running '%s' in container %s", cmd, container)
        cmd = cmd.split(' ')
        return self._run_cmd("docker-compose", "exec", container, *cmd)

    def port(self, container, port, protocol=None):
        self.log.info("getting port for %s:%s", container, port)

        if protocol and protocol not in ["udp", "tcp"]:
            raise Exception("invalid protocol %s" % protocol)

        cmd = ["docker-compose", "port", container, port]
        if protocol:
            cmd[2:2] = ["--protocol", protocol]
        return self._run_cmd(*cmd)

    def logs(self):
        self.log.info("getting docker logs")
        cmd = ["docker-compose", "logs"]
        return self._run_cmd(*cmd)

    def get_host(self, container, port, protocol=None):
        """Return a usable `host:port` for the container.

        The host in os.environ('DOCKER_HOST') will be used, if set.
        Otherwise, it will assume we're running locally and force a host of
        127.0.0.1 instead of 0.0.0.0 (because dnspython complains sending to
        0.0.0.0 but receiving from 127.0.0.1).
        """
        out, err, ret = self.port(container, port, protocol)
        assert ret == 0

        parts = urlparse.urlsplit("tcp://%s" % out.strip())
        host = os.environ.get('DOCKER_HOST', 'tcp://127.0.0.1:80')
        host_parts = urlparse.urlsplit(host)

        return "%s:%s" % (host_parts.hostname, parts.port)
