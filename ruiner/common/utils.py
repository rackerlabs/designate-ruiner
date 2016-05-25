import json
import logging
import subprocess
import random
import string
import os

import dns
import dns.exception
import dns.message
import dns.rdatatype
import dns.query

import colorlog

from ruiner.common.config import cfg


def create_logger(name):
    colors = cfg.CONF['ruiner:colorlog']
    stream = logging.StreamHandler()
    stream.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s [%(levelname)s] %(message)s',
        log_colors={
            'DEBUG': colors.debug_color,
            'INFO': colors.info_color,
            'WARNING': colors.warning_color,
            'ERROR': colors.error_color,
            'CRITICAL': colors.critical_color,
        }
    ))

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream)
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
            msg += "\n{0}".format(json.dumps(resp.text, indent=2))
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
    resp = dns.query.udp(query, host, timeout=1, port=port)
    LOG.debug("\n%s", resp)
    return resp


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


def random_project_name():
    chars = "".join(random.choice(string.ascii_letters) for _ in range(8))
    return "ruin_designate_%s" % chars


def cleanup_file(filename):
    try:
        os.remove(filename)
    except OSError:
        pass
