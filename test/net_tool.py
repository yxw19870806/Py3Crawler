# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import unittest
from common import net_config


class TestNetTool(unittest.TestCase):
    def test_convert_to_bytes(self):
        self.assertEqual(1, net_config.convert_to_bytes("1", 0))
        self.assertEqual(2, net_config.convert_to_bytes("2 B", 0))
        self.assertEqual(3 * 2 ** 10, net_config.convert_to_bytes("3 KB", 0))
        self.assertEqual(4 * 2 ** 20, net_config.convert_to_bytes("4 MB", 0))
        self.assertEqual(5 * 2 ** 30, net_config.convert_to_bytes("5 GB", 0))


if __name__ == '__main__':
    unittest.main()
