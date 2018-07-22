# -*- coding:UTF-8  -*-
"""
对称加解密类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import hashlib
import socket
import uuid
from cryptography.fernet import Fernet, InvalidToken


class Crypto:
    """Encrypt、Decrypt Algorithm
        cryptography.fernet.Fernet
        加解密算法为AES，密钥位长128，CBC模式，填充标准PKCS7
        签名算法为SHA256的HMAC，密钥位长128位
    """
    SALT = "#@Py3Crawl@#"

    def __init__(self):
        # MAC + 固定字符串 + 计算机名，生成基本上唯一的加密私钥
        private_key = hex(uuid.getnode()) + self.SALT + socket.gethostname()

        # 任意字符串MD5后生成32位的key，然后base64
        self.PRIVATE_KEY = base64.urlsafe_b64encode(hashlib.md5(private_key.encode()).hexdigest().encode())

    def encrypt(self, s):
        if not isinstance(s, bytes):
            s = str(s).encode("UTF-8")
        f = Fernet(self.PRIVATE_KEY)
        return f.encrypt(s).decode()

    def decrypt(self, s):
        if not s:
            return None
        f = Fernet(self.PRIVATE_KEY)
        try:
            return f.decrypt(s.encode()).decode()
        except InvalidToken:
            return None
