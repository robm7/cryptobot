"""
Platform-specific updater implementations for CryptoBot.

This module provides platform-specific implementations for the update process
on Windows, macOS, and Linux.
"""

import os
import sys
import logging
import subprocess
import platform
import shutil
import tempfile
from typing import Dict, List, Optional, Any, Tuple, Callable
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class PlatformUpdater(ABC):
    """
    Abstract base class for platform-specific updaters.
    """
    
    def __init__(self, app_dir: str):
        """
        Initialize the platform updater.
        
        Args:
            app_dir: Application directory
        """
        self._app_dir = app_dir
    
    @abstractmethod
    def prepare_update(self) -> bool:
        """
        Prepare for the update process.
        
        Returns:
            bool: True if preparation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def install_update(self, update_dir: str) -> bool:
        """
        Install the update.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the installation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def finalize_update(self) -> bool:
        """
        Finalize the update process.
        
        Returns:
            bool: True if finalization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def restart_application(self) -> None:
        """
        Restart the application after updating.
        """
        pass
    
    @classmethod
    def create(cls, app_dir: str) -> 'PlatformUpdater':
        """
        Create a platform-specific updater.
        
        Args:
            app_dir: Application directory
            
        Returns:
            PlatformUpdater: Platform-specific updater
        """
        system = platform.system()
        
        if system == "Windows":
            return WindowsUpdater(app_dir)
        elif system == "Darwin":  # macOS
            return MacOSUpdater(app_dir)
        elif system == "Linux":
            return LinuxUpdater(app_dir)
        else:
            logger.warning(f"Unsupported platform: {system}, using generic updater")
            return GenericUpdater(app_dir)


class WindowsUpdater(PlatformUpdater):
    """
    Windows-specific updater implementation.
    """
    
    def prepare_update(self) -> bool:
        """
        Prepare for the update process on Windows.
        
        Returns:
            bool: True if preparation was successful, False otherwise
        """
        logger.info("Preparing for update on Windows")
        
        try:
            # Check if running with admin privileges
            # This is important for updating files in Program Files
            if not self._is_admin():
                logger.warning("Not running with administrator privileges")
                # We'll continue anyway, but some files might not be updatable
            
            # Stop Windows services if they exist
            self._stop_windows_services()
            
            return True
            
        except Exception as e:
            logger.error(f"Error preparing for update on Windows: {e}")
            return False
    
    def install_update(self, update_dir: str) -> bool:
        """
        Install the update on Windows.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the installation was successful, False otherwise
        """
        logger.info(f"Installing update on Windows from {update_dir}")
        
        try:
            # Check for installer
            installer_path = os.path.join(update_dir, "setup.exe")
            if os.path.exists(installer_path):
                # Run installer
                logger.info(f"Running installer: {installer_path}")
                subprocess.run([installer_path, "/SILENT", "/SUPPRESSMSGBOXES"], check=True)
                return True
            
            # If no installer, copy files manually
            return self._copy_files(update_dir)
            
        except Exception as e:
            logger.error(f"Error installing update on Windows: {e}")
            return False
    
    def finalize_update(self) -> bool:
        """
        Finalize the update process on Windows.
        
        Returns:
            bool: True if finalization was successful, False otherwise
        """
        logger.info("Finalizing update on Windows")
        
        try:
            # Start Windows services if they exist
            self._start_windows_services()
            
            return True
            
        except Exception as e:
            logger.error(f"Error finalizing update on Windows: {e}")
            return False
    
    def restart_application(self) -> None:
        """
        Restart the application after updating on Windows.
        """
        logger.info("Restarting application on Windows")
        
        try:
            # Create a batch file to restart the application
            restart_script = os.path.join(tempfile.gettempdir(), "restart_cryptobot.bat")
            
            with open(restart_script, "w") as f:
                f.write("@echo off\n")
                f.write("ping 127.0.0.1 -n 2 > nul\n")  # Wait for 1 second
                
                # If running as executable
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                    f.write(f'start "" "{exe_path}"\n')
                else:
                    # If running as script
                    script_path = os.path.join(self._app_dir, "main.py")
                    python_path = sys.executable
                    f.write(f'start "" "{python_path}" "{script_path}"\n')
                
                f.write("del %0\n")  # Delete the batch file
            
            # Run the batch file
            subprocess.Popen(["cmd", "/c", restart_script], shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            
            # Exit the current process
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error restarting application on Windows: {e}")
    
    def _is_admin(self) -> bool:
        """
        Check if the application is running with administrator privileges.
        
        Returns:
            bool: True if running with administrator privileges, False otherwise
        """
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def _stop_windows_services(self) -> None:
        """
        Stop Windows services related to the application.
        """
        try:
            # Check if the service exists
            result = subprocess.run(["sc", "query", "CryptoBot"], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Service exists, stop it
                subprocess.run(["sc", "stop", "CryptoBot"], check=True)
                logger.info("CryptoBot Windows service stopped")
        except Exception as e:
            logger.warning(f"Error stopping Windows service: {e}")
    
    def _start_windows_services(self) -> None:
        """
        Start Windows services related to the application.
        """
        try:
            # Check if the service exists
            result = subprocess.run(["sc", "query", "CryptoBot"], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Service exists, start it
                subprocess.run(["sc", "start", "CryptoBot"], check=True)
                logger.info("CryptoBot Windows service started")
        except Exception as e:
            logger.warning(f"Error starting Windows service: {e}")
    
    def _copy_files(self, update_dir: str) -> bool:
        """
        Copy files from the update directory to the application directory.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the copy was successful, False otherwise
        """
        try:
            # Copy files
            for item in os.listdir(update_dir):
                src = os.path.join(update_dir, item)
                dst = os.path.join(self._app_dir, item)
                
                if os.path.isdir(src):
                    # Remove existing directory
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    
                    # Copy directory
                    shutil.copytree(src, dst)
                else:
                    # Copy file
                    shutil.copy2(src, dst)
            
            return True
            
        except Exception as e:
            logger.error(f"Error copying files: {e}")
            return False


class MacOSUpdater(PlatformUpdater):
    """
    macOS-specific updater implementation.
    """
    
    def prepare_update(self) -> bool:
        """
        Prepare for the update process on macOS.
        
        Returns:
            bool: True if preparation was successful, False otherwise
        """
        logger.info("Preparing for update on macOS")
        
        try:
            # Stop launchd services if they exist
            self._stop_launchd_services()
            
            return True
            
        except Exception as e:
            logger.error(f"Error preparing for update on macOS: {e}")
            return False
    
    def install_update(self, update_dir: str) -> bool:
        """
        Install the update on macOS.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the installation was successful, False otherwise
        """
        logger.info(f"Installing update on macOS from {update_dir}")
        
        try:
            # Check for installer package
            pkg_path = None
            for item in os.listdir(update_dir):
                if item.endswith(".pkg"):
                    pkg_path = os.path.join(update_dir, item)
                    break
            
            if pkg_path:
                # Run installer
                logger.info(f"Running installer: {pkg_path}")
                subprocess.run(["installer", "-pkg", pkg_path, "-target", "/"], check=True)
                return True
            
            # Check for app bundle
            app_path = None
            for item in os.listdir(update_dir):
                if item.endswith(".app"):
                    app_path = os.path.join(update_dir, item)
                    break
            
            if app_path:
                # Copy app bundle
                app_name = os.path.basename(app_path)
                dst_path = os.path.join("/Applications", app_name)
                
                # Remove existing app
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                
                # Copy app
                shutil.copytree(app_path, dst_path)
                return True
            
            # If no installer or app bundle, copy files manually
            return self._copy_files(update_dir)
            
        except Exception as e:
            logger.error(f"Error installing update on macOS: {e}")
            return False
    
    def finalize_update(self) -> bool:
        """
        Finalize the update process on macOS.
        
        Returns:
            bool: True if finalization was successful, False otherwise
        """
        logger.info("Finalizing update on macOS")
        
        try:
            # Start launchd services if they exist
            self._start_launchd_services()
            
            return True
            
        except Exception as e:
            logger.error(f"Error finalizing update on macOS: {e}")
            return False
    
    def restart_application(self) -> None:
        """
        Restart the application after updating on macOS.
        """
        logger.info("Restarting application on macOS")
        
        try:
            # Create a shell script to restart the application
            restart_script = os.path.join(tempfile.gettempdir(), "restart_cryptobot.sh")
            
            with open(restart_script, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("sleep 1\n")  # Wait for 1 second
                
                # If running as app bundle
                app_path = None
                if self._app_dir.endswith(".app"):
                    app_path = self._app_dir
                elif os.path.exists(os.path.join("/Applications", "CryptoBot.app")):
                    app_path = os.path.join("/Applications", "CryptoBot.app")
                
                if app_path:
                    f.write(f'open "{app_path}"\n')
                else:
                    # If running as executable
                    if getattr(sys, 'frozen', False):
                        exe_path = sys.executable
                        f.write(f'"{exe_path}" &\n')
                    else:
                        # If running as script
                        script_path = os.path.join(self._app_dir, "main.py")
                        python_path = sys.executable
                        f.write(f'"{python_path}" "{script_path}" &\n')
                
                f.write("rm $0\n")  # Delete the script
            
            # Make the script executable
            os.chmod(restart_script, 0o755)
            
            # Run the script
            subprocess.Popen(["/bin/bash", restart_script])
            
            # Exit the current process
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error restarting application on macOS: {e}")
    
    def _stop_launchd_services(self) -> None:
        """
        Stop launchd services related to the application.
        """
        try:
            # Check if the service exists
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.cryptobot.plist")
            
            if os.path.exists(plist_path):
                # Service exists, stop it
                subprocess.run(["launchctl", "unload", plist_path], check=True)
                logger.info("CryptoBot launchd service stopped")
        except Exception as e:
            logger.warning(f"Error stopping launchd service: {e}")
    
    def _start_launchd_services(self) -> None:
        """
        Start launchd services related to the application.
        """
        try:
            # Check if the service exists
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.cryptobot.plist")
            
            if os.path.exists(plist_path):
                # Service exists, start it
                subprocess.run(["launchctl", "load", plist_path], check=True)
                logger.info("CryptoBot launchd service started")
        except Exception as e:
            logger.warning(f"Error starting launchd service: {e}")
    
    def _copy_files(self, update_dir: str) -> bool:
        """
        Copy files from the update directory to the application directory.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the copy was successful, False otherwise
        """
        try:
            # Copy files
            for item in os.listdir(update_dir):
                src = os.path.join(update_dir, item)
                dst = os.path.join(self._app_dir, item)
                
                if os.path.isdir(src):
                    # Remove existing directory
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    
                    # Copy directory
                    shutil.copytree(src, dst)
                else:
                    # Copy file
                    shutil.copy2(src, dst)
            
            return True
            
        except Exception as e:
            logger.error(f"Error copying files: {e}")
            return False


class LinuxUpdater(PlatformUpdater):
    """
    Linux-specific updater implementation.
    """
    
    def prepare_update(self) -> bool:
        """
        Prepare for the update process on Linux.
        
        Returns:
            bool: True if preparation was successful, False otherwise
        """
        logger.info("Preparing for update on Linux")
        
        try:
            # Check if running with root privileges
            if os.geteuid() != 0:
                logger.warning("Not running with root privileges")
                # We'll continue anyway, but some files might not be updatable
            
            # Stop systemd services if they exist
            self._stop_systemd_services()
            
            return True
            
        except Exception as e:
            logger.error(f"Error preparing for update on Linux: {e}")
            return False
    
    def install_update(self, update_dir: str) -> bool:
        """
        Install the update on Linux.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the installation was successful, False otherwise
        """
        logger.info(f"Installing update on Linux from {update_dir}")
        
        try:
            # Check for package files
            deb_path = None
            rpm_path = None
            
            for item in os.listdir(update_dir):
                if item.endswith(".deb"):
                    deb_path = os.path.join(update_dir, item)
                elif item.endswith(".rpm"):
                    rpm_path = os.path.join(update_dir, item)
            
            # Install package if available
            if deb_path and self._is_debian_based():
                # Install DEB package
                logger.info(f"Installing DEB package: {deb_path}")
                subprocess.run(["dpkg", "-i", deb_path], check=True)
                return True
            
            if rpm_path and self._is_redhat_based():
                # Install RPM package
                logger.info(f"Installing RPM package: {rpm_path}")
                subprocess.run(["rpm", "-U", rpm_path], check=True)
                return True
            
            # Check for AppImage
            appimage_path = None
            for item in os.listdir(update_dir):
                if item.endswith(".AppImage"):
                    appimage_path = os.path.join(update_dir, item)
                    break
            
            if appimage_path:
                # Copy AppImage
                dst_path = os.path.join(self._app_dir, os.path.basename(appimage_path))
                shutil.copy2(appimage_path, dst_path)
                os.chmod(dst_path, 0o755)  # Make executable
                return True
            
            # If no package or AppImage, copy files manually
            return self._copy_files(update_dir)
            
        except Exception as e:
            logger.error(f"Error installing update on Linux: {e}")
            return False
    
    def finalize_update(self) -> bool:
        """
        Finalize the update process on Linux.
        
        Returns:
            bool: True if finalization was successful, False otherwise
        """
        logger.info("Finalizing update on Linux")
        
        try:
            # Start systemd services if they exist
            self._start_systemd_services()
            
            return True
            
        except Exception as e:
            logger.error(f"Error finalizing update on Linux: {e}")
            return False
    
    def restart_application(self) -> None:
        """
        Restart the application after updating on Linux.
        """
        logger.info("Restarting application on Linux")
        
        try:
            # Create a shell script to restart the application
            restart_script = os.path.join(tempfile.gettempdir(), "restart_cryptobot.sh")
            
            with open(restart_script, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("sleep 1\n")  # Wait for 1 second
                
                # If running as AppImage
                appimage_path = None
                for item in os.listdir(self._app_dir):
                    if item.endswith(".AppImage"):
                        appimage_path = os.path.join(self._app_dir, item)
                        break
                
                if appimage_path:
                    f.write(f'"{appimage_path}" &\n')
                else:
                    # If running as executable
                    if getattr(sys, 'frozen', False):
                        exe_path = sys.executable
                        f.write(f'"{exe_path}" &\n')
                    else:
                        # If running as script
                        script_path = os.path.join(self._app_dir, "main.py")
                        python_path = sys.executable
                        f.write(f'"{python_path}" "{script_path}" &\n')
                
                f.write("rm $0\n")  # Delete the script
            
            # Make the script executable
            os.chmod(restart_script, 0o755)
            
            # Run the script
            subprocess.Popen(["/bin/bash", restart_script])
            
            # Exit the current process
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error restarting application on Linux: {e}")
    
    def _is_debian_based(self) -> bool:
        """
        Check if the system is Debian-based.
        
        Returns:
            bool: True if the system is Debian-based, False otherwise
        """
        return os.path.exists("/etc/debian_version")
    
    def _is_redhat_based(self) -> bool:
        """
        Check if the system is Red Hat-based.
        
        Returns:
            bool: True if the system is Red Hat-based, False otherwise
        """
        return os.path.exists("/etc/redhat-release")
    
    def _stop_systemd_services(self) -> None:
        """
        Stop systemd services related to the application.
        """
        try:
            # Check if the service exists
            result = subprocess.run(["systemctl", "is-active", "cryptobot"], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Service exists and is active, stop it
                subprocess.run(["systemctl", "stop", "cryptobot"], check=True)
                logger.info("CryptoBot systemd service stopped")
        except Exception as e:
            logger.warning(f"Error stopping systemd service: {e}")
    
    def _start_systemd_services(self) -> None:
        """
        Start systemd services related to the application.
        """
        try:
            # Check if the service exists
            result = subprocess.run(["systemctl", "is-enabled", "cryptobot"], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Service exists and is enabled, start it
                subprocess.run(["systemctl", "start", "cryptobot"], check=True)
                logger.info("CryptoBot systemd service started")
        except Exception as e:
            logger.warning(f"Error starting systemd service: {e}")
    
    def _copy_files(self, update_dir: str) -> bool:
        """
        Copy files from the update directory to the application directory.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the copy was successful, False otherwise
        """
        try:
            # Copy files
            for item in os.listdir(update_dir):
                src = os.path.join(update_dir, item)
                dst = os.path.join(self._app_dir, item)
                
                if os.path.isdir(src):
                    # Remove existing directory
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    
                    # Copy directory
                    shutil.copytree(src, dst)
                else:
                    # Copy file
                    shutil.copy2(src, dst)
            
            return True
            
        except Exception as e:
            logger.error(f"Error copying files: {e}")
            return False


class GenericUpdater(PlatformUpdater):
    """
    Generic updater implementation for unsupported platforms.
    """
    
    def prepare_update(self) -> bool:
        """
        Prepare for the update process on an unsupported platform.
        
        Returns:
            bool: True if preparation was successful, False otherwise
        """
        logger.info("Preparing for update on unsupported platform")
        return True
    
    def install_update(self, update_dir: str) -> bool:
        """
        Install the update on an unsupported platform.
        
        Args:
            update_dir: Directory containing the update files
            
        Returns:
            bool: True if the installation was successful, False otherwise
        """
        logger.info(f"Installing update on unsupported platform from {update_dir}")
        
        try:
            # Copy files
            for item in os.listdir(update_dir):
                src = os.path.join(update_dir, item)
                dst = os.path.join(self._app_dir, item)
                
                if os.path.isdir(src):
                    # Remove existing directory
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    
                    # Copy directory
                    shutil.copytree(src, dst)
                else:
                    # Copy file
                    shutil.copy2(src, dst)
            
            return True
            
        except Exception as e:
            logger.error(f"Error installing update on unsupported platform: {e}")
            return False
    
    def finalize_update(self) -> bool:
        """
        Finalize the update process on an unsupported platform.
        
        Returns:
            bool: True if finalization was successful, False otherwise
        """
        logger.info("Finalizing update on unsupported platform")
        return True
    
    def restart_application(self) -> None:
        """
        Restart the application after updating on an unsupported platform.
        """
        logger.info("Restarting application on unsupported platform")
        
        try:
            # If running as executable
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                subprocess.Popen([exe_path])
            else:
                # If running as script
                script_path = os.path.join(self._app_dir, "main.py")
                python_path = sys.executable
                subprocess.Popen([python_path, script_path])
            
            # Exit the current process
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error restarting application on unsupported platform: {e}")