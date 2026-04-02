"""Encryption — AES-256 encryption/decryption"""

import base64, logging, os
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class Encryption:
    def __init__(self, key: bytes = None):
        self.key = key or Fernet.generate_key()
        self._fernet = Fernet(self.key)

    def encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self._fernet.decrypt(encrypted.encode()).decode()

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, encrypted: bytes) -> bytes:
        return self._fernet.decrypt(encrypted)

    def get_key(self) -> str:
        return self.key.decode()
