from ConfigParser import ConfigParser
from ConfigParser import NoSectionError
from cStringIO import StringIO


class IniFile(object):
    """Simple utility for editing an ini file in place.

    This is not thread safe. Don't write the same file from multiple threads.
    """

    def __init__(self, filename):
        self.filename = filename

    def set(self, section_name, key, value):
        config = self._read()
        try:
            config.set(section_name, key, value)
        except NoSectionError:
            config.add_section(section_name)
            config.set(section_name, key, value)
        self._write(config)

    def get(self, section_name, key):
        return self._read().get(section_name, key)

    def getint(self, section_name, key):
        return self._read().getint(section_name, key)

    def _write(self, config):
        with open(self.filename, 'w') as f:
            config.write(f)

    def _read(self):
        config = ConfigParser(allow_no_value=True)

        # ConfigParser refuses to read an empty file
        contents = open(self.filename, 'r').read().strip()
        if contents:
            config.readfp(StringIO(contents))

        return config
