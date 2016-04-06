import tempfile
import unittest
import logging

from ruiner.common.ini import IniFile

LOG = logging.getLogger(__name__)


class TestIniFile(unittest.TestCase):

    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile()
        self.filename = self.tempfile.name
        LOG.info("using tempfile %s", self.filename)
        self.inifile = IniFile(self.filename)

    def assertFileContains(self, expected):
        content = open(self.filename, 'r').read()
        self.assertEqual(content, expected)

    def test_iniset_in_empty_file(self):
        self.inifile.set("hello", "mykey", "12345")
        self.assertFileContains(
            "[hello]\n"
            "mykey = 12345\n\n"
        )

        self.inifile.set("hello", "mykey", "45678")
        self.assertFileContains(
            "[hello]\n"
            "mykey = 45678\n\n"
        )

        self.inifile.set("hello", "otherkey", '\"abcde\"')
        self.assertFileContains(
            "[hello]\n"
            "mykey = 45678\n"
            "otherkey = \"abcde\"\n\n"
        )

        self.inifile.set("goodbye", "mykey", "")
        self.assertFileContains(
            "[hello]\n"
            "mykey = 45678\n"
            "otherkey = \"abcde\"\n\n"
            "[goodbye]\n"
            "mykey = \n\n"
        )

        self.inifile.set("goodbye", "mykey", "value")
        self.assertFileContains(
            "[hello]\n"
            "mykey = 45678\n"
            "otherkey = \"abcde\"\n\n"
            "[goodbye]\n"
            "mykey = value\n\n"
        )

        self.inifile.set("goodbye", "yellow", 1)
        self.assertFileContains(
            "[hello]\n"
            "mykey = 45678\n"
            "otherkey = \"abcde\"\n\n"
            "[goodbye]\n"
            "mykey = value\n"
            "yellow = 1\n\n"
        )
