"""
Update Manager UI for CryptoBot.

This module provides a UI component for the Update Manager that can be
integrated with the Quick Start Launcher.
"""

import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Any, Callable

from .manager import UpdateManager

logger = logging.getLogger(__name__)

class UpdateUI:
    """
    UI component for the Update Manager.
    """
    
    def __init__(self, parent: tk.Widget, update_manager: UpdateManager):
        """
        Initialize the Update UI.
        
        Args:
            parent: Parent widget
            update_manager: Update Manager instance
        """
        self._parent = parent
        self._update_manager = update_manager
        
        # Create UI components
        self._create_ui()
        
        # Initialize state
        self._checking = False
        self._downloading = False
        self._installing = False
        
        # Check for updates automatically if enabled
        self._auto_check_updates()
    
    def _create_ui(self) -> None:
        """
        Create the UI components.
        """
        # Create frame
        self._frame = ttk.LabelFrame(self._parent, text="Updates")
        
        # Create status label
        self._status_label = ttk.Label(
            self._frame,
            text="No updates available",
            font=("Arial", 9)
        )
        self._status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Create progress bar
        self._progress = ttk.Progressbar(
            self._frame,
            orient=tk.HORIZONTAL,
            length=200,
            mode="determinate"
        )
        self._progress.pack(side=tk.LEFT, padx=10, pady=5)
        self._progress.pack_forget()  # Hide initially
        
        # Create check button
        self._check_button = ttk.Button(
            self._frame,
            text="Check for Updates",
            command=self.check_for_updates
        )
        self._check_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Create download button
        self._download_button = ttk.Button(
            self._frame,
            text="Download Update",
            command=self.download_update,
            state=tk.DISABLED
        )
        self._download_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Create install button
        self._install_button = ttk.Button(
            self._frame,
            text="Install Update",
            command=self.install_update,
            state=tk.DISABLED
        )
        self._install_button.pack(side=tk.RIGHT, padx=5, pady=5)
    
    def pack(self, **kwargs) -> None:
        """
        Pack the frame.
        
        Args:
            **kwargs: Pack options
        """
        self._frame.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """
        Grid the frame.
        
        Args:
            **kwargs: Grid options
        """
        self._frame.grid(**kwargs)
    
    def place(self, **kwargs) -> None:
        """
        Place the frame.
        
        Args:
            **kwargs: Place options
        """
        self._frame.place(**kwargs)
    
    def check_for_updates(self) -> None:
        """
        Check for updates.
        """
        if self._checking:
            return
        
        self._checking = True
        self._check_button.config(state=tk.DISABLED)
        self._status_label.config(text="Checking for updates...")
        
        def check():
            try:
                update_available = self._update_manager.check_for_updates(force=True)
                
                # Update UI
                self._parent.after(0, lambda: self._update_ui_after_check(update_available))
                
            except Exception as e:
                logger.error(f"Error checking for updates: {e}")
                self._parent.after(0, lambda: self._update_ui_after_check(False, str(e)))
            
            finally:
                self._checking = False
        
        threading.Thread(target=check, daemon=True).start()
    
    def download_update(self) -> None:
        """
        Download the update.
        """
        if self._downloading:
            return
        
        self._downloading = True
        self._download_button.config(state=tk.DISABLED)
        self._status_label.config(text="Downloading update...")
        self._progress.pack(side=tk.LEFT, padx=10, pady=5)
        self._progress["value"] = 0
        
        def download():
            try:
                success = self._update_manager.download_update()
                
                # Update UI
                self._parent.after(0, lambda: self._update_ui_after_download(success))
                
            except Exception as e:
                logger.error(f"Error downloading update: {e}")
                self._parent.after(0, lambda: self._update_ui_after_download(False, str(e)))
            
            finally:
                self._downloading = False
        
        threading.Thread(target=download, daemon=True).start()
    
    def install_update(self) -> None:
        """
        Install the update.
        """
        if self._installing:
            return
        
        # Confirm installation
        if not messagebox.askyesno(
            "Install Update",
            "Are you sure you want to install the update? The application will be restarted."
        ):
            return
        
        self._installing = True
        self._install_button.config(state=tk.DISABLED)
        self._status_label.config(text="Installing update...")
        self._progress.pack(side=tk.LEFT, padx=10, pady=5)
        self._progress["value"] = 0
        
        def update_progress(status: str, progress: float) -> None:
            self._parent.after(0, lambda: self._status_label.config(text=f"Installing update: {status}..."))
            self._parent.after(0, lambda: self._progress.config(value=progress * 100))
        
        def install():
            try:
                success = self._update_manager.install_update(callback=update_progress)
                
                # Update UI
                self._parent.after(0, lambda: self._update_ui_after_install(success))
                
            except Exception as e:
                logger.error(f"Error installing update: {e}")
                self._parent.after(0, lambda: self._update_ui_after_install(False, str(e)))
            
            finally:
                self._installing = False
        
        threading.Thread(target=install, daemon=True).start()
    
    def _update_ui_after_check(self, update_available: bool, error: str = None) -> None:
        """
        Update the UI after checking for updates.
        
        Args:
            update_available: Whether an update is available
            error: Error message, if any
        """
        self._check_button.config(state=tk.NORMAL)
        
        if error:
            self._status_label.config(text=f"Error checking for updates: {error}")
            return
        
        if update_available:
            update_info = self._update_manager.get_update_info()
            current_version = update_info.get("current_version", "")
            latest_version = update_info.get("latest_version", "")
            
            self._status_label.config(text=f"Update available: {current_version} → {latest_version}")
            self._download_button.config(state=tk.NORMAL)
            
            # Show update details
            self._show_update_details(update_info)
        else:
            self._status_label.config(text="No updates available")
            self._download_button.config(state=tk.DISABLED)
            self._install_button.config(state=tk.DISABLED)
    
    def _update_ui_after_download(self, success: bool, error: str = None) -> None:
        """
        Update the UI after downloading the update.
        
        Args:
            success: Whether the download was successful
            error: Error message, if any
        """
        self._progress.pack_forget()
        self._download_button.config(state=tk.NORMAL)
        
        if error:
            self._status_label.config(text=f"Error downloading update: {error}")
            return
        
        if success:
            update_info = self._update_manager.get_update_info()
            latest_version = update_info.get("latest_version", "")
            
            self._status_label.config(text=f"Update downloaded: {latest_version}")
            self._install_button.config(state=tk.NORMAL)
        else:
            self._status_label.config(text="Failed to download update")
    
    def _update_ui_after_install(self, success: bool, error: str = None) -> None:
        """
        Update the UI after installing the update.
        
        Args:
            success: Whether the installation was successful
            error: Error message, if any
        """
        self._progress.pack_forget()
        self._install_button.config(state=tk.NORMAL)
        
        if error:
            self._status_label.config(text=f"Error installing update: {error}")
            return
        
        if success:
            self._status_label.config(text="Update installed successfully")
            messagebox.showinfo(
                "Update Installed",
                "The update has been installed successfully. The application will now restart."
            )
        else:
            self._status_label.config(text="Failed to install update")
            messagebox.showerror(
                "Update Failed",
                "Failed to install the update. Please try again later."
            )
    
    def _show_update_details(self, update_info: Dict[str, Any]) -> None:
        """
        Show update details.
        
        Args:
            update_info: Update information
        """
        current_version = update_info.get("current_version", "")
        latest_version = update_info.get("latest_version", "")
        release_notes = update_info.get("release_notes", "")
        release_date = update_info.get("release_date", "")
        download_size = update_info.get("download_size", "")
        critical_update = update_info.get("critical_update", False)
        
        # Create message
        message = f"Current version: {current_version}\n"
        message += f"Latest version: {latest_version}\n"
        message += f"Release date: {release_date}\n"
        message += f"Download size: {download_size}\n"
        
        if critical_update:
            message += "\nThis is a critical update and should be installed as soon as possible.\n"
        
        message += "\nRelease notes:\n"
        message += release_notes
        
        # Show message box
        messagebox.showinfo("Update Available", message)
    
    def _auto_check_updates(self) -> None:
        """
        Check for updates automatically if enabled.
        """
        # This would be implemented to check for updates automatically
        # based on the configuration
        pass


class UpdateDialog(tk.Toplevel):
    """
    Dialog for checking, downloading, and installing updates.
    """
    
    def __init__(self, parent: tk.Widget, update_manager: UpdateManager):
        """
        Initialize the Update Dialog.
        
        Args:
            parent: Parent widget
            update_manager: Update Manager instance
        """
        super().__init__(parent)
        
        self.title("CryptoBot Updates")
        self.geometry("600x400")
        self.minsize(500, 300)
        self.transient(parent)
        self.grab_set()
        
        self._update_manager = update_manager
        
        # Create UI components
        self._create_ui()
        
        # Initialize state
        self._checking = False
        self._downloading = False
        self._installing = False
        
        # Check for updates
        self.check_for_updates()
        
        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_ui(self) -> None:
        """
        Create the UI components.
        """
        # Create main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="CryptoBot Updates",
            font=("Arial", 16, "bold")
        ).pack(side=tk.LEFT)
        
        # Create status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            status_frame,
            text="Status:",
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT)
        
        self._status_label = ttk.Label(
            status_frame,
            text="Checking for updates...",
            font=("Arial", 10)
        )
        self._status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Create progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self._progress = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            length=580,
            mode="determinate"
        )
        self._progress.pack(fill=tk.X)
        self._progress.pack_forget()  # Hide initially
        
        # Create info frame
        info_frame = ttk.LabelFrame(main_frame, text="Update Information")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create info grid
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X, padx=10, pady=5)
        
        # Current version
        ttk.Label(
            info_grid,
            text="Current Version:",
            font=("Arial", 10, "bold")
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self._current_version_label = ttk.Label(
            info_grid,
            text="",
            font=("Arial", 10)
        )
        self._current_version_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Latest version
        ttk.Label(
            info_grid,
            text="Latest Version:",
            font=("Arial", 10, "bold")
        ).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self._latest_version_label = ttk.Label(
            info_grid,
            text="",
            font=("Arial", 10)
        )
        self._latest_version_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Release date
        ttk.Label(
            info_grid,
            text="Release Date:",
            font=("Arial", 10, "bold")
        ).grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self._release_date_label = ttk.Label(
            info_grid,
            text="",
            font=("Arial", 10)
        )
        self._release_date_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Download size
        ttk.Label(
            info_grid,
            text="Download Size:",
            font=("Arial", 10, "bold")
        ).grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self._download_size_label = ttk.Label(
            info_grid,
            text="",
            font=("Arial", 10)
        )
        self._download_size_label.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # Critical update
        ttk.Label(
            info_grid,
            text="Critical Update:",
            font=("Arial", 10, "bold")
        ).grid(row=4, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self._critical_update_label = ttk.Label(
            info_grid,
            text="",
            font=("Arial", 10)
        )
        self._critical_update_label.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Release notes
        ttk.Label(
            info_frame,
            text="Release Notes:",
            font=("Arial", 10, "bold")
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self._release_notes_text = tk.Text(
            info_frame,
            wrap=tk.WORD,
            height=8,
            font=("Arial", 10)
        )
        self._release_notes_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self._release_notes_text.config(state=tk.DISABLED)
        
        # Create button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Create check button
        self._check_button = ttk.Button(
            button_frame,
            text="Check for Updates",
            command=self.check_for_updates
        )
        self._check_button.pack(side=tk.LEFT)
        
        # Create download button
        self._download_button = ttk.Button(
            button_frame,
            text="Download Update",
            command=self.download_update,
            state=tk.DISABLED
        )
        self._download_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Create install button
        self._install_button = ttk.Button(
            button_frame,
            text="Install Update",
            command=self.install_update,
            state=tk.DISABLED
        )
        self._install_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Create close button
        self._close_button = ttk.Button(
            button_frame,
            text="Close",
            command=self.destroy
        )
        self._close_button.pack(side=tk.RIGHT)
    
    def check_for_updates(self) -> None:
        """
        Check for updates.
        """
        if self._checking:
            return
        
        self._checking = True
        self._check_button.config(state=tk.DISABLED)
        self._status_label.config(text="Checking for updates...")
        
        def check():
            try:
                update_available = self._update_manager.check_for_updates(force=True)
                
                # Update UI
                self.after(0, lambda: self._update_ui_after_check(update_available))
                
            except Exception as e:
                logger.error(f"Error checking for updates: {e}")
                self.after(0, lambda: self._update_ui_after_check(False, str(e)))
            
            finally:
                self._checking = False
        
        threading.Thread(target=check, daemon=True).start()
    
    def download_update(self) -> None:
        """
        Download the update.
        """
        if self._downloading:
            return
        
        self._downloading = True
        self._download_button.config(state=tk.DISABLED)
        self._status_label.config(text="Downloading update...")
        self._progress.pack(fill=tk.X)
        self._progress["value"] = 0
        
        def download():
            try:
                success = self._update_manager.download_update()
                
                # Update UI
                self.after(0, lambda: self._update_ui_after_download(success))
                
            except Exception as e:
                logger.error(f"Error downloading update: {e}")
                self.after(0, lambda: self._update_ui_after_download(False, str(e)))
            
            finally:
                self._downloading = False
        
        threading.Thread(target=download, daemon=True).start()
    
    def install_update(self) -> None:
        """
        Install the update.
        """
        if self._installing:
            return
        
        # Confirm installation
        if not messagebox.askyesno(
            "Install Update",
            "Are you sure you want to install the update? The application will be restarted."
        ):
            return
        
        self._installing = True
        self._install_button.config(state=tk.DISABLED)
        self._status_label.config(text="Installing update...")
        self._progress.pack(fill=tk.X)
        self._progress["value"] = 0
        
        def update_progress(status: str, progress: float) -> None:
            self.after(0, lambda: self._status_label.config(text=f"Installing update: {status}..."))
            self.after(0, lambda: self._progress.config(value=progress * 100))
        
        def install():
            try:
                success = self._update_manager.install_update(callback=update_progress)
                
                # Update UI
                self.after(0, lambda: self._update_ui_after_install(success))
                
            except Exception as e:
                logger.error(f"Error installing update: {e}")
                self.after(0, lambda: self._update_ui_after_install(False, str(e)))
            
            finally:
                self._installing = False
        
        threading.Thread(target=install, daemon=True).start()
    
    def _update_ui_after_check(self, update_available: bool, error: str = None) -> None:
        """
        Update the UI after checking for updates.
        
        Args:
            update_available: Whether an update is available
            error: Error message, if any
        """
        self._check_button.config(state=tk.NORMAL)
        
        if error:
            self._status_label.config(text=f"Error checking for updates: {error}")
            return
        
        update_info = self._update_manager.get_update_info()
        current_version = update_info.get("current_version", "")
        self._current_version_label.config(text=current_version)
        
        if update_available:
            latest_version = update_info.get("latest_version", "")
            release_date = update_info.get("release_date", "")
            download_size = update_info.get("download_size", "")
            critical_update = update_info.get("critical_update", False)
            release_notes = update_info.get("release_notes", "")
            
            self._status_label.config(text=f"Update available: {current_version} → {latest_version}")
            self._latest_version_label.config(text=latest_version)
            self._release_date_label.config(text=release_date)
            self._download_size_label.config(text=download_size)
            self._critical_update_label.config(text="Yes" if critical_update else "No")
            
            # Update release notes
            self._release_notes_text.config(state=tk.NORMAL)
            self._release_notes_text.delete("1.0", tk.END)
            self._release_notes_text.insert(tk.END, release_notes)
            self._release_notes_text.config(state=tk.DISABLED)
            
            self._download_button.config(state=tk.NORMAL)
        else:
            self._status_label.config(text="No updates available")
            self._latest_version_label.config(text=current_version)
            self._release_date_label.config(text="")
            self._download_size_label.config(text="")
            self._critical_update_label.config(text="")
            
            # Clear release notes
            self._release_notes_text.config(state=tk.NORMAL)
            self._release_notes_text.delete("1.0", tk.END)
            self._release_notes_text.config(state=tk.DISABLED)
            
            self._download_button.config(state=tk.DISABLED)
            self._install_button.config(state=tk.DISABLED)
    
    def _update_ui_after_download(self, success: bool, error: str = None) -> None:
        """
        Update the UI after downloading the update.
        
        Args:
            success: Whether the download was successful
            error: Error message, if any
        """
        self._progress.pack_forget()
        self._download_button.config(state=tk.NORMAL)
        
        if error:
            self._status_label.config(text=f"Error downloading update: {error}")
            return
        
        if success:
            update_info = self._update_manager.get_update_info()
            latest_version = update_info.get("latest_version", "")
            
            self._status_label.config(text=f"Update downloaded: {latest_version}")
            self._install_button.config(state=tk.NORMAL)
        else:
            self._status_label.config(text="Failed to download update")
    
    def _update_ui_after_install(self, success: bool, error: str = None) -> None:
        """
        Update the UI after installing the update.
        
        Args:
            success: Whether the installation was successful
            error: Error message, if any
        """
        self._progress.pack_forget()
        self._install_button.config(state=tk.NORMAL)
        
        if error:
            self._status_label.config(text=f"Error installing update: {error}")
            return
        
        if success:
            self._status_label.config(text="Update installed successfully")
            messagebox.showinfo(
                "Update Installed",
                "The update has been installed successfully. The application will now restart."
            )
            self.destroy()
        else:
            self._status_label.config(text="Failed to install update")
            messagebox.showerror(
                "Update Failed",
                "Failed to install the update. Please try again later."
            )