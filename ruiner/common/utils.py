import errno
import json
import logging
import subprocess
import random
import re
import string
import os
import tempfile
import shutil

import dns
import dns.exception
import dns.message
import dns.rdatatype
import dns.query

import colorlog

from ruiner.common.config import cfg

# http://stackoverflow.com/a/33925425
ANSI_ESCAPES_REGEX = re.compile('(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
LOG_FMT = ('{%(process)s} %(asctime)s [%(levelname)s] %(filename)s:%(lineno)s '
           '| %(message)s')


def test_start_time_tag():
    """Returns a tag, which may be start time of this test run. This tag is
    identical across the test runner's worker processes."""
    return os.environ.get("RUINER_TEST_START_TIME", "latest")


def get_log_dir():
    """Return the unique log directory for this test run. This will be
    identical across the test runner's worker processes."""
    base_dir = os.path.realpath(cfg.CONF.ruiner.log_dir.rstrip('/'))
    return os.path.join(base_dir, test_start_time_tag())


def setup_log_dir():
    """Create and return the log directory for this test run"""
    log_dir = get_log_dir()
    if log_dir.endswith('latest'):
        shutil.rmtree(log_dir, ignore_errors=True)
    mkdirs(log_dir)
    return log_dir


def get_colored_log_handler():
    colors = cfg.CONF['ruiner:colorlog']

    # stdout/stderr handler, with colors
    handler = logging.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s' + LOG_FMT,
        log_colors={
            'DEBUG': colors.debug_color,
            'INFO': colors.info_color,
            'WARNING': colors.warning_color,
            'ERROR': colors.error_color,
            'CRITICAL': colors.critical_color,
        }
    ))
    return handler


def create_logger(name, filename=None):
    # a handler to write to `master.log`
    master_log_file = os.path.join(get_log_dir(), 'master.log')
    master_handler = logging.FileHandler(master_log_file, delay=True)
    master_handler.setFormatter(logging.Formatter(LOG_FMT))

    log_handlers = [get_colored_log_handler(), master_handler]
    if filename:
        log_file = os.path.join(get_log_dir(), filename)
        file_handler = logging.FileHandler(log_file, delay=True)
        file_handler.setFormatter(logging.Formatter(LOG_FMT))
        log_handlers.append(file_handler)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    for h in log_handlers:
        logger.addHandler(h)
    return logger

LOG = create_logger(__name__)


def run_cmd(cmd, workdir=None):
    """Run the command. Return (out, err, ret) which are the stdout, stderr,
    and return code respectively.

        >>> run_cmd("ls", "-la")
        (u'.\n..\ndocker.py\nutils.py\nwaiters.py\n', u'', 0)
    """
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir,
    )
    out, err = p.communicate()
    _log_cmd(cmd, workdir, out, err, p.returncode)
    return (out.decode('utf-8'), err.decode('utf-8'), p.returncode)


def _log_cmd(cmd, workdir, out, err, ret):
    msg = "command exited %s: " % ret
    if workdir is not None:
        msg += " from dir %s, " % workdir
    msg += " `%s`" % " ".join(cmd)

    if ret == 0:
        LOG.debug(msg)
    else:
        LOG.warning(msg)
        LOG.warning("+-- stdout\n%s", out)
        LOG.warning("+-- stderr\n%s", err)


def resp_to_string(resp):
    """Convert a resp (from the requests lib) to a string."""
    if resp is None:
        return "<resp is None!>"
    msg = "\n----------------- Request -----------------"
    msg += "\n[{2}] {0} {1}".format(
        resp.request.method, resp.request.url, resp.status_code,
    )
    for k, v in resp.request.headers.items():
        msg += "\n{0}: {1}".format(k, v)
    if resp.request.body:
        msg += "\n{0}".format(resp.request.body)

    msg += "\n----------------- Response -----------------"
    msg += "\n{0} {1}".format(resp.status_code, resp.reason)
    for k, v in resp.headers.items():
        msg += "\n{0}: {1}".format(k, v)

    if resp.text and len(resp.text) > 1000:
        msg += "\n{0}... <truncated>".format(resp.text[:1000])
    else:
        try:
            data = json.loads(resp.text)
            msg += "\n{0}".format(json.dumps(data, indent=2))
        except:
            msg += "\n{0}".format(resp.text)

    return msg


def dig(zone_name, nameserver, rdatatype):
    """dig a nameserver for a record of the given type

        >>> dig('poo.com.', '127.0.0.1:53', 'SOA')
        <DNS message, ID 1044>
        >>> dig('poo.com.', '127.0.0.1', dns.rdatatype.SOA)
        <DNS message, ID 1044>
    """
    host = nameserver
    port = 53

    if ':' in nameserver:
        host, port = nameserver.split(':')
        port = int(port)

    if isinstance(rdatatype, basestring):
        rdatatype = dns.rdatatype.from_text(rdatatype)

    query = prepare_query(zone_name, rdatatype)
    return dns.query.udp(query, host, timeout=1, port=port)


def prepare_query(zone_name, rdatatype):
    dns_message = dns.message.make_query(zone_name, rdatatype)
    dns_message.set_opcode(dns.opcode.QUERY)
    return dns_message


def random_zone(name='pooey', tld='com'):
    """
        >>> random_zone(name='pooey', tld='com')
        'pooey-mjxWsMnz.com.'
    """
    chars = "".join(random.choice(string.ascii_letters) for _ in range(8))
    return '{0}-{1}.{2}.'.format(name, chars, tld)


def require_success(result):
    out, err, ret = result
    assert ret == 0


def random_tag(n=8):
    result = "".join(random.choice(string.ascii_letters) for _ in range(n))
    return result.lower()


def random_project_name(name="ruin_designate", tag=None):
    tag = tag or random_tag()
    return "{}_{}".format(name, tag).lower()


def cleanup_file(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


def new_temp_file(prefix, suffix):
    """Return the name of a new (closed) temp file, in tempfile.tempdir.
    This ensures the file will be cleaned up after the test runs."""
    f = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
    f.close()
    return f.name


def mkdirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            return
        raise


def strip_ansi(content):
    """Strip all ansi escape codes"""
    return ANSI_ESCAPES_REGEX.sub('', content)


def random_ipv4():
    return ".".join(str(random.randrange(0, 256)) for _ in range(4))
