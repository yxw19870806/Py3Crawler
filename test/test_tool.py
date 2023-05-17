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
        self.assertTrue(tool.is_date("2020-01-01"))
        self.assertFalse(tool.is_date("2020-01-01 00:00:00"))
        self.assertFalse(tool.is_date("20200101"))

    def is_datetime(self):
        self.assertFalse(tool.is_datetime("2020-01-01"))
        self.assertTrue(tool.is_datetime("2020-01-01 00:00:00"))
        self.assertFalse(tool.is_datetime("20200101000000"))

    def test_json_decode(self):
        self.assertDictEqual({"a": "b"}, tool.json_decode('{"a": "b"}'))
        self.assertListEqual([1, 2], tool.json_decode("[1, 2]"))
        self.assertIsNone(tool.json_decode("['1]"))
        self.assertTrue(tool.json_decode("true"))
        self.assertFalse(tool.json_decode("false"))
        self.assertIsNone(tool.json_decode("null"))

    def test_json_encode(self):
        self.assertEqual('{"a": "b"}', tool.json_encode({"a": "b"}))
        self.assertEqual("[1, 2]", tool.json_encode([1, 2]))
        self.assertEqual("true", tool.json_encode(True))
        self.assertEqual("false", tool.json_encode(False))
        self.assertEqual("null", tool.json_encode(None))

    def test_dyadic_list_to_string(self):
        self.assertEqual("a\tb\nc\td", tool.dyadic_list_to_string([["a", "b"], ["c", "d"]]))

    def test_string_to_dyadic_list(self):
        self.assertEqual([["a", "b"], ["c", "d"]], tool.string_to_dyadic_list("a\tb\nc\td"))

    def test_generate_random_string(self):
        self.assertEqual(10, len(tool.generate_random_string(10)))
        self.assertRegex(tool.generate_random_string(100, 1), "^[a-z]{100}$")
        self.assertRegex(tool.generate_random_string(100, 2), "^[A-Z]{100}$")
        self.assertRegex(tool.generate_random_string(100, 4), r"^\d{100}$")
        self.assertRegex(tool.generate_random_string(100, 3), "^[a-zA-Z]{100}$")
        self.assertRegex(tool.generate_random_string(100, 5), r"^[\da-z]{100}$")
        self.assertRegex(tool.generate_random_string(100, 6), r"^[\dA-Z]{100}$")
        self.assertRegex(tool.generate_random_string(100, 7), r"^[\da-zA-Z]{100}$")

    def test_convert_timestamp_to_formatted_time(self):
        self.assertEqual("2020-01-01 00:00:00", tool.convert_timestamp_to_formatted_time("%Y-%m-%d %H:%M:%S", 1577808000))

    def test_convert_formatted_time_to_timestamp(self):
        self.assertEqual(1577808000, tool.convert_formatted_time_to_timestamp("2020-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"))

    def test_change_date_format(self):
        self.assertEqual("Jan, 20", tool.change_date_format("2020-01-01 00:00:00", "%Y-%m-%d %H:%M:%S", "%b, %y"))

    def test_check_dict_sub_key(self):
        self.assertTrue(tool.check_dict_sub_key("a", {"a": 1}))
        self.assertFalse(tool.check_dict_sub_key("b", {"a": 1}))
        self.assertTrue(tool.check_dict_sub_key(("a", "b"), {"a": 1, "b": 1}))
        self.assertFalse(tool.check_dict_sub_key(("a", "b"), {"a": 1}))


if __name__ == '__main__':
    unittest.main()
