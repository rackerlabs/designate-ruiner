import argparse
import os
import sys

import jinja2

from ruiner.common.utils import strip_ansi


class Trie(object):
    """A prefix trie for paths:

        >>> trie.insert('ruiner-logs/1234/things')
        >>> trie.insert('ruiner-logs/1234/stuff')
        >>> trie.insert('ruiner-logs/5678/things')

    Each part of a path becomes a node:

        'ruiner-logs'--> '1234'--> 'things'
                    \         \--> 'stuff'
                     --> '5678'

    This lets us list prefixes up to a particular depth:

        >>> trie.prefixes(1)
        'ruiner-logs'
        >>> trie.prefixes(2)
        ['ruiner-logs/1234', 'ruiner-logs/5678']

    We can list everything:

        >>> trie.traverse()
        ['./ruiner-logs/1234/things', './ruiner-logs/1234/stuff',
         './ruiner-logs/5678/things']

    We can find a sub-tree and perform the same operations:

        >>> x = trie.find('ruiner-logs/1234')
        >>> x.prefixes(1)
        ['things', 'stuff']
    """

    def __init__(self, val=''):
        self.val = val
        self.children = {}

    def __str__(self):
        return 'Trie(%s)' % self.val

    def __repr__(self):
        return str(self)

    def traverse(self):
        """Return a list containing all (unique) inserted items"""
        if not self.children:
            return [self.val]
        result = []
        for child in self.children.values():
            for item in child.traverse():
                if self.val:
                    item = self.val + '/' + item
                result.append(item)
        return result

    def prefixes(self, depth, prefix=''):
        """Return all prefixes up to the given depth"""
        prefix += self.val if not prefix else "/" + self.val
        result = []
        if depth <= 0 or not self.children:
            result.append(prefix)
        else:
            for child in self.children.values():
                for pre in child.prefixes(depth - 1, prefix):
                    result.append(pre)
        return result

    def insert(self, path):
        parts = path.lstrip('.').split('/')
        current = self
        for c in parts:
            if c in current.children:
                new = current.children[c]
            else:
                new = Trie(c)
                current.children[c] = new
            current = new

    def find(self, prefix):
        """Return the sub-trie at the prefix"""
        parts = prefix.split('/')
        current = self
        for c in parts:
            if c not in current.children:
                return None
            current = current.children[c]
        return current

    @classmethod
    def test(cls):
        paths = [
            'abc/thing.log',
            'abc/123/thing.log',
            'abc/123/stuff.txt',
            'abc/456/thing.log',
            'abc/456/stuff.txt',
            'def/123/thing.log',
            'def/123/stuff.txt',
            'def/456/thing.log',
            'def/456/stuff.txt',
        ]
        trie = cls()
        for p in paths:
            trie.insert(p)
        assert sorted(trie.traverse()) == sorted(paths)

        assert sorted(trie.prefixes(1)) == ['abc', 'def']
        assert sorted(trie.prefixes(2)) == sorted([
            'abc/thing.log', 'abc/123', 'abc/456', 'def/123', 'def/456'
        ])
        assert sorted(trie.prefixes(3)) == sorted(paths)
        assert sorted(trie.prefixes(4)) == sorted(paths)

        sub = trie.find('abc')
        assert sub.val == 'abc'
        assert sorted(sub.prefixes(1)) == sorted([
            'abc/thing.log', 'abc/123', 'abc/456'
        ])
        assert sorted(sub.prefixes(2)) == sorted([
            'abc/thing.log',
            'abc/123/thing.log',
            'abc/123/stuff.txt',
            'abc/456/thing.log',
            'abc/456/stuff.txt',
        ])

        sub = trie.find('abc/123')
        assert sub.val == '123'
        assert sorted(sub.prefixes(1)) == sorted([
            '123/thing.log', '123/stuff.txt',
        ])


def read_filenames():
    return [line.strip().lstrip('./') for line in sys.stdin]


def find_jinja_source(filename):
    """Look for the file in the current dir or this module's containing dir.

    Raise an exception if none of the locations have the file.
    """
    module_dir = os.path.dirname(__file__)
    locations = [filename, os.path.join(module_dir, filename)]
    for loc in locations:
        if os.path.exists(loc):
            return loc
    raise Exception("Failed to find %s at any of %s" % (filename, locations))


def detect_log_level(line):
    for level in ('INFO', 'DEBUG', 'WARNING', 'CRITICAL', 'ERROR'):
        if level in line:
            return level
    return 'UNKNOWN'


def generate_index_html(template_file='index.html.j2'):
    """Return a string containing html for all paths in the trie.

    For all <name>.log files, if a <name>.log.html file is in the trie, then
    we link to the html version of the file instead of the file itself. In this
    case, a second link to the raw html is added.
    """
    filelist = read_filenames()
    trie = Trie()
    for f in filelist:
        trie.insert(f)

    template_file = find_jinja_source(template_file)
    template = jinja2.Template(open(template_file).read())

    dirs = {}
    for d in trie.prefixes(2):
        node = trie.find(d)
        for child in node.children.values():
            children = []
            for p in child.traverse():
                fullpath = d + '/' + p
                if not fullpath.endswith('log.html'):
                    n = trie.find(fullpath)
                    children.append({
                        'name': n.val,
                        'path': fullpath,
                        'has_html': bool(trie.find(fullpath + ".html")),
                    })
            if children:
                dirs[node.val + '/' + child.val] = children

    kwargs = {
        'title': 'Rackspace CloudDNS CI',
        'dirs': dirs,

    }
    print template.render(**kwargs)
    return 0


def write_html_versions_of_logs(template_file='log.html.j2'):
    filenames = read_filenames()

    template_file = find_jinja_source(template_file)
    template = jinja2.Template(open(template_file).read())
    for source in (f for f in filenames if f.endswith('.log')):
        dest = "%s.html" % source

        with open(source, 'r') as f:
            lines = [strip_ansi(line.strip()) for line in f]

        lines = [
            {
                'line': line,
                'loglevel': detect_log_level(line),
            } for line in lines
        ]

        print 'Generating %s' % dest
        content = template.render(lines=lines)
        with open(dest, 'w') as f:
            f.write(content)
    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Generate an html listing of ruiner log files. This is
intended to be used in conjunction with the `ruiner` script:

To generate an index.html, with links to other files:

    $ ruiner logs --last -r | python wrath.py --index > index.html

Write out html versions of all *.log files:

    $ ruiner logs --last -r | python wrath.py --html_log

""")

    parser.add_argument(
        '--test', action='store_true', help="Run internal tests")
    parser.add_argument(
        '--html-log', dest='html_log', action='store_true',
        help="Write html versions of log files")
    parser.add_argument(
        '--index', dest='index', action='store_true',
        help='Generate an index.html with a "directory listing"')

    return parser, parser.parse_args()


def main():
    parser, args = parse_args()
    if args.test:
        Trie.test()
    elif args.index:
        return generate_index_html()
    elif args.html_log:
        return write_html_versions_of_logs()
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
