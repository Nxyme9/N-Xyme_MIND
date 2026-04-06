"""Hash Service — SHA-256, bcrypt hashing"""

import hashlib, logging

logger = logging.getLogger(__name__)


class HashService:
    @staticmethod
    def sha256(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def sha512(data: str) -> str:
        return hashlib.sha512(data.encode()).hexdigest()

    @staticmethod
    def md5(data: str) -> str:
        return hashlib.md5(data.encode()).hexdigest()

    @staticmethod
    def bcrypt_hash(password: str) -> str:
        try:
            import bcrypt

            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            return HashService.sha256(password)

    @staticmethod
    def bcrypt_verify(password: str, hashed: str) -> bool:
        try:
            import bcrypt

            return bcrypt.checkpw(password.encode(), hashed.encode())
        except ImportError:
            return HashService.sha256(password) == hashed

    @staticmethod
    def file_hash(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
