"""
Update Manager for CryptoBot.

This module provides the UpdateManager class, which is the central component
responsible for managing updates in the CryptoBot application.
"""

import os
import sys
import logging
import json
import shutil
import tempfile
import hashlib
import platform
import subprocess
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl
import zipfile
import tarfile

logger = logging.getLogger(__name__)

class UpdateManager:
    """
    Manager for CryptoBot updates.
    
    The UpdateManager is responsible for checking for updates, downloading updates,
    and installing updates. It also handles backup and rollback operations.
    """
    
    def __init__(self, config: Dict[str, Any], app_dir: str = None):
        """
        Initialize the update manager.
        
        Args:
            config: Configuration dictionary
            app_dir: Application directory (if None, uses the directory of the executable)
        """
        self._config = config
        
        # Set application directory
        if app_dir is None:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                self._app_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                self._app_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        else:
            self._app_dir = app_dir
        
        # Set update directory
        self._update_dir = os.path.join(self._app_dir, "updates")
        os.makedirs(self._update_dir, exist_ok=True)
        
        # Set backup directory
        self._backup_dir = os.path.join(self._app_dir, "backups")
        os.makedirs(self._backup_dir, exist_ok=True)
        
        # Get update configuration
        self._update_config = self._config.get("update", {})
        self._update_url = self._update_config.get("update_url", "https://api.cryptobot.com/updates")
        self._check_interval = self._update_config.get("check_interval", 86400)  # Default: once per day
        self._auto_check = self._update_config.get("auto_check", True)
        self._auto_download = self._update_config.get("auto_download", False)
        self._auto_install = self._update_config.get("auto_install", False)
        
        # Initialize state
        self._current_version = self._get_current_version()
        self._latest_version = None
        self._update_available = False
        self._update_downloaded = False
        self._update_info = None
        self._download_path = None
        self._last_check_time = 0
        
        logger.info(f"Update Manager initialized (current version: {self._current_version})")
    
    def check_for_updates(self, force: bool = False) -> bool:
        """
        Check for updates.
        
        Args:
            force: Force check even if the check interval hasn't elapsed
            
        Returns:
            bool: True if an update is available, False otherwise
        """
        current_time = time.time()
        
        # Skip check if the check interval hasn't elapsed and not forced
        if not force and current_time - self._last_check_time < self._check_interval:
            logger.debug("Skipping update check (check interval not elapsed)")
            return self._update_available
        
        logger.info("Checking for updates...")
        
        try:
            # Get system information
            system_info = self._get_system_info()
            
            # Create request
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"CryptoBot/{self._current_version} ({system_info})"
            }
            data = json.dumps({
                "version": self._current_version,
                "platform": system_info,
                "components": self._get_installed_components()
            }).encode("utf-8")
            
            # Send request
            context = ssl.create_default_context()
            req = Request(self._update_url, data=data, headers=headers)
            with urlopen(req, context=context, timeout=10) as response:
                response_data = response.read().decode("utf-8")
                update_info = json.loads(response_data)
            
            # Process response
            self._latest_version = update_info.get("latest_version")
            self._update_available = self._is_newer_version(self._latest_version, self._current_version)
            self._update_info = update_info
            self._last_check_time = current_time
            
            if self._update_available:
                logger.info(f"Update available: {self._latest_version}")
                
                # Auto-download if enabled
                if self._auto_download:
                    self.download_update()
                    
                    # Auto-install if enabled
                    if self._auto_install and self._update_downloaded:
                        self.install_update()
            else:
                logger.info("No updates available")
            
            return self._update_available
            
        except (URLError, HTTPError, json.JSONDecodeError, Exception) as e:
            logger.error(f"Error checking for updates: {e}")
            return False
    
    def download_update(self) -> bool:
        """
        Download the latest update.
        
        Returns:
            bool: True if the download was successful, False otherwise
        """
        if not self._update_available:
            logger.warning("No update available to download")
            return False
        
        if not self._update_info:
            logger.warning("Update information not available")
            return False
        
        logger.info(f"Downloading update {self._latest_version}...")
        
        try:
            # Get download URL for the current platform
            download_url = self._get_platform_download_url()
            if not download_url:
                logger.error("No download URL available for the current platform")
                return False
            
            # Create temporary directory for download
            temp_dir = tempfile.mkdtemp()
            file_name = os.path.basename(download_url)
            download_path = os.path.join(temp_dir, file_name)
            
            # Download the update
            context = ssl.create_default_context()
            with urlopen(download_url, context=context, timeout=300) as response, open(download_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            # Verify the download
            if not self._verify_download(download_path):
                logger.error("Downloaded file verification failed")
                shutil.rmtree(temp_dir)
                return False
            
            # Move to updates directory
            update_path = os.path.join(self._update_dir, file_name)
            shutil.move(download_path, update_path)
            
            # Update state
            self._download_path = update_path
            self._update_downloaded = True
            
            logger.info(f"Update downloaded successfully to {update_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            return False
    
    def install_update(self, callback: Callable[[str, float], None] = None) -> bool:
        """
        Install the downloaded update.
        
        Args:
            callback: Optional callback function to report progress
            
        Returns:
            bool: True if the installation was successful, False otherwise
        """
        if not self._update_downloaded:
            logger.warning("No update downloaded to install")
            return False
        
        if not os.path.exists(self._download_path):
            logger.warning(f"Update file not found: {self._download_path}")
            return False
        
        logger.info(f"Installing update {self._latest_version}...")
        
        try:
            # Create backup
            if not self._create_backup():
                logger.error("Failed to create backup")
                return False
            
            # Extract update
            extract_dir = tempfile.mkdtemp()
            self._extract_update(self._download_path, extract_dir, callback)
            
            # Stop services
            self._stop_services()
            
            # Install update
            self._install_files(extract_dir, callback)
            
            # Clean up
            shutil.rmtree(extract_dir)
            os.remove(self._download_path)
            
            # Update version
            self._current_version = self._latest_version
            self._update_available = False
            self._update_downloaded = False
            
            logger.info(f"Update installed successfully (version: {self._current_version})")
            
            # Restart application
            self._restart_application()
            
            return True
            
        except Exception as e:
            logger.error(f"Error installing update: {e}")
            self._rollback()
            return False
    
    def rollback(self) -> bool:
        """
        Rollback to the previous version.
        
        Returns:
            bool: True if the rollback was successful, False otherwise
        """
        return self._rollback()
    
    def get_update_info(self) -> Dict[str, Any]:
        """
        Get information about the available update.
        
        Returns:
            Dict[str, Any]: Update information
        """
        if not self._update_info:
            return {}
        
        return {
            "current_version": self._current_version,
            "latest_version": self._latest_version,
            "update_available": self._update_available,
            "update_downloaded": self._update_downloaded,
            "release_notes": self._update_info.get("release_notes", ""),
            "release_date": self._update_info.get("release_date", ""),
            "download_size": self._update_info.get("download_size", ""),
            "critical_update": self._update_info.get("critical", False)
        }
    
    def _get_current_version(self) -> str:
        """
        Get the current version of the application.
        
        Returns:
            str: Current version
        """
        # Try to get version from version file
        version_file = os.path.join(self._app_dir, "version.txt")
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
        
        # Fall back to config
        return self._config.get("version", "1.0.0")
    
    def _get_system_info(self) -> str:
        """
        Get system information.
        
        Returns:
            str: System information string
        """
        system = platform.system()
        release = platform.release()
        machine = platform.machine()
        
        return f"{system} {release} {machine}"
    
    def _get_installed_components(self) -> List[str]:
        """
        Get a list of installed components.
        
        Returns:
            List[str]: List of installed components
        """
        # This would be implemented based on the actual component structure
        return ["core"]
    
    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """
        Check if version1 is newer than version2.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            bool: True if version1 is newer than version2, False otherwise
        """
        if not version1 or not version2:
            return False
        
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]
        
        # Pad with zeros if necessary
        while len(v1_parts) < 3:
            v1_parts.append(0)
        while len(v2_parts) < 3:
            v2_parts.append(0)
        
        # Compare version parts
        for i in range(len(v1_parts)):
            if v1_parts[i] > v2_parts[i]:
                return True
            elif v1_parts[i] < v2_parts[i]:
                return False
        
        return False
    
    def _get_platform_download_url(self) -> str:
        """
        Get the download URL for the current platform.
        
        Returns:
            str: Download URL
        """
        if not self._update_info:
            return ""
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Map architecture
        arch = "x64"
        if "arm" in machine or "aarch" in machine:
            if "64" in machine:
                arch = "arm64"
            else:
                arch = "arm"
        elif "86" in machine and "64" not in machine:
            arch = "x86"
        
        # Get download URLs
        downloads = self._update_info.get("downloads", {})
        
        # Try exact match
        key = f"{system}-{arch}"
        if key in downloads:
            return downloads[key]
        
        # Try system match
        if system in downloads:
            return downloads[system]
        
        # No match
        return ""
    
    def _verify_download(self, file_path: str) -> bool:
        """
        Verify the downloaded file.
        
        Args:
            file_path: Path to the downloaded file
            
        Returns:
            bool: True if the file is valid, False otherwise
        """
        if not self._update_info:
            return False
        
        # Get expected checksum
        checksums = self._update_info.get("checksums", {})
        file_name = os.path.basename(file_path)
        expected_checksum = checksums.get(file_name)
        
        if not expected_checksum:
            logger.warning(f"No checksum available for {file_name}")
            return True  # Skip verification if no checksum is available
        
        # Calculate actual checksum
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        actual_checksum = sha256.hexdigest()
        
        # Compare checksums
        if actual_checksum.lower() != expected_checksum.lower():
            logger.error(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
            return False
        
        return True
    
    def _create_backup(self) -> bool:
        """
        Create a backup of the current installation.
        
        Returns:
            bool: True if the backup was successful, False otherwise
        """
        logger.info("Creating backup...")
        
        try:
            # Create backup directory
            timestamp = time.strftime("%Y%m%d%H%M%S")
            backup_dir = os.path.join(self._backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup info file
            backup_info = {
                "version": self._current_version,
                "timestamp": timestamp,
                "platform": self._get_system_info()
            }
            with open(os.path.join(backup_dir, "backup_info.json"), "w") as f:
                json.dump(backup_info, f, indent=2)
            
            # Copy files
            for item in os.listdir(self._app_dir):
                # Skip certain directories
                if item in ["updates", "backups", "logs", "data"]:
                    continue
                
                src = os.path.join(self._app_dir, item)
                dst = os.path.join(backup_dir, item)
                
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            logger.info(f"Backup created successfully at {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    def _extract_update(self, file_path: str, extract_dir: str, callback: Callable[[str, float], None] = None) -> bool:
        """
        Extract the update package.
        
        Args:
            file_path: Path to the update package
            extract_dir: Directory to extract to
            callback: Optional callback function to report progress
            
        Returns:
            bool: True if the extraction was successful, False otherwise
        """
        logger.info(f"Extracting update package: {file_path}")
        
        try:
            file_name = os.path.basename(file_path)
            
            if file_name.endswith(".zip"):
                # Extract ZIP file
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    total_files = len(zip_ref.namelist())
                    for i, member in enumerate(zip_ref.namelist()):
                        zip_ref.extract(member, extract_dir)
                        if callback:
                            callback("Extracting", (i + 1) / total_files)
            
            elif file_name.endswith((".tar.gz", ".tgz")):
                # Extract TAR.GZ file
                with tarfile.open(file_path, "r:gz") as tar_ref:
                    total_files = len(tar_ref.getmembers())
                    for i, member in enumerate(tar_ref.getmembers()):
                        tar_ref.extract(member, extract_dir)
                        if callback:
                            callback("Extracting", (i + 1) / total_files)
            
            else:
                logger.error(f"Unsupported file format: {file_name}")
                return False
            
            logger.info(f"Update package extracted to {extract_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting update package: {e}")
            return False
    
    def _stop_services(self) -> bool:
        """
        Stop all services before installing the update.
        
        Returns:
            bool: True if all services were stopped successfully, False otherwise
        """
        logger.info("Stopping services...")
        
        try:
            # This would be implemented to use the Service Manager
            # For now, we'll just assume it's successful
            return True
            
        except Exception as e:
            logger.error(f"Error stopping services: {e}")
            return False
    
    def _install_files(self, extract_dir: str, callback: Callable[[str, float], None] = None) -> bool:
        """
        Install files from the extracted update.
        
        Args:
            extract_dir: Directory containing the extracted update
            callback: Optional callback function to report progress
            
        Returns:
            bool: True if the installation was successful, False otherwise
        """
        logger.info("Installing update files...")
        
        try:
            # Get list of files to install
            files_to_install = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    src = os.path.join(root, file)
                    rel_path = os.path.relpath(src, extract_dir)
                    dst = os.path.join(self._app_dir, rel_path)
                    files_to_install.append((src, dst))
            
            # Install files
            total_files = len(files_to_install)
            for i, (src, dst) in enumerate(files_to_install):
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                
                # Copy file
                shutil.copy2(src, dst)
                
                # Report progress
                if callback:
                    callback("Installing", (i + 1) / total_files)
            
            # Update version file
            with open(os.path.join(self._app_dir, "version.txt"), "w") as f:
                f.write(self._latest_version)
            
            logger.info("Update files installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error installing update files: {e}")
            return False
    
    def _restart_application(self) -> None:
        """
        Restart the application after installing the update.
        """
        logger.info("Restarting application...")
        
        try:
            # This would be implemented to restart the application
            # For now, we'll just log a message
            logger.info("Application restart not implemented")
            
        except Exception as e:
            logger.error(f"Error restarting application: {e}")
    
    def _rollback(self) -> bool:
        """
        Rollback to the previous version.
        
        Returns:
            bool: True if the rollback was successful, False otherwise
        """
        logger.info("Rolling back to previous version...")
        
        try:
            # Find the latest backup
            backups = []
            for item in os.listdir(self._backup_dir):
                if item.startswith("backup_"):
                    backup_path = os.path.join(self._backup_dir, item)
                    if os.path.isdir(backup_path):
                        backups.append(backup_path)
            
            if not backups:
                logger.error("No backups found")
                return False
            
            # Sort backups by timestamp (newest first)
            backups.sort(reverse=True)
            latest_backup = backups[0]
            
            # Stop services
            self._stop_services()
            
            # Restore files
            for item in os.listdir(latest_backup):
                # Skip backup info file
                if item == "backup_info.json":
                    continue
                
                src = os.path.join(latest_backup, item)
                dst = os.path.join(self._app_dir, item)
                
                # Remove existing file/directory
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                
                # Copy backup file/directory
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            # Get backup info
            backup_info_path = os.path.join(latest_backup, "backup_info.json")
            if os.path.exists(backup_info_path):
                with open(backup_info_path, "r") as f:
                    backup_info = json.load(f)
                self._current_version = backup_info.get("version", "1.0.0")
            
            logger.info(f"Rollback successful (version: {self._current_version})")
            
            # Restart application
            self._restart_application()
            
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back: {e}")
            return False
    
    @classmethod
    def from_config_file(cls, config_path: str) -> 'UpdateManager':
        """
        Create an update manager from a configuration file.
        
        Args:
            config_path: Path to the configuration file
        
        Returns:
            UpdateManager: Update manager
        
        Raises:
            FileNotFoundError: If the configuration file does not exist
            json.JSONDecodeError: If the configuration file is not valid JSON
        """
        # Check if the file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found")
        
        # Load the configuration
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Create the update manager
        return cls(config)