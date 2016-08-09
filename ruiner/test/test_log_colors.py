from ruiner.common import utils
from ruiner.test import base


class TestLogColor(base.BaseTest):

    def test_log_color(self):
        # this "test" doesn't check anything, but is useful for checking
        # terminal colors based on the config in jenkins
        #
        #   py.test -sv -k test_log_color ruiner/test/
        #
        log = utils.create_logger('test_log_color')
        log.info('info')
        log.debug('debug')
        log.warning('warning')
        log.critical('critical')
        log.error('error')
