# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import unittest
from common import const, file


class TestFile(unittest.TestCase):
    test_file_path = os.path.join("cache.txt")

    def clear_cache(self):
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)

    def __del__(self):
        self.clear_cache()

    def test_read_file(self):
        self.clear_cache()
        self.assertFalse(os.path.exists(self.test_file_path))

        with open(self.test_file_path, "w") as file_handle:
            file_handle.write("a\nb")
        self.assertEqual("a\nb", file.read_file(self.test_file_path, const.ReadFileMode.FULL))
        self.assertEqual(["a", "b"], file.read_file(self.test_file_path, const.ReadFileMode.LINE))

        self.clear_cache()

    def test_write_file(self):
        self.clear_cache()
        self.assertFalse(os.path.exists(self.test_file_path))

        file.write_file("a", self.test_file_path, const.WriteFileMode.REPLACE)
        self.assertTrue(os.path.exists(self.test_file_path))
        with open(self.test_file_path, "r") as file_handle:
            self.assertEqual("a\n", file_handle.read())

        file.write_file("b", self.test_file_path, const.WriteFileMode.APPEND)
        self.assertTrue(os.path.exists(self.test_file_path))
        with open(self.test_file_path, "r") as file_handle:
            self.assertEqual("a\nb\n", file_handle.read())

        file.write_file("c", self.test_file_path, const.WriteFileMode.REPLACE)
        self.assertTrue(os.path.exists(self.test_file_path))
        with open(self.test_file_path, "r") as file_handle:
            self.assertEqual("c\n", file_handle.read())

        self.clear_cache()

    def test_read_json_file(self):
        self.clear_cache()
        self.assertFalse(os.path.exists(self.test_file_path))

        self.assertIsNone(file.read_json_file(self.test_file_path, None))

        with open(self.test_file_path, "w") as file_handle:
            file_handle.write('["a", "b"]\n')
        self.assertListEqual(["a", "b"], file.read_json_file(self.test_file_path))

        with open(self.test_file_path, "w") as file_handle:
            file_handle.write('{"a": 1, "b": 2}\n')
        self.assertDictEqual({"a": 1, "b": 2}, file.read_json_file(self.test_file_path))

        self.clear_cache()

    def test_write_json_file(self):
        self.clear_cache()
        self.assertFalse(os.path.exists(self.test_file_path))

        file.write_json_file(["a", "b"], self.test_file_path)
        self.assertTrue(os.path.exists(self.test_file_path))
        with open(self.test_file_path, "r") as file_handle:
            self.assertEqual('["a", "b"]\n', file_handle.read())

        file.write_json_file({"a": 1, "b": 2}, self.test_file_path)
        self.assertTrue(os.path.exists(self.test_file_path))
        with open(self.test_file_path, "r") as file_handle:
            self.assertEqual('{"a": 1, "b": 2}\n', file_handle.read())

        self.clear_cache()


if __name__ == '__main__':
    unittest.main()
