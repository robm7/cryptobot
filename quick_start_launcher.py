#!/usr/bin/env python
"""
Cryptobot Quick Start Launcher

A user-friendly interface to start and manage the Cryptobot application.
This launcher allows users to:
1. Select which services to start
2. Configure basic options
3. Monitor the status of running services
4. Open the dashboard in a web browser
"""

import os
import sys
import subprocess
import threading
import time
import json
import webbrowser
import logging
import platform
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
from typing import Dict, List, Optional, Any, Callable

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import core components
try:
    from core.service_manager.manager import ServiceManager
    from core.service_manager.registry import ServiceStatus
    from core.config_manager.manager import ConfigManager
    from core.update_manager.manager import UpdateManager
    from core.update_manager.ui import UpdateUI, UpdateDialog
    DIRECT_IMPORT = True
except ImportError:
    # If we can't import directly, we'll use subprocess to run commands
    DIRECT_IMPORT = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("launcher.log")
    ]
)
logger = logging.getLogger("launcher")

# Define service information
SERVICE_INFO = {
    "auth": {
        "name": "Authentication Service",
        "description": "Handles user authentication and API key management",
        "default_port": 8000,
        "dependencies": []
    },
    "strategy": {
        "name": "Strategy Service",
        "description": "Manages trading strategies and signals",
        "default_port": 8001,
        "dependencies": ["auth"]
    },
    "data": {
        "name": "Data Service",
        "description": "Provides market data and historical prices",
        "default_port": 8002,
        "dependencies": ["auth"]
    },
    "trade": {
        "name": "Trade Service",
        "description": "Executes trades and manages positions",
        "default_port": 8003,
        "dependencies": ["auth", "strategy", "data"]
    },
    "backtest": {
        "name": "Backtest Service",
        "description": "Runs strategy backtests on historical data",
        "default_port": 8004,
        "dependencies": ["auth", "strategy", "data"]
    },
    "dashboard": {
        "name": "Dashboard",
        "description": "Web interface for monitoring and control",
        "default_port": 8080,
        "dependencies": ["auth", "strategy", "data", "trade"]
    }
}

# MCP Services
MCP_SERVICES = [
    "exchange-gateway",
    "market-data",
    "order-execution",
    "paper-trading",
    "portfolio-management",
    "reporting",
    "risk-management",
    "strategy-execution"
]
class ServiceController:
    """Controls service lifecycle using either direct imports or subprocess"""
    
    def __init__(self, use_direct_import=True):
        self.use_direct_import = use_direct_import and DIRECT_IMPORT
        self.service_manager = None
        self.config_manager = None
        self.processes = {}
        self.status_callbacks = []
        self.running = False
        
    def initialize(self, environment="dev", profile="default"):
        """Initialize the service controller"""
        if self.use_direct_import:
            try:
                self.config_manager = ConfigManager.create_default()
                self.config_manager.set_environment(environment)
                self.config_manager.set_profile(profile)
                config = self.config_manager.get_config()
                self.service_manager = ServiceManager(config)
                return True
            except Exception as e:
                logger.error(f"Error initializing service controller: {e}")
                self.use_direct_import = False
                return False
        return True
    
    def start_service(self, service_name):
        """Start a service"""
        if self.use_direct_import and self.service_manager:
            try:
                lifecycle_controller = self.service_manager.get_lifecycle_controller()
                success = lifecycle_controller.start_service(service_name)
                return success
            except Exception as e:
                logger.error(f"Error starting service {service_name}: {e}")
                return False
        else:
            try:
                # Use subprocess to start the service
                cmd = [sys.executable, "main.py", "--service", service_name]
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                self.processes[service_name] = process
                
                # Start a thread to read the output
                def read_output():
                    for line in process.stdout:
                        logger.info(f"[{service_name}] {line.strip()}")
                
                threading.Thread(target=read_output, daemon=True).start()
                
                # Wait a bit to see if the process crashes immediately
                time.sleep(2)
                if process.poll() is not None:
                    logger.error(f"Service {service_name} failed to start")
                    return False
                
                return True
            except Exception as e:
                logger.error(f"Error starting service {service_name}: {e}")
                return False
    
    def stop_service(self, service_name):
        """Stop a service"""
        if self.use_direct_import and self.service_manager:
            try:
                lifecycle_controller = self.service_manager.get_lifecycle_controller()
                success = lifecycle_controller.stop_service(service_name)
                return success
            except Exception as e:
                logger.error(f"Error stopping service {service_name}: {e}")
                return False
        else:
            try:
                # Use subprocess to stop the service
                if service_name in self.processes:
                    process = self.processes[service_name]
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    del self.processes[service_name]
                return True
            except Exception as e:
                logger.error(f"Error stopping service {service_name}: {e}")
                return False
    
    def get_service_status(self, service_name):
        """Get the status of a service"""
        if self.use_direct_import and self.service_manager:
            try:
                registry = self.service_manager.get_registry()
                try:
                    service = registry.get_service(service_name)
                    return service.status.value
                except ValueError:
                    return "not_registered"
            except Exception as e:
                logger.error(f"Error getting status for service {service_name}: {e}")
                return "unknown"
        else:
            # Check if the process is running
            if service_name in self.processes:
                process = self.processes[service_name]
                if process.poll() is None:
                    return "running"
                else:
                    return "stopped"
            else:
                # Check if the service is running by checking the port
                port = SERVICE_INFO.get(service_name, {}).get("default_port")
                if port and self.is_port_in_use(port):
                    return "running"
                return "stopped"
    
    def start_all_services(self, services):
        """Start all selected services"""
        success = True
        for service_name in services:
            if not self.start_service(service_name):
                success = False
        return success
    
    def stop_all_services(self):
        """Stop all running services"""
        if self.use_direct_import and self.service_manager:
            try:
                self.service_manager.stop()
                return True
            except Exception as e:
                logger.error(f"Error stopping all services: {e}")
                return False
        else:
            try:
                for service_name in list(self.processes.keys()):
                    self.stop_service(service_name)
                return True
            except Exception as e:
                logger.error(f"Error stopping all services: {e}")
                return False
    
    def start_dashboard(self):
        """Start the dashboard"""
        if self.use_direct_import:
            try:
                # Use subprocess for the dashboard even with direct import
                cmd = [sys.executable, "main.py", "--dashboard"]
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                self.processes["dashboard"] = process
                
                # Start a thread to read the output
                def read_output():
                    for line in process.stdout:
                        logger.info(f"[dashboard] {line.strip()}")
                
                threading.Thread(target=read_output, daemon=True).start()
                
                # Wait a bit to see if the process crashes immediately
                time.sleep(2)
                if process.poll() is not None:
                    logger.error("Dashboard failed to start")
                    return False
                
                return True
            except Exception as e:
                logger.error(f"Error starting dashboard: {e}")
                return False
        else:
            return self.start_service("dashboard")
    
    def register_status_callback(self, callback):
        """Register a callback for status updates"""
        self.status_callbacks.append(callback)
    
    def start_status_monitoring(self):
        """Start monitoring service status"""
        self.running = True
        
        def monitor_status():
            while self.running:
                statuses = {}
                for service_name in SERVICE_INFO.keys():
                    statuses[service_name] = self.get_service_status(service_name)
                
                for callback in self.status_callbacks:
                    callback(statuses)
                
                time.sleep(2)
        
        threading.Thread(target=monitor_status, daemon=True).start()
    
    def stop_status_monitoring(self):
        """Stop monitoring service status"""
        self.running = False
    
    def is_port_in_use(self, port):
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_all_services()
        self.stop_status_monitoring()


class LogRedirector:
    """Redirects stdout/stderr to a tkinter Text widget"""
    
    def __init__(self, text_widget, tag=None):
        self.text_widget = text_widget
        self.tag = tag
    
    def write(self, string):
        self.text_widget.configure(state=tk.NORMAL)
        if self.tag:
            self.text_widget.insert(tk.END, string, self.tag)
        else:
            self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state=tk.DISABLED)
    
    def flush(self):
        pass
class QuickStartLauncher(tk.Tk):
    """Main application window for the Quick Start Launcher"""
    
    def __init__(self):
        super().__init__()
        
        self.title("CryptoBot Quick Start Launcher")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        # Set icon if available
        try:
            if platform.system() == "Windows":
                self.iconbitmap("static/favicon.ico")
            else:
                # For Linux and macOS
                icon = tk.PhotoImage(file="static/favicon.ico")
                self.iconphoto(True, icon)
        except:
            pass
        
        # Initialize the service controller
        self.service_controller = ServiceController()
        
        # Create the main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create the UI components
        self.create_header()
        self.create_service_selection()
        self.create_config_options()
        self.create_control_buttons()
        self.create_status_display()
        self.create_log_display()
        
        # Initialize the service controller
        self.service_controller.initialize()
        
        # Initialize the update manager
        self.update_manager = None
        if DIRECT_IMPORT:
            try:
                config = {}
                if hasattr(self.service_controller, "config_manager"):
                    config = self.service_controller.config_manager.get_config()
                self.update_manager = UpdateManager(config)
            except Exception as e:
                logger.error(f"Error initializing update manager: {e}")
        
        # Register status callback
        self.service_controller.register_status_callback(self.update_service_status)
        
        # Start status monitoring
        self.service_controller.start_status_monitoring()
        
        # Set up protocol for window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_header(self):
        """Create the header section"""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame, 
            text="CryptoBot Quick Start Launcher", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(
            header_frame, 
            text="v1.0.0", 
            font=("Arial", 10)
        )
        version_label.pack(side=tk.LEFT, padx=(5, 0), pady=(5, 0))
    
    def create_service_selection(self):
        """Create the service selection section"""
        services_frame = ttk.LabelFrame(self.main_frame, text="Services")
        services_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a frame for the services
        self.services_checkboxes = {}
        self.services_vars = {}
        self.services_status_labels = {}
        
        # Create a frame for core services
        core_services_frame = ttk.LabelFrame(services_frame, text="Core Services")
        core_services_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add core services
        core_services = ["auth", "strategy", "data", "trade", "backtest"]
        for i, service_name in enumerate(core_services):
            service_info = SERVICE_INFO[service_name]
            
            # Create a frame for this service
            service_frame = ttk.Frame(core_services_frame)
            service_frame.grid(row=i//3, column=i%3, sticky="w", padx=10, pady=5)
            
            # Create a variable for the checkbox
            var = tk.BooleanVar(value=True)
            self.services_vars[service_name] = var
            
            # Create the checkbox
            cb = ttk.Checkbutton(
                service_frame, 
                text=service_info["name"], 
                variable=var
            )
            cb.grid(row=0, column=0, sticky="w")
            self.services_checkboxes[service_name] = cb
            
            # Create a tooltip label
            tooltip = ttk.Label(
                service_frame, 
                text=service_info["description"],
                font=("Arial", 8),
                foreground="gray"
            )
            tooltip.grid(row=1, column=0, sticky="w")
            
            # Create a status label
            status_label = ttk.Label(
                service_frame, 
                text="Stopped",
                font=("Arial", 8, "bold"),
                foreground="red"
            )
            status_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
            self.services_status_labels[service_name] = status_label
        
        # Create a frame for MCP services
        mcp_services_frame = ttk.LabelFrame(services_frame, text="MCP Services")
        mcp_services_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add MCP services
        for i, service_name in enumerate(MCP_SERVICES):
            display_name = service_name.replace("-", " ").title()
            
            # Create a frame for this service
            service_frame = ttk.Frame(mcp_services_frame)
            service_frame.grid(row=i//4, column=i%4, sticky="w", padx=10, pady=5)
            
            # Create a variable for the checkbox
            var = tk.BooleanVar(value=False)
            self.services_vars[service_name] = var
            
            # Create the checkbox
            cb = ttk.Checkbutton(
                service_frame, 
                text=display_name, 
                variable=var
            )
            cb.grid(row=0, column=0, sticky="w")
            self.services_checkboxes[service_name] = cb
            
            # Create a status label
            status_label = ttk.Label(
                service_frame, 
                text="Stopped",
                font=("Arial", 8, "bold"),
                foreground="red"
            )
            status_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
            self.services_status_labels[service_name] = status_label
        
        # Create a frame for the dashboard
        dashboard_frame = ttk.LabelFrame(services_frame, text="User Interface")
        dashboard_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add dashboard service
        service_name = "dashboard"
        service_info = SERVICE_INFO[service_name]
        
        # Create a frame for the dashboard
        service_frame = ttk.Frame(dashboard_frame)
        service_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create a variable for the checkbox
        var = tk.BooleanVar(value=True)
        self.services_vars[service_name] = var
        
        # Create the checkbox
        cb = ttk.Checkbutton(
            service_frame, 
            text=service_info["name"], 
            variable=var
        )
        cb.pack(side=tk.LEFT)
        self.services_checkboxes[service_name] = cb
        
        # Create a tooltip label
        tooltip = ttk.Label(
            service_frame, 
            text=service_info["description"],
            font=("Arial", 8),
            foreground="gray"
        )
        tooltip.pack(side=tk.LEFT, padx=(5, 0))
        
        # Create a status label
        status_label = ttk.Label(
            service_frame, 
            text="Stopped",
            font=("Arial", 8, "bold"),
            foreground="red"
        )
        status_label.pack(side=tk.LEFT, padx=(10, 0))
        self.services_status_labels[service_name] = status_label
        
        # Create an open button
        open_button = ttk.Button(
            service_frame, 
            text="Open in Browser",
            command=self.open_dashboard
        )
        open_button.pack(side=tk.RIGHT)
    
    def create_config_options(self):
        """Create the configuration options section"""
        config_frame = ttk.LabelFrame(self.main_frame, text="Configuration")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a grid for the options
        options_frame = ttk.Frame(config_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Environment selection
        ttk.Label(options_frame, text="Environment:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.environment_var = tk.StringVar(value="dev")
        environment_combo = ttk.Combobox(
            options_frame, 
            textvariable=self.environment_var,
            values=["dev", "test", "stage", "prod"],
            state="readonly",
            width=10
        )
        environment_combo.grid(row=0, column=1, sticky="w", pady=5)
        
        # Profile selection
        ttk.Label(options_frame, text="Profile:").grid(row=0, column=2, sticky="w", padx=(20, 10), pady=5)
        self.profile_var = tk.StringVar(value="default")
        profile_combo = ttk.Combobox(
            options_frame, 
            textvariable=self.profile_var,
            values=["default", "docker", "kubernetes"],
            state="readonly",
            width=10
        )
        profile_combo.grid(row=0, column=3, sticky="w", pady=5)
        
        # Log level selection
        ttk.Label(options_frame, text="Log Level:").grid(row=0, column=4, sticky="w", padx=(20, 10), pady=5)
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(
            options_frame, 
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=10
        )
        log_level_combo.grid(row=0, column=5, sticky="w", pady=5)
        
        # Apply button
        apply_button = ttk.Button(
            options_frame, 
            text="Apply Configuration",
            command=self.apply_configuration
        )
        apply_button.grid(row=0, column=6, sticky="e", padx=(20, 0), pady=5)
    
    def create_control_buttons(self):
        """Create the control buttons section"""
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Start button
        self.start_button = ttk.Button(
            buttons_frame,
            text="Start Selected Services",
            command=self.start_selected_services,
            style="Accent.TButton"
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Stop button
        self.stop_button = ttk.Button(
            buttons_frame,
            text="Stop All Services",
            command=self.stop_all_services
        )
        self.stop_button.pack(side=tk.LEFT)
        
        # Update button
        self.update_button = ttk.Button(
            buttons_frame,
            text="Check for Updates",
            command=self.check_for_updates
        )
        self.update_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Select all button
        self.select_all_button = ttk.Button(
            buttons_frame,
            text="Select All",
            command=self.select_all_services
        )
        self.select_all_button.pack(side=tk.RIGHT)
        
        # Deselect all button
        self.deselect_all_button = ttk.Button(
            buttons_frame,
            text="Deselect All",
            command=self.deselect_all_services
        )
        self.deselect_all_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_status_display(self):
        """Create the status display section"""
        status_frame = ttk.LabelFrame(self.main_frame, text="Service Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a frame for the status
        self.status_labels = {}
        
        # Create a grid for the status
        grid_frame = ttk.Frame(status_frame)
        grid_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add status for each service
        all_services = list(SERVICE_INFO.keys()) + MCP_SERVICES
        for i, service_name in enumerate(all_services):
            if service_name in SERVICE_INFO:
                display_name = SERVICE_INFO[service_name]["name"]
            else:
                display_name = service_name.replace("-", " ").title()
            
            # Create a label for the service name
            ttk.Label(
                grid_frame, 
                text=f"{display_name}:",
                font=("Arial", 9)
            ).grid(row=i//3, column=(i%3)*2, sticky="w", padx=(10 if i%3 else 0, 5), pady=2)
            
            # Create a label for the status
            status_label = ttk.Label(
                grid_frame, 
                text="Stopped",
                font=("Arial", 9, "bold"),
                foreground="red"
            )
            status_label.grid(row=i//3, column=(i%3)*2+1, sticky="w", pady=2)
            self.status_labels[service_name] = status_label
    
    def create_log_display(self):
        """Create the log display section"""
        log_frame = ttk.LabelFrame(self.main_frame, text="Logs")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a scrolled text widget for the logs
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Redirect stdout and stderr to the log text
        sys.stdout = LogRedirector(self.log_text)
        sys.stderr = LogRedirector(self.log_text, "red")
        
        # Add a welcome message
        self.log_text.insert(tk.END, "Welcome to CryptoBot Quick Start Launcher!\n")
        self.log_text.insert(tk.END, "Select the services you want to start and click 'Start Selected Services'.\n\n")
    
    def update_service_status(self, statuses):
        """Update the service status display"""
        # Use after method to ensure UI updates happen in the main thread
        def update_ui():
            for service_name, status in statuses.items():
                if service_name in self.services_status_labels:
                    label = self.services_status_labels[service_name]
                    if status == "running":
                        label.config(text="Running", foreground="green")
                    elif status == "starting":
                        label.config(text="Starting", foreground="orange")
                    elif status == "stopping":
                        label.config(text="Stopping", foreground="orange")
                    elif status == "error":
                        label.config(text="Error", foreground="red")
                    else:
                        label.config(text="Stopped", foreground="red")
                
                if service_name in self.status_labels:
                    label = self.status_labels[service_name]
                    if status == "running":
                        label.config(text="Running", foreground="green")
                    elif status == "starting":
                        label.config(text="Starting", foreground="orange")
                    elif status == "stopping":
                        label.config(text="Stopping", foreground="orange")
                    elif status == "error":
                        label.config(text="Error", foreground="red")
                    else:
                        label.config(text="Stopped", foreground="red")
        
        # Schedule the UI update on the main thread
        self.after(0, update_ui)
    
    def start_selected_services(self):
        """Start the selected services"""
        selected_services = []
        for service_name, var in self.services_vars.items():
            if var.get():
                selected_services.append(service_name)
        
        if not selected_services:
            messagebox.showwarning("No Services Selected", "Please select at least one service to start.")
            return
        
        # Disable the start button
        self.start_button.config(state="disabled")
        
        # Start the services in a separate thread
        def start_services():
            # Start core services first
            core_services = [s for s in selected_services if s in SERVICE_INFO]
            for service_name in core_services:
                logger.info(f"Starting {service_name} service...")
                if self.service_controller.start_service(service_name):
                    logger.info(f"{service_name} service started successfully")
                else:
                    logger.error(f"Failed to start {service_name} service")
            
            # Start MCP services
            mcp_services = [s for s in selected_services if s in MCP_SERVICES]
            for service_name in mcp_services:
                logger.info(f"Starting {service_name} service...")
                if self.service_controller.start_service(service_name):
                    logger.info(f"{service_name} service started successfully")
                else:
                    logger.error(f"Failed to start {service_name} service")
            
            # Start dashboard if selected
            if "dashboard" in selected_services:
                logger.info("Starting dashboard...")
                if self.service_controller.start_dashboard():
                    logger.info("Dashboard started successfully")
                    # Open the dashboard in the browser using the main thread
                    self.after(1000, self.open_dashboard)
                else:
                    logger.error("Failed to start dashboard")
            
            # Re-enable the start button using the main thread
            self.after(0, lambda: self.start_button.config(state="normal"))
        
        threading.Thread(target=start_services, daemon=True).start()
    
    def stop_all_services(self):
        """Stop all running services"""
        # Disable the stop button
        self.stop_button.config(state="disabled")
        
        # Stop the services in a separate thread
        def stop_services():
            logger.info("Stopping all services...")
            if self.service_controller.stop_all_services():
                logger.info("All services stopped successfully")
            else:
                logger.error("Failed to stop all services")
            
            # Re-enable the stop button using the main thread
            self.after(0, lambda: self.stop_button.config(state="normal"))
        
        threading.Thread(target=stop_services, daemon=True).start()
    
    def select_all_services(self):
        """Select all services"""
        for var in self.services_vars.values():
            var.set(True)
    
    def deselect_all_services(self):
        """Deselect all services"""
        for var in self.services_vars.values():
            var.set(False)
    
    def apply_configuration(self):
        """Apply the configuration options"""
        environment = self.environment_var.get()
        profile = self.profile_var.get()
        log_level = self.log_level_var.get()
        
        logger.info(f"Applying configuration: environment={environment}, profile={profile}, log_level={log_level}")
        
        # Set the log level
        logging.getLogger().setLevel(getattr(logging, log_level))
        
        # Initialize the service controller with the new configuration
        self.service_controller.initialize(environment, profile)
        
        messagebox.showinfo("Configuration Applied", "Configuration has been applied successfully.")
    
    def open_dashboard(self):
        """Open the dashboard in a web browser"""
        dashboard_port = SERVICE_INFO["dashboard"]["default_port"]
        dashboard_url = f"http://localhost:{dashboard_port}"
        
        logger.info(f"Opening dashboard at {dashboard_url}")
        
        try:
            webbrowser.open(dashboard_url)
        except Exception as e:
            logger.error(f"Error opening dashboard: {e}")
            messagebox.showerror("Error", f"Failed to open dashboard: {e}")
    
    def check_for_updates(self):
        """Check for updates"""
        if not self.update_manager:
            messagebox.showinfo("Updates", "Update manager is not available.")
            return
        
        # Show update dialog
        UpdateDialog(self, self.update_manager)
    
    def on_close(self):
        """Handle window close event"""
        if messagebox.askyesno("Quit", "Are you sure you want to quit? All running services will be stopped."):
            logger.info("Shutting down...")
            self.service_controller.cleanup()
            self.destroy()
def main():
    """Main function"""
    # Set up Tkinter styles
    style = ttk.Style()
    if hasattr(style, 'theme_use'):
        try:
            # Try to use a modern theme
            if platform.system() == "Windows":
                style.theme_use('vista')
            elif platform.system() == "Darwin":  # macOS
                style.theme_use('aqua')
            else:  # Linux
                style.theme_use('clam')
        except tk.TclError:
            # Fall back to default theme
            pass
    
    # Create and run the application
    app = QuickStartLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()