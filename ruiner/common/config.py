import os.path

from oslo_config import cfg


def get_location(name='ruiner.conf'):
    path = os.path.realpath(os.environ.get('RUINER_CONF', name))
    if not os.path.exists(path):
        raise Exception("Failed to find config file at %r" % path)
    return path

cfg.CONF.register_group(cfg.OptGroup('ruiner'))

cfg.CONF.register_opts([
    cfg.IntOpt("interval", default=3),
    cfg.IntOpt("timeout", default=120),
    cfg.IntOpt("service_startup_wait_time", default=15,
               help="How to wait after `docker-compose up` for services to "
                    "be ready."),
], group='ruiner')

cfg.CONF(args=[], default_config_files=[get_location()])
