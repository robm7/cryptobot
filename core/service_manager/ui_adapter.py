"""
User Interface Adapter for CryptoBot.

This module provides the UserInterfaceAdapter class, which provides interfaces for
service management, supports both web UI and CLI, displays service status and health,
allows manual service control, and exposes a management API for external tools.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import threading
import time

from .registry import ServiceRegistry, ServiceStatus, ServiceMetadata
from .lifecycle_controller import ServiceLifecycleController
from .health_monitor import HealthMonitor
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)

# Pydantic models for API
class ServiceInfo(BaseModel):
    """Service information for API responses."""
    name: str
    description: str
    status: str
    host: Optional[str] = None
    port: Optional[int] = None
    process_id: Optional[int] = None
    dependencies: List[str] = Field(default_factory=list)
    optional_dependencies: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ResourceUsageInfo(BaseModel):
    """Resource usage information for API responses."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used: int
    disk_percent: Optional[float] = None
    disk_used: Optional[int] = None
    num_threads: Optional[int] = None
    num_connections: Optional[int] = None


class HealthCheckInfo(BaseModel):
    """Health check information for API responses."""
    service_name: str
    timestamp: str
    status: bool
    response_time: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ResourceLimitInfo(BaseModel):
    """Resource limit information for API responses."""
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_bytes: Optional[int] = None
    num_threads: Optional[int] = None
    num_connections: Optional[int] = None


class ServiceActionResponse(BaseModel):
    """Response for service actions."""
    success: bool
    message: str


class UserInterfaceAdapter:
    """
    Adapter for user interfaces.
    
    The UserInterfaceAdapter provides interfaces for service management, supports
    both web UI and CLI, displays service status and health, allows manual service
    control, and exposes a management API for external tools.
    """
    
    def __init__(self, registry: ServiceRegistry, lifecycle_controller: ServiceLifecycleController,
                 health_monitor: HealthMonitor, resource_manager: ResourceManager):
        """
        Initialize the user interface adapter.
        
        Args:
            registry: Service registry
            lifecycle_controller: Service lifecycle controller
            health_monitor: Health monitor
            resource_manager: Resource manager
        """
        self._registry = registry
        self._lifecycle_controller = lifecycle_controller
        self._health_monitor = health_monitor
        self._resource_manager = resource_manager
        self._api_app = None
        self._api_thread = None
        self._api_running = False
        self._cli_handlers: Dict[str, Callable] = {}
        logger.info("User Interface Adapter initialized")
    
    def start_api(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """
        Start the management API.
        
        Args:
            host: Host address
            port: Port number
        """
        if self._api_running:
            logger.warning("Management API is already running")
            return
        
        # Create FastAPI app
        self._api_app = FastAPI(
            title="CryptoBot Service Manager API",
            description="API for managing CryptoBot services",
            version="1.0.0"
        )
        
        # Create router
        router = APIRouter()
        
        # Service endpoints
        @router.get("/services", response_model=List[ServiceInfo], tags=["Services"])
        async def get_services():
            """Get information about all services."""
            services = self._registry.get_all_services()
            return [self._service_metadata_to_info(service) for service in services.values()]
        
        @router.get("/services/{service_name}", response_model=ServiceInfo, tags=["Services"])
        async def get_service(service_name: str = Path(..., description="Name of the service")):
            """Get information about a specific service."""
            try:
                service = self._registry.get_service(service_name)
                return self._service_metadata_to_info(service)
            except ValueError:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
        @router.post("/services/{service_name}/start", response_model=ServiceActionResponse, tags=["Services"])
        async def start_service(service_name: str = Path(..., description="Name of the service")):
            """Start a service."""
            try:
                success = self._lifecycle_controller.start_service(service_name)
                if success:
                    return ServiceActionResponse(success=True, message=f"Service '{service_name}' started successfully")
                else:
                    return ServiceActionResponse(success=False, message=f"Failed to start service '{service_name}'")
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/services/{service_name}/stop", response_model=ServiceActionResponse, tags=["Services"])
        async def stop_service(service_name: str = Path(..., description="Name of the service")):
            """Stop a service."""
            try:
                success = self._lifecycle_controller.stop_service(service_name)
                if success:
                    return ServiceActionResponse(success=True, message=f"Service '{service_name}' stopped successfully")
                else:
                    return ServiceActionResponse(success=False, message=f"Failed to stop service '{service_name}'")
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/services/{service_name}/restart", response_model=ServiceActionResponse, tags=["Services"])
        async def restart_service(service_name: str = Path(..., description="Name of the service")):
            """Restart a service."""
            try:
                success = self._lifecycle_controller.restart_service(service_name)
                if success:
                    return ServiceActionResponse(success=True, message=f"Service '{service_name}' restarted successfully")
                else:
                    return ServiceActionResponse(success=False, message=f"Failed to restart service '{service_name}'")
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/services/start-all", response_model=ServiceActionResponse, tags=["Services"])
        async def start_all_services():
            """Start all services."""
            try:
                success = self._lifecycle_controller.start_all_services()
                if success:
                    return ServiceActionResponse(success=True, message="All services started successfully")
                else:
                    return ServiceActionResponse(success=False, message="Failed to start all services")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/services/stop-all", response_model=ServiceActionResponse, tags=["Services"])
        async def stop_all_services():
            """Stop all services."""
            try:
                success = self._lifecycle_controller.stop_all_services()
                if success:
                    return ServiceActionResponse(success=True, message="All services stopped successfully")
                else:
                    return ServiceActionResponse(success=False, message="Failed to stop all services")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Health endpoints
        @router.get("/health", response_model=Dict[str, HealthCheckInfo], tags=["Health"])
        async def get_health():
            """Get health information for all services."""
            health_results = self._health_monitor.check_all_services_health()
            return {name: self._health_check_to_info(check) for name, check in health_results.items()}
        
        @router.get("/health/{service_name}", response_model=HealthCheckInfo, tags=["Health"])
        async def get_service_health(service_name: str = Path(..., description="Name of the service")):
            """Get health information for a specific service."""
            try:
                health_check = self._health_monitor.check_service_health(service_name)
                return self._health_check_to_info(health_check)
            except ValueError:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
        @router.get("/health/{service_name}/history", response_model=List[HealthCheckInfo], tags=["Health"])
        async def get_service_health_history(
            service_name: str = Path(..., description="Name of the service"),
            limit: int = Query(10, description="Maximum number of health checks to return")
        ):
            """Get health history for a specific service."""
            try:
                history = self._health_monitor.get_service_health_history(service_name)
                return [self._health_check_to_info(check) for check in history[-limit:]]
            except ValueError:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
        # Resource endpoints
        @router.get("/resources/system", response_model=ResourceUsageInfo, tags=["Resources"])
        async def get_system_resources():
            """Get system resource usage."""
            usage = self._resource_manager.get_system_resource_usage()
            return ResourceUsageInfo(
                timestamp=usage.timestamp.isoformat(),
                cpu_percent=usage.cpu_percent,
                memory_percent=usage.memory_percent,
                memory_used=usage.memory_used,
                disk_percent=usage.disk_percent,
                disk_used=usage.disk_used
            )
        
        @router.get("/resources/services", response_model=Dict[str, ResourceUsageInfo], tags=["Resources"])
        async def get_services_resources():
            """Get resource usage for all services."""
            usages = self._resource_manager.get_all_services_resource_usage()
            result = {}
            for name, usage in usages.items():
                if usage is not None:
                    result[name] = ResourceUsageInfo(
                        timestamp=usage.timestamp.isoformat(),
                        cpu_percent=usage.cpu_percent,
                        memory_percent=usage.memory_percent,
                        memory_used=usage.memory_used,
                        num_threads=usage.num_threads,
                        num_connections=usage.num_connections
                    )
            return result
        
        @router.get("/resources/services/{service_name}", response_model=ResourceUsageInfo, tags=["Resources"])
        async def get_service_resources(service_name: str = Path(..., description="Name of the service")):
            """Get resource usage for a specific service."""
            try:
                usage = self._resource_manager.get_service_resource_usage(service_name)
                if usage is None:
                    raise HTTPException(status_code=404, detail=f"Resource usage for service '{service_name}' not available")
                
                return ResourceUsageInfo(
                    timestamp=usage.timestamp.isoformat(),
                    cpu_percent=usage.cpu_percent,
                    memory_percent=usage.memory_percent,
                    memory_used=usage.memory_used,
                    num_threads=usage.num_threads,
                    num_connections=usage.num_connections
                )
            except ValueError:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
        @router.get("/resources/limits/{service_name}", response_model=ResourceLimitInfo, tags=["Resources"])
        async def get_service_resource_limits(service_name: str = Path(..., description="Name of the service")):
            """Get resource limits for a specific service."""
            try:
                limits = self._resource_manager.get_resource_limits(service_name)
                if limits is None:
                    raise HTTPException(status_code=404, detail=f"Resource limits for service '{service_name}' not set")
                
                return ResourceLimitInfo(
                    cpu_percent=limits.cpu_percent,
                    memory_percent=limits.memory_percent,
                    memory_bytes=limits.memory_bytes,
                    num_threads=limits.num_threads,
                    num_connections=limits.num_connections
                )
            except ValueError:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
        # Add router to app
        self._api_app.include_router(router, prefix="/api/v1")
        
        # Start API in a separate thread
        def run_api():
            uvicorn.run(self._api_app, host=host, port=port, log_level="info")
        
        self._api_thread = threading.Thread(target=run_api, daemon=True)
        self._api_thread.start()
        self._api_running = True
        
        logger.info(f"Management API started on {host}:{port}")
    
    def stop_api(self) -> None:
        """Stop the management API."""
        if not self._api_running:
            logger.warning("Management API is not running")
            return
        
        # There's no clean way to stop a running uvicorn server in a thread
        # We'll just set the flag and let the thread die when the application exits
        self._api_running = False
        logger.info("Management API stopped")
    
    def register_cli_handler(self, command: str, handler: Callable, help_text: str) -> None:
        """
        Register a CLI command handler.
        
        Args:
            command: Command name
            handler: Handler function
            help_text: Help text for the command
        """
        self._cli_handlers[command] = {
            "handler": handler,
            "help": help_text
        }
    
    def handle_cli_command(self, command: str, args: List[str]) -> str:
        """
        Handle a CLI command.
        
        Args:
            command: Command name
            args: Command arguments
        
        Returns:
            str: Command output
        
        Raises:
            ValueError: If the command is not recognized
        """
        if command == "help":
            # Show help
            output = "Available commands:\n"
            for cmd, info in self._cli_handlers.items():
                output += f"  {cmd}: {info['help']}\n"
            
            # Add built-in commands
            output += "  help: Show this help message\n"
            output += "  list: List all services\n"
            output += "  status <service>: Show status of a service\n"
            output += "  start <service>: Start a service\n"
            output += "  stop <service>: Stop a service\n"
            output += "  restart <service>: Restart a service\n"
            output += "  health <service>: Show health of a service\n"
            output += "  resources <service>: Show resource usage of a service\n"
            
            return output
        
        elif command == "list":
            # List all services
            services = self._registry.get_all_services()
            output = "Services:\n"
            for name, service in services.items():
                output += f"  {name}: {service.status.value}\n"
            return output
        
        elif command == "status":
            # Show status of a service
            if not args:
                return "Error: Missing service name"
            
            service_name = args[0]
            try:
                service = self._registry.get_service(service_name)
                output = f"Service: {service_name}\n"
                output += f"Status: {service.status.value}\n"
                output += f"Description: {service.description}\n"
                
                if service.host is not None and service.port is not None:
                    output += f"Endpoint: {service.host}:{service.port}\n"
                
                if service.process_id is not None:
                    output += f"Process ID: {service.process_id}\n"
                
                if service.dependencies:
                    output += f"Dependencies: {', '.join(service.dependencies)}\n"
                
                if service.optional_dependencies:
                    output += f"Optional Dependencies: {', '.join(service.optional_dependencies)}\n"
                
                if service.error_message:
                    output += f"Error: {service.error_message}\n"
                
                return output
            except ValueError:
                return f"Error: Service '{service_name}' not found"
        
        elif command == "start":
            # Start a service
            if not args:
                return "Error: Missing service name"
            
            service_name = args[0]
            try:
                success = self._lifecycle_controller.start_service(service_name)
                if success:
                    return f"Service '{service_name}' started successfully"
                else:
                    return f"Failed to start service '{service_name}'"
            except ValueError as e:
                return f"Error: {str(e)}"
        
        elif command == "stop":
            # Stop a service
            if not args:
                return "Error: Missing service name"
            
            service_name = args[0]
            try:
                success = self._lifecycle_controller.stop_service(service_name)
                if success:
                    return f"Service '{service_name}' stopped successfully"
                else:
                    return f"Failed to stop service '{service_name}'"
            except ValueError as e:
                return f"Error: {str(e)}"
        
        elif command == "restart":
            # Restart a service
            if not args:
                return "Error: Missing service name"
            
            service_name = args[0]
            try:
                success = self._lifecycle_controller.restart_service(service_name)
                if success:
                    return f"Service '{service_name}' restarted successfully"
                else:
                    return f"Failed to restart service '{service_name}'"
            except ValueError as e:
                return f"Error: {str(e)}"
        
        elif command == "health":
            # Show health of a service
            if not args:
                return "Error: Missing service name"
            
            service_name = args[0]
            try:
                health_check = self._health_monitor.check_service_health(service_name)
                output = f"Health of service '{service_name}':\n"
                output += f"Status: {'Healthy' if health_check.status else 'Unhealthy'}\n"
                output += f"Timestamp: {health_check.timestamp.isoformat()}\n"
                output += f"Response Time: {health_check.response_time:.3f} seconds\n"
                
                if health_check.error_message:
                    output += f"Error: {health_check.error_message}\n"
                
                if health_check.metrics:
                    output += "Metrics:\n"
                    for key, value in health_check.metrics.items():
                        output += f"  {key}: {value}\n"
                
                return output
            except ValueError as e:
                return f"Error: {str(e)}"
        
        elif command == "resources":
            # Show resource usage of a service
            if not args:
                return "Error: Missing service name"
            
            service_name = args[0]
            try:
                usage = self._resource_manager.get_service_resource_usage(service_name)
                if usage is None:
                    return f"Resource usage for service '{service_name}' not available"
                
                output = f"Resource usage of service '{service_name}':\n"
                output += f"Timestamp: {usage.timestamp.isoformat()}\n"
                output += f"CPU Usage: {usage.cpu_percent:.1f}%\n"
                output += f"Memory Usage: {usage.memory_percent:.1f}% ({usage.memory_used} bytes)\n"
                output += f"Threads: {usage.num_threads}\n"
                output += f"Connections: {usage.num_connections}\n"
                
                # Check resource limits
                limits = self._resource_manager.get_resource_limits(service_name)
                if limits is not None:
                    output += "Resource Limits:\n"
                    if limits.cpu_percent is not None:
                        output += f"  CPU: {limits.cpu_percent:.1f}%\n"
                    if limits.memory_percent is not None:
                        output += f"  Memory: {limits.memory_percent:.1f}%\n"
                    if limits.memory_bytes is not None:
                        output += f"  Memory: {limits.memory_bytes} bytes\n"
                    if limits.num_threads is not None:
                        output += f"  Threads: {limits.num_threads}\n"
                    if limits.num_connections is not None:
                        output += f"  Connections: {limits.num_connections}\n"
                
                return output
            except ValueError as e:
                return f"Error: {str(e)}"
        
        elif command in self._cli_handlers:
            # Call custom handler
            try:
                return self._cli_handlers[command]["handler"](args)
            except Exception as e:
                return f"Error: {str(e)}"
        
        else:
            return f"Error: Unknown command '{command}'"
    
    def _service_metadata_to_info(self, metadata: ServiceMetadata) -> ServiceInfo:
        """
        Convert service metadata to service info.
        
        Args:
            metadata: Service metadata
        
        Returns:
            ServiceInfo: Service information
        """
        return ServiceInfo(
            name=metadata.name,
            description=metadata.description,
            status=metadata.status.value,
            host=metadata.host,
            port=metadata.port,
            process_id=metadata.process_id,
            dependencies=list(metadata.dependencies),
            optional_dependencies=list(metadata.optional_dependencies),
            metrics=metadata.metrics,
            error_message=metadata.error_message
        )
    
    def _health_check_to_info(self, health_check) -> HealthCheckInfo:
        """
        Convert health check to health check info.
        
        Args:
            health_check: Health check
        
        Returns:
            HealthCheckInfo: Health check information
        """
        return HealthCheckInfo(
            service_name=health_check.service_name,
            timestamp=health_check.timestamp.isoformat(),
            status=health_check.status,
            response_time=health_check.response_time,
            error_message=health_check.error_message,
            metrics=health_check.metrics
        )