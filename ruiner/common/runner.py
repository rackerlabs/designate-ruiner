import argparse
from datetime import datetime
import os
import subprocess
import signal
import sys


from ruiner.common.config import cfg


def pytest(args):
    """Run tests with py.test, ensuring all py.test processes use the same
    timestamp for the test run"""
    RUINER_TEST_START_TIME = datetime.utcnow().strftime('%Y-%m-%d_%H_%M_%S.%f')

    env = dict(os.environ)
    env.update({
        'RUINER_TEST_START_TIME': RUINER_TEST_START_TIME,
    })

    try:
        p = subprocess.Popen(['py.test'] + list(args), env=env)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()
        sys.exit(1)

    return p.returncode


def logs(args):
    """List logs from previous ruiner test runs."""
    log_dir = cfg.CONF.ruiner.log_dir

    if not os.path.exists(log_dir):
        print '{} does not exist'.format(log_dir)
        return 1

    dirs = [os.path.join(log_dir, d) for d in os.listdir(log_dir)]
    if not dirs:
        print 'No previous logs in {}'.format(log_dir)
        return 1

    # sort log dirs by time
    entries = [(d, os.path.getmtime(d)) for d in dirs]
    entries.sort(key=lambda x: x[1], reverse=True)

    result_dirs = []
    if args.want_last:
        result_dirs.append(entries[0][0])
    else:
        result_dirs.extend([d for d, _ in entries])

    if args.want_recursive:
        for f in recursive_list(result_dirs):
            print f
    else:
        for d in result_dirs:
            print d

    return 0


def recursive_list(dirs):
    """Return a sorted, recursive list of plain files in the directories"""
    result = []
    frontier = list(dirs)
    while frontier:
        for current, subdirs, files in os.walk(frontier.pop(0)):
            frontier.extend(subdirs)
            for f in files:
                result.append(os.path.join(current, f))
    result.sort()
    return result


def parse_args():
    # We need a bit of extra stuff here in order to forward arbitrary flags to
    # a subprocess. For example, with:
    #
    #   ruiner pytest --collect-only
    #
    # argparse will complain because we didn't define a `--collect-only` flag.
    # However, we need to forward all remaining args along to py.test. To work
    # around this:
    #
    #   - Require a strict format of `<script> <command> [args...]`. No flags
    #   are allowed between the script and the command.
    #   - The base/top-level parser is given just the command to parse.
    #   - Each command gets its own special subparser.
    #
    # This lets us easily remove the subparser for the `pytest` command, to
    # then forward all args without argparse complaining, and without losing
    # argparse everywhere.
    parser = argparse.ArgumentParser(description="""
A tiny wrapper for the designate-ruiner tests, to make management and discovery
of test logs easier.""")

    # declare subparsers here
    subparsers = parser.add_subparsers()
    pytest_sub_parser = subparsers.add_parser(
        'py.test', help='Run tests with py.test')
    log_sub_parser = subparsers.add_parser(
        'logs', help='List logs from previous test runs')

    # the actual subparser for the logs command
    log_parser = argparse.ArgumentParser(
        description="List logs from previous test runs")
    log_parser.add_argument(
        '--last', dest='want_last', action='store_true',
        help="only show the most recent log entry")
    log_parser.add_argument(
        '-r', dest='want_recursive', action='store_true',
        help="recursively list all files")

    # set the handler for the pytest command. this has no subparser
    pytest_sub_parser.set_defaults(
        handler=lambda: invoke_command_handler('py.test', pytest)
    )

    # set the handler and the subparser for the logs command
    log_sub_parser.set_defaults(
        handler=lambda: invoke_command_handler('logs', logs, log_parser),
    )
    return parser.parse_args(sys.argv[1:2])


def invoke_command_handler(command, func, arg_parser=None):
    """This invokes the func, passing it appropriate arguments.

    This finds all args after the first occurrence of `command` in sys.argv.
    If given, `arg_parser` will parse the args. Then `func` is invoke with the
    args (or parsed args).
    """
    i = sys.argv.index(command)
    args = sys.argv[i+1:]
    if arg_parser:
        args = arg_parser.parse_args(args)
    return func(args)


def main():
    args = parse_args()
    sys.exit(args.handler())


if __name__ == '__main__':
    main()
