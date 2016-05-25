import mock
import os
import unittest

from ruiner.common.docker import DockerComposer


class TestDockerComposer(unittest.TestCase):

    def setUp(self):
        self.dc = DockerComposer(
            project_name='wumbo',
            compose_files=['hello.yml', 'goodbye.yml'],
            carina_dir='./fake-designate-carina',
        )

    def test_args(self):
        self.assertEqual(self.dc.project_name, 'wumbo')
        self.assertEqual(self.dc.compose_files, ['hello.yml', 'goodbye.yml'])
        self.assertEqual(self.dc.dir, './fake-designate-carina')

    def test_port(self):
        self.dc._run_cmd = mock.Mock(return_value=('0.0.0.0:1234', '', 0))
        self.assertEqual(self.dc.port('api', 123), ('0.0.0.0:1234', '', 0))
        self.dc._run_cmd.assert_called_with(
            'docker-compose', 'port', 'api', 123)

    def test_port_with_protocol(self):
        self.dc._run_cmd = mock.Mock(return_value=('1.2.3.4:5555', '', 0))
        self.assertEqual(self.dc.port('bind-1', 53, 'udp'),
                         ('1.2.3.4:5555', '', 0))
        self.dc._run_cmd.assert_called_with(
            'docker-compose', 'port', '--protocol', 'udp', 'bind-1', 53)

    # make sure DOCKER_HOST is not set
    @mock.patch.dict(os.environ, {}, clear=True)
    def test_get_host(self):
        self.dc.port = mock.Mock(return_value=('0.0.0.0:1234', '', 0))
        self.assertEqual(self.dc.get_host('api', 0), '127.0.0.1:1234')
        self.dc.port.assert_called_with('api', 0, None)

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_get_host_with_protocol(self):
        self.dc.port = mock.Mock(return_value=('0.0.0.0:5555', '', 0))
        self.assertEqual(self.dc.get_host('central', 1122, 'udp'),
                         '127.0.0.1:5555')
        self.dc.port.assert_called_with('central', 1122, 'udp')

    @mock.patch.dict(os.environ, {'DOCKER_HOST': 'tcp://1.2.3.4:2379'},
                     clear=True)
    def test_get_host_respects_docker_host(self):
        self.dc.port = mock.Mock(return_value=('0.0.0.0:5678', '', 0))
        self.assertEqual(self.dc.get_host('api', 0), '1.2.3.4:5678')
