"""
Secret Manager for CryptoBot.

This module provides the SecretManager class, which securely stores sensitive information
(API keys, passwords), encrypts secrets at rest, supports external secret providers
(OS keychain, etc.), provides secure access to secrets for services, and implements
secret rotation policies.
"""

import os
import json
import logging
import base64
import hashlib
import sqlite3
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import keyring
import getpass

logger = logging.getLogger(__name__)

class SecretManager:
    """
    Manager for sensitive information.
    
    The SecretManager securely stores sensitive information (API keys, passwords),
    encrypts secrets at rest, supports external secret providers (OS keychain, etc.),
    provides secure access to secrets for services, and implements secret rotation policies.
    """
    
    def __init__(self, config_dir: str, app_name: str = "cryptobot"):
        """
        Initialize the secret manager.
        
        Args:
            config_dir: Directory for configuration files
            app_name: Application name
        """
        self._config_dir = config_dir
        self._app_name = app_name
        self._db_path = os.path.join(config_dir, f"{app_name}_secrets.db")
        self._key_path = os.path.join(config_dir, f"{app_name}_key.bin")
        self._cipher = None
        self._use_keyring = True
        self._rotation_days = 90  # Default rotation period
        
        # Create config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Initialize encryption
        self._init_encryption()
        
        # Initialize database
        self._init_db()
        
        logger.info("Secret Manager initialized")
    
    def store_secret(self, name: str, value: str, service: Optional[str] = None,
                    use_keyring: bool = False, expires_in_days: Optional[int] = None) -> None:
        """
        Store a secret.
        
        Args:
            name: Secret name
            value: Secret value
            service: Service that owns the secret
            use_keyring: Whether to use the system keyring
            expires_in_days: Number of days until the secret expires
        """
        if use_keyring and self._use_keyring:
            # Store in system keyring
            keyring_service = f"{self._app_name}_{service}" if service else self._app_name
            keyring.set_password(keyring_service, name, value)
            logger.info(f"Stored secret '{name}' in system keyring")
            
            # Store metadata in database
            self._store_secret_metadata(name, service, True, expires_in_days)
        else:
            # Encrypt the secret
            encrypted_value = self._encrypt(value)
            
            # Store in database
            self._store_secret_in_db(name, encrypted_value, service, expires_in_days)
            
            logger.info(f"Stored secret '{name}' in database")
    
    def get_secret(self, name: str, service: Optional[str] = None) -> Optional[str]:
        """
        Get a secret.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        
        Returns:
            Optional[str]: Secret value, or None if not found
        """
        # Check if secret is in keyring
        is_in_keyring = self._is_secret_in_keyring(name, service)
        
        if is_in_keyring:
            # Get from system keyring
            keyring_service = f"{self._app_name}_{service}" if service else self._app_name
            try:
                value = keyring.get_password(keyring_service, name)
                if value is not None:
                    return value
            except Exception as e:
                logger.error(f"Error getting secret '{name}' from system keyring: {e}")
        
        # Get from database
        encrypted_value = self._get_secret_from_db(name, service)
        
        if encrypted_value is None:
            return None
        
        # Decrypt the secret
        try:
            return self._decrypt(encrypted_value)
        except Exception as e:
            logger.error(f"Error decrypting secret '{name}': {e}")
            return None
    
    def delete_secret(self, name: str, service: Optional[str] = None) -> bool:
        """
        Delete a secret.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        
        Returns:
            bool: True if the secret was deleted, False otherwise
        """
        # Check if secret is in keyring
        is_in_keyring = self._is_secret_in_keyring(name, service)
        
        if is_in_keyring:
            # Delete from system keyring
            keyring_service = f"{self._app_name}_{service}" if service else self._app_name
            try:
                keyring.delete_password(keyring_service, name)
                logger.info(f"Deleted secret '{name}' from system keyring")
            except Exception as e:
                logger.error(f"Error deleting secret '{name}' from system keyring: {e}")
        
        # Delete from database
        success = self._delete_secret_from_db(name, service)
        
        if success:
            logger.info(f"Deleted secret '{name}' from database")
        
        return success
    
    def list_secrets(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all secrets.
        
        Args:
            service: Service that owns the secrets
        
        Returns:
            List[Dict[str, Any]]: List of secret metadata
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            if service:
                cursor.execute(
                    "SELECT name, service, in_keyring, created_at, expires_at, last_rotated_at FROM secrets WHERE service = ?",
                    (service,)
                )
            else:
                cursor.execute(
                    "SELECT name, service, in_keyring, created_at, expires_at, last_rotated_at FROM secrets"
                )
            
            result = []
            for name, svc, in_keyring, created_at, expires_at, last_rotated_at in cursor.fetchall():
                result.append({
                    "name": name,
                    "service": svc,
                    "in_keyring": bool(in_keyring),
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "last_rotated_at": last_rotated_at
                })
            
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error listing secrets: {e}")
            return []
    
    def rotate_secret(self, name: str, new_value: str, service: Optional[str] = None) -> bool:
        """
        Rotate a secret.
        
        Args:
            name: Secret name
            new_value: New secret value
            service: Service that owns the secret
        
        Returns:
            bool: True if the secret was rotated, False otherwise
        """
        # Check if secret exists
        is_in_keyring = self._is_secret_in_keyring(name, service)
        
        if not is_in_keyring and self._get_secret_from_db(name, service) is None:
            logger.error(f"Secret '{name}' not found")
            return False
        
        # Store the new secret
        self.store_secret(name, new_value, service, is_in_keyring)
        
        # Update rotation timestamp
        self._update_rotation_timestamp(name, service)
        
        logger.info(f"Rotated secret '{name}'")
        return True
    
    def check_expired_secrets(self) -> List[Dict[str, Any]]:
        """
        Check for expired secrets.
        
        Returns:
            List[Dict[str, Any]]: List of expired secret metadata
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute(
                "SELECT name, service, in_keyring, created_at, expires_at, last_rotated_at FROM secrets WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,)
            )
            
            result = []
            for name, service, in_keyring, created_at, expires_at, last_rotated_at in cursor.fetchall():
                result.append({
                    "name": name,
                    "service": service,
                    "in_keyring": bool(in_keyring),
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "last_rotated_at": last_rotated_at
                })
            
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error checking expired secrets: {e}")
            return []
    
    def check_rotation_needed(self) -> List[Dict[str, Any]]:
        """
        Check for secrets that need rotation.
        
        Returns:
            List[Dict[str, Any]]: List of secret metadata
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            # Calculate the rotation threshold
            threshold_date = (datetime.now() - timedelta(days=self._rotation_days)).isoformat()
            
            cursor.execute(
                "SELECT name, service, in_keyring, created_at, expires_at, last_rotated_at FROM secrets WHERE last_rotated_at <= ?",
                (threshold_date,)
            )
            
            result = []
            for name, service, in_keyring, created_at, expires_at, last_rotated_at in cursor.fetchall():
                result.append({
                    "name": name,
                    "service": service,
                    "in_keyring": bool(in_keyring),
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "last_rotated_at": last_rotated_at
                })
            
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error checking secrets for rotation: {e}")
            return []
    
    def set_rotation_period(self, days: int) -> None:
        """
        Set the rotation period for secrets.
        
        Args:
            days: Number of days between rotations
        """
        self._rotation_days = days
        logger.info(f"Set secret rotation period to {days} days")
    
    def get_rotation_period(self) -> int:
        """
        Get the rotation period for secrets.
        
        Returns:
            int: Number of days between rotations
        """
        return self._rotation_days
    
    def set_use_keyring(self, use_keyring: bool) -> None:
        """
        Set whether to use the system keyring.
        
        Args:
            use_keyring: Whether to use the system keyring
        """
        self._use_keyring = use_keyring
        logger.info(f"Set use_keyring to {use_keyring}")
    
    def get_use_keyring(self) -> bool:
        """
        Get whether to use the system keyring.
        
        Returns:
            bool: Whether to use the system keyring
        """
        return self._use_keyring
    
    def _init_encryption(self) -> None:
        """Initialize encryption."""
        # Check if key exists
        if os.path.exists(self._key_path):
            # Load key
            try:
                with open(self._key_path, "rb") as f:
                    key = f.read()
                self._cipher = Fernet(key)
                logger.info("Loaded encryption key")
            except Exception as e:
                logger.error(f"Error loading encryption key: {e}")
                self._generate_key()
        else:
            # Generate key
            self._generate_key()
    
    def _generate_key(self) -> None:
        """Generate a new encryption key."""
        try:
            # Generate a random salt
            salt = os.urandom(16)
            
            # Get a password from the user or use a default
            try:
                password = getpass.getpass("Enter a password for encrypting secrets: ").encode()
            except:
                # Use a random password if running non-interactively
                password = os.urandom(32)
            
            # Derive a key from the password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Save the key
            with open(self._key_path, "wb") as f:
                f.write(key)
            
            # Set file permissions
            os.chmod(self._key_path, 0o600)
            
            # Create cipher
            self._cipher = Fernet(key)
            
            logger.info("Generated new encryption key")
        except Exception as e:
            logger.error(f"Error generating encryption key: {e}")
    
    def _encrypt(self, value: str) -> bytes:
        """
        Encrypt a value.
        
        Args:
            value: Value to encrypt
        
        Returns:
            bytes: Encrypted value
        
        Raises:
            ValueError: If encryption is not initialized
        """
        if self._cipher is None:
            raise ValueError("Encryption not initialized")
        
        return self._cipher.encrypt(value.encode())
    
    def _decrypt(self, encrypted_value: bytes) -> str:
        """
        Decrypt a value.
        
        Args:
            encrypted_value: Encrypted value
        
        Returns:
            str: Decrypted value
        
        Raises:
            ValueError: If encryption is not initialized
        """
        if self._cipher is None:
            raise ValueError("Encryption not initialized")
        
        return self._cipher.decrypt(encrypted_value).decode()
    
    def _init_db(self) -> None:
        """Initialize the database."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    service TEXT,
                    value BLOB,
                    in_keyring INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_rotated_at TEXT NOT NULL,
                    UNIQUE(name, service)
                )
            """)
            
            conn.commit()
            conn.close()
            
            # Set file permissions
            os.chmod(self._db_path, 0o600)
            
            logger.info("Secret database initialized")
        except Exception as e:
            logger.error(f"Error initializing secret database: {e}")
    
    def _store_secret_in_db(self, name: str, encrypted_value: bytes, service: Optional[str] = None,
                           expires_in_days: Optional[int] = None) -> None:
        """
        Store a secret in the database.
        
        Args:
            name: Secret name
            encrypted_value: Encrypted secret value
            service: Service that owns the secret
            expires_in_days: Number of days until the secret expires
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            expires_at = None
            if expires_in_days is not None:
                expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
            
            # Check if secret exists
            cursor.execute(
                "SELECT id FROM secrets WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                (name, service, service)
            )
            
            if cursor.fetchone() is None:
                # Insert new secret
                cursor.execute(
                    "INSERT INTO secrets (name, service, value, in_keyring, created_at, expires_at, last_rotated_at) VALUES (?, ?, ?, 0, ?, ?, ?)",
                    (name, service, encrypted_value, now, expires_at, now)
                )
            else:
                # Update existing secret
                cursor.execute(
                    "UPDATE secrets SET value = ?, in_keyring = 0, expires_at = ?, last_rotated_at = ? WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                    (encrypted_value, expires_at, now, name, service, service)
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error storing secret in database: {e}")
    
    def _store_secret_metadata(self, name: str, service: Optional[str] = None,
                              in_keyring: bool = False, expires_in_days: Optional[int] = None) -> None:
        """
        Store secret metadata in the database.
        
        Args:
            name: Secret name
            service: Service that owns the secret
            in_keyring: Whether the secret is stored in the system keyring
            expires_in_days: Number of days until the secret expires
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            expires_at = None
            if expires_in_days is not None:
                expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
            
            # Check if secret exists
            cursor.execute(
                "SELECT id FROM secrets WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                (name, service, service)
            )
            
            if cursor.fetchone() is None:
                # Insert new secret metadata
                cursor.execute(
                    "INSERT INTO secrets (name, service, value, in_keyring, created_at, expires_at, last_rotated_at) VALUES (?, ?, NULL, ?, ?, ?, ?)",
                    (name, service, 1 if in_keyring else 0, now, expires_at, now)
                )
            else:
                # Update existing secret metadata
                cursor.execute(
                    "UPDATE secrets SET value = NULL, in_keyring = ?, expires_at = ?, last_rotated_at = ? WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                    (1 if in_keyring else 0, expires_at, now, name, service, service)
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error storing secret metadata in database: {e}")
    
    def _get_secret_from_db(self, name: str, service: Optional[str] = None) -> Optional[bytes]:
        """
        Get a secret from the database.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        
        Returns:
            Optional[bytes]: Encrypted secret value, or None if not found
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT value FROM secrets WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                (name, service, service)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None or row[0] is None:
                return None
            
            return row[0]
        except Exception as e:
            logger.error(f"Error getting secret from database: {e}")
            return None
    
    def _is_secret_in_keyring(self, name: str, service: Optional[str] = None) -> bool:
        """
        Check if a secret is stored in the system keyring.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        
        Returns:
            bool: True if the secret is in the keyring, False otherwise
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT in_keyring FROM secrets WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                (name, service, service)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                return False
            
            return bool(row[0])
        except Exception as e:
            logger.error(f"Error checking if secret is in keyring: {e}")
            return False
    
    def _delete_secret_from_db(self, name: str, service: Optional[str] = None) -> bool:
        """
        Delete a secret from the database.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        
        Returns:
            bool: True if the secret was deleted, False otherwise
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM secrets WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                (name, service, service)
            )
            
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            return deleted
        except Exception as e:
            logger.error(f"Error deleting secret from database: {e}")
            return False
    
    def _update_rotation_timestamp(self, name: str, service: Optional[str] = None) -> None:
        """
        Update the rotation timestamp for a secret.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute(
                "UPDATE secrets SET last_rotated_at = ? WHERE name = ? AND (service = ? OR (service IS NULL AND ? IS NULL))",
                (now, name, service, service)
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating rotation timestamp: {e}")