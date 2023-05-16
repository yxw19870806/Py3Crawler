# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import unittest
from common import const, tool


class TestTool(unittest.TestCase):
    def test_find_sub_string(self):
        self.assertEqual("ab", tool.find_sub_string("abc", "a", "c", const.IncludeStringMode.START))
        self.assertEqual("bc", tool.find_sub_string("abc", "a", "c", const.IncludeStringMode.END))
        self.assertEqual("abc", tool.find_sub_string("abc", "a", "c", const.IncludeStringMode.ALL))
        self.assertEqual("b", tool.find_sub_string("abc", "a", "c", const.IncludeStringMode.NONE))
        self.assertEqual("bc", tool.find_sub_string("abc", "a", None, const.IncludeStringMode.NONE))
        self.assertEqual("ab", tool.find_sub_string("abc", None, "c", const.IncludeStringMode.NONE))

    def test_remove_string_prefix(self):
        self.assertEqual("bc", tool.remove_string_prefix("abc", "a"))
        self.assertEqual("abc", tool.remove_string_prefix("abc", "b"))

    def test_remove_string_suffix(self):
        self.assertEqual("ab", tool.remove_string_suffix("abc", "c"))
        self.assertEqual("abc", tool.remove_string_suffix("abc", "b"))

    def test_is_integer(self):
        self.assertTrue(tool.is_integer(1))
        self.assertTrue(tool.is_integer(+1))
        self.assertTrue(tool.is_integer(-1))
        self.assertTrue(tool.is_integer("1"))
        self.assertTrue(tool.is_integer("+1"))
        self.assertTrue(tool.is_integer("-1"))
        self.assertFalse(tool.is_integer("1a"))
        self.assertFalse(tool.is_integer(True))
        self.assertFalse(tool.is_integer(["1"]))
        self.assertFalse(tool.is_integer({"1": "2"}))

    def test_is_date(self):
        self.assertTrue(tool.is_date("2000-01-01"))
        self.assertFalse(tool.is_date("2000-01-01 00:00:00"))
        self.assertFalse(tool.is_date("20000101"))


if __name__ == '__main__':
    unittest.main()
