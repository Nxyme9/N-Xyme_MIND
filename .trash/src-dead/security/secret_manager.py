"""Secret Manager — Encrypted secret storage"""

import json, logging, os, base64
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SecretManager:
    def __init__(self, storage_file: str = "data/secrets.enc"):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file = self.storage_file.with_suffix(".key")
        self._fernet = self._load_key()
        self._secrets = self._load()

    def _load_key(self) -> Fernet:
        if self.key_file.exists():
            key = self.key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
        return Fernet(key)

    def _load(self) -> dict:
        if self.storage_file.exists():
            data = self._fernet.decrypt(self.storage_file.read_bytes())
            return json.loads(data)
        return {}

    def _save(self):
        data = self._fernet.encrypt(json.dumps(self._secrets).encode())
        self.storage_file.write_bytes(data)

    def set(self, key: str, value: str):
        self._secrets[key] = value
        self._save()

    def get(self, key: str) -> Optional[str]:
        return self._secrets.get(key)

    def delete(self, key: str) -> bool:
        if key in self._secrets:
            del self._secrets[key]
            self._save()
            return True
        return False

    def list_keys(self):
        return list(self._secrets.keys())
