"""
Data Encryption Module
Provides at-rest encryption for sensitive data using Fernet (symmetric encryption)
with support for key rotation
"""

import os
import base64
import hashlib
import json
from typing import Optional, Union, List
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

CRYPTO_AVAILABLE = False
Fernet = None
hashes = None
PBKDF2 = None
AESGCM = None

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTO_AVAILABLE = True
except ImportError:
    logger.warning("Cryptography not installed - encryption unavailable")


class KeyRotationManager:
    """Manages encryption key rotation with secure storage"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path(".nxm_memory/encryption")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.keys_file = self.storage_path / "keys.json.enc"  # Encrypted keys file
        self._keys: List[dict] = []
        self._master_key: Optional[str] = None
        self._load_keys()
    
    def _get_master_key(self) -> str:
        """Get master key from environment or secure source"""
        # Priority: Env var > HSM placeholder > Generate warning
        master_key = os.getenv("NXM_MASTER_KEY", "")
        if master_key:
            return master_key
        
        # Check for HSM/vault integration
        vault_addr = os.getenv("VAULT_ADDR", "")
        vault_token = os.getenv("VAULT_TOKEN", "")
        if vault_addr and vault_token:
            # Would integrate with Vault here
            logger.info("Vault integration configured")
            return ""
        
        logger.warning("No master key set - encryption may be using weak fallback")
        fallback = os.getenv("JWT_SECRET", "")
        if not fallback or len(fallback) < 32:
            import secrets
            logger.error("FALLBACK ENCRYPTION KEY TOO WEAK - MUST SET NXM_MASTER_KEY")
            return secrets.token_hex(32)
        return fallback
    
    def _encrypt_keys_file(self, data: str) -> bytes:
        """Encrypt keys file before saving"""
        master_key = self._get_master_key()
        if len(master_key) < 32:
            master_key = hashlib.sha256(master_key.encode()).hexdigest()
        
        salt = os.urandom(16)
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(master_key.encode())
        fernet = Fernet(base64.urlsafe_b64encode(key))
        
        return salt + fernet.encrypt(data.encode())
    
    def _decrypt_keys_file(self, data: bytes) -> Optional[str]:
        """Decrypt keys file after loading"""
        if len(data) < 16:
            return None
        
        master_key = self._get_master_key()
        if len(master_key) < 32:
            master_key = hashlib.sha256(master_key.encode()).hexdigest()
        
        salt = data[:16]
        encrypted = data[16:]
        
        try:
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = kdf.derive(master_key.encode())
            fernet = Fernet(base64.urlsafe_b64encode(key))
            return fernet.decrypt(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt keys file: {e}")
            return None
    
    def _load_keys(self):
        """Load keys from encrypted storage"""
        if self.keys_file.exists():
            try:
                with open(self.keys_file, "rb") as f:
                    encrypted_data = f.read()
                decrypted = self._decrypt_keys_file(encrypted_data)
                if decrypted:
                    self._keys = json.loads(decrypted)
                else:
                    # Try legacy unencrypted format
                    with open(self.keys_file, "r") as f:
                        self._keys = json.load(f)
                    # Migrate to encrypted
                    self._save_keys()
            except Exception as e:
                logger.error(f"Failed to load keys: {e}")
                self._keys = []
    
    def _save_keys(self):
        """Save keys to encrypted storage"""
        try:
            data = json.dumps(self._keys, indent=2)
            encrypted = self._encrypt_keys_file(data)
            with open(self.keys_file, "wb") as f:
                f.write(encrypted)
        except Exception as e:
            logger.error(f"Failed to save keys: {e}")
    
    def add_key(self, key: str, is_primary: bool = False) -> str:
        """Add a new encryption key"""
        key_id = hashlib.sha256(key.encode()[:32]).hexdigest()[:8]
        
        # If adding as primary, demote existing primary
        if is_primary:
            for k in self._keys:
                k["is_primary"] = False
        
        self._keys.append({
            "key_id": key_id,
            "key": key,
            "is_primary": is_primary or len(self._keys) == 0,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": None,
        })
        
        self._save_keys()
        return key_id
    
    def get_primary_key(self) -> Optional[str]:
        """Get the primary encryption key"""
        for key in self._keys:
            if key.get("is_primary"):
                return key["key"]
        return self._keys[0]["key"] if self._keys else None
    
    def get_all_keys(self) -> List[dict]:
        """Get all keys (without exposing secrets)"""
        return [
            {
                "key_id": k["key_id"],
                "is_primary": k.get("is_primary", False),
                "created_at": k.get("created_at"),
                "expires_at": k.get("expires_at"),
            }
            for k in self._keys
        ]
    
    def set_primary_key(self, key_id: str) -> bool:
        """Set a key as primary"""
        for k in self._keys:
            if k["key_id"] == key_id:
                # Demote existing primary
                for existing in self._keys:
                    existing["is_primary"] = False
                k["is_primary"] = True
                self._save_keys()
                return True
        return False
    
    def remove_key(self, key_id: str) -> bool:
        """Remove a key (cannot remove primary if it's the only one)"""
        for i, k in enumerate(self._keys):
            if k["key_id"] == key_id:
                if k.get("is_primary") and len(self._keys) == 1:
                    return False  # Cannot remove only key
                self._keys.pop(i)
                self._save_keys()
                return True
        return False
    
    def rotate_key(self) -> str:
        """Rotate to a new primary key"""
        new_key = Fernet.generate_key().decode()
        key_id = self.add_key(new_key, is_primary=True)
        return key_id


class DataEncryption:
    """At-rest data encryption using Fernet with key rotation support"""
    
    def __init__(self, key: Optional[str] = None, key_rotation: bool = False):
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not installed")
        
        self._key = key or os.getenv("NXM_ENCRYPTION_KEY", "")
        self._key_rotation = key_rotation
        
        if key_rotation:
            self._key_manager = KeyRotationManager()
            if self._key:
                self._key_manager.add_key(self._key, is_primary=True)
        else:
            self._key_manager = None
        
        if not self._key:
            logger.warning("No encryption key set - generating ephemeral key")
            self._fernet = None
            return
        
        try:
            if len(self._key) < 32:
                self._key = self._derive_key(self._key)
            self._fernet = Fernet(self._key.encode() if isinstance(self._key, str) else self._key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self._fernet = None
    
    def _derive_key(self, password: str) -> str:
        """Derive a key from password using PBKDF2"""
        salt = b"nxyme_salt_v1"
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode()
    
    def is_configured(self) -> bool:
        return self._fernet is not None
    
    def encrypt(self, data: Union[str, bytes]) -> Optional[bytes]:
        """Encrypt data"""
        if not self._fernet:
            logger.warning("Encryption not configured")
            return data.encode() if isinstance(data, str) else data
        
        try:
            if isinstance(data, str):
                data = data.encode()
            return self._fernet.encrypt(data)
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(self, encrypted_data: bytes) -> Optional[bytes]:
        """Decrypt data"""
        if not self._fernet:
            logger.warning("Encryption not configured")
            return encrypted_data
        
        try:
            return self._fernet.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_with_key_id(self, data: Union[str, bytes]) -> Optional[dict]:
        """Encrypt data and include key ID for decryption"""
        if self._key_rotation and self._key_manager:
            primary_key = self._key_manager.get_primary_key()
            if primary_key:
                fernet = Fernet(primary_key.encode() if isinstance(primary_key, str) else primary_key)
                key_id = hashlib.sha256(primary_key.encode()[:32]).hexdigest()[:8]
                
                if isinstance(data, str):
                    data = data.encode()
                
                encrypted = fernet.encrypt(data)
                return {
                    "data": encrypted.decode() if isinstance(encrypted, bytes) else encrypted,
                    "key_id": key_id,
                }
        
        # Fallback to regular encryption
        encrypted = self.encrypt(data)
        if encrypted:
            return {"data": encrypted.decode() if isinstance(encrypted, bytes) else encrypted}
        return None
    
    def decrypt_with_key_id(self, encrypted_package: dict) -> Optional[bytes]:
        """Decrypt data using key ID"""
        if not encrypted_package or "data" not in encrypted_package:
            return None
        
        encrypted_data = encrypted_package["data"]
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        
        # Try primary key first
        if self._key_manager:
            primary_key = self._key_manager.get_primary_key()
            if primary_key:
                try:
                    fernet = Fernet(primary_key.encode() if isinstance(primary_key, str) else primary_key)
                    return fernet.decrypt(encrypted_data)
                except:
                    pass
            
            # Try all keys
            for key_info in self._key_manager._keys:
                try:
                    key = key_info["key"]
                    fernet = Fernet(key.encode() if isinstance(key, str) else key)
                    return fernet.decrypt(encrypted_data)
                except:
                    continue
        
        # Fallback to regular decryption
        return self.decrypt(encrypted_data)
    
    def rotate_keys(self) -> bool:
        """Rotate encryption keys"""
        if not self._key_rotation or not self._key_manager:
            return False
        
        try:
            new_key_id = self._key_manager.rotate_key()
            new_key = self._key_manager.get_primary_key()
            if new_key:
                self._key = new_key
                self._fernet = Fernet(new_key.encode() if isinstance(new_key, str) else new_key)
                return True
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
        
        return False
    
    def get_key_status(self) -> dict:
        """Get encryption key status"""
        if self._key_rotation and self._key_manager:
            return {
                "key_rotation_enabled": True,
                "keys": self._key_manager.get_all_keys(),
            }
        return {
            "key_rotation_enabled": False,
            "key_configured": self.is_configured(),
        }
    
    def encrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> bool:
        """Encrypt a file"""
        if not self._fernet:
            return False
        
        try:
            with open(input_path, "rb") as f:
                data = f.read()
            
            encrypted = self.encrypt(data)
            if not encrypted:
                return False
            
            output_path = output_path or Path(str(input_path) + ".enc")
            with open(output_path, "wb") as f:
                f.write(encrypted)
            
            return True
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            return False
    
    def decrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> bool:
        """Decrypt a file"""
        if not self._fernet:
            return False
        
        try:
            with open(input_path, "rb") as f:
                encrypted = f.read()
            
            decrypted = self.decrypt(encrypted)
            if not decrypted:
                return False
            
            output_path = output_path or input_path.with_suffix(".dec")
            with open(output_path, "wb") as f:
                f.write(decrypted)
            
            return True
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            return False
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography not installed")
        return Fernet.generate_key().decode()


class SecureStorage:
    """Encrypted file storage wrapper"""
    
    def __init__(self, storage_path: Path, encryption: Optional[DataEncryption] = None):
        self.storage_path = storage_path
        self.encryption = encryption or DataEncryption()
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, key: str, data: Union[str, bytes]) -> bool:
        """Save encrypted data"""
        if not self.encryption.is_configured():
            logger.warning("Saving unencrypted data")
            return self._save_plain(key, data)
        
        encrypted = self.encryption.encrypt(data)
        if not encrypted:
            return False
        
        return self._save_raw(key, encrypted)
    
    def load(self, key: str) -> Optional[bytes]:
        """Load and decrypt data"""
        encrypted = self._load_raw(key)
        if not encrypted:
            return None
        
        if not self.encryption.is_configured():
            return encrypted
        
        return self.encryption.decrypt(encrypted)
    
    def _save_plain(self, key: str, data: Union[str, bytes]) -> bool:
        try:
            file_path = self.storage_path / f"{key}.json"
            with open(file_path, "w" if isinstance(data, str) else "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False
    
    def _save_raw(self, key: str, data: bytes) -> bool:
        try:
            file_path = self.storage_path / f"{key}.enc"
            with open(file_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False
    
    def _load_raw(self, key: str) -> Optional[bytes]:
        try:
            file_path = self.storage_path / f"{key}.enc"
            if not file_path.exists():
                file_path = self.storage_path / f"{key}.json"
                if not file_path.exists():
                    return None
                with open(file_path, "rb") as f:
                    return f.read()
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete stored data"""
        try:
            for ext in [".enc", ".json"]:
                file_path = self.storage_path / f"{key}{ext}"
                if file_path.exists():
                    file_path.unlink()
                    return True
            return False
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False


_encryption: Optional[DataEncryption] = None


def get_encryption() -> DataEncryption:
    """Get the global encryption instance"""
    global _encryption
    if _encryption is None:
        _encryption = DataEncryption()
    return _encryption
