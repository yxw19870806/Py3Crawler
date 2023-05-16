# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import unittest
from common import net


class TestNet(unittest.TestCase):
    url = "ftp://username:password@www.test.com:1080/sub/path/name1.name2.ext/?key1=value1&key2=value2#fragment"

    def test_build_header_cookie_string(self):
        self.assertEqual("key1=value1; key2=value2", net.build_header_cookie_string({"key1": "value1", "key2": "value2"}))

    def test_split_cookies_from_cookie_string(self):
        self.assertDictEqual({"key1": "value1", "key2": "value2"}, net.split_cookies_from_cookie_string("key1=value1; key2=value2"))

    def test_get_url_query_dict(self):
        self.assertDictEqual({"key1": "value1", "key2": "value2"}, net.get_url_query_dict(self.url))

    def test_remove_url_query(self):
        self.assertEqual("ftp://username:password@www.test.com:1080/sub/path/name1.name2.ext", net.remove_url_query(self.url))

    def test_get_url_path(self):
        self.assertEqual("/sub/path/name1.name2.ext", net.get_url_path(self.url))

    def test_split_url_path(self):
        self.assertListEqual(["sub", "path", "name1.name2.ext"], net.split_url_path(self.url))

    def test_get_url_basename(self):
        self.assertEqual("name1.name2.ext", net.get_url_basename(self.url))

    def test_get_url_file_name_ext(self):
        self.assertTupleEqual(("name1.name2", "ext"), net.get_url_file_name_ext(self.url))

    def test_get_url_file_ext(self):
        self.assertEqual("ext", net.get_url_file_ext(self.url))

    def test_get_url_file_name(self):
        self.assertEqual("name1.name2", net.get_url_file_name(self.url))


if __name__ == '__main__':
    unittest.main()
