"""
Dependency Resolver for CryptoBot.

This module provides the DependencyResolver class, which analyzes service dependencies,
determines the correct startup/shutdown order, prevents circular dependencies,
handles optional service dependencies, and supports dynamic dependency resolution.
"""

import logging
from typing import Dict, List, Set, Optional
from collections import defaultdict

from .registry import ServiceRegistry, ServiceMetadata

logger = logging.getLogger(__name__)

class CircularDependencyError(Exception):
    """Exception raised when a circular dependency is detected."""
    pass


class DependencyResolver:
    """
    Resolver for service dependencies.
    
    The DependencyResolver analyzes service dependencies, determines the correct
    startup/shutdown order, prevents circular dependencies, handles optional
    service dependencies, and supports dynamic dependency resolution.
    """
    
    def __init__(self, registry: ServiceRegistry):
        """
        Initialize the dependency resolver.
        
        Args:
            registry: Service registry
        """
        self._registry = registry
        logger.info("Dependency Resolver initialized")
    
    def get_startup_order(self) -> List[str]:
        """
        Get the order in which services should be started.
        
        Returns:
            List[str]: List of service names in the order they should be started
        
        Raises:
            CircularDependencyError: If a circular dependency is detected
        """
        # Get all registered services
        services = self._registry.get_all_services()
        
        # Build dependency graph
        graph = self._build_dependency_graph(services)
        
        # Check for circular dependencies
        self._check_circular_dependencies(graph)
        
        # Perform topological sort
        return self._topological_sort(graph)
    
    def get_shutdown_order(self) -> List[str]:
        """
        Get the order in which services should be shut down.
        
        Returns:
            List[str]: List of service names in the order they should be shut down
        
        Raises:
            CircularDependencyError: If a circular dependency is detected
        """
        # Shutdown order is the reverse of startup order
        return list(reversed(self.get_startup_order()))
    
    def get_dependencies(self, service_name: str, include_optional: bool = False) -> Set[str]:
        """
        Get the dependencies of a service.
        
        Args:
            service_name: Name of the service
            include_optional: Whether to include optional dependencies
        
        Returns:
            Set[str]: Set of service names that the service depends on
        
        Raises:
            ValueError: If the service is not registered
        """
        service = self._registry.get_service(service_name)
        
        if include_optional:
            return service.dependencies.union(service.optional_dependencies)
        else:
            return service.dependencies.copy()
    
    def get_dependents(self, service_name: str) -> Set[str]:
        """
        Get the services that depend on a service.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Set[str]: Set of service names that depend on the service
        
        Raises:
            ValueError: If the service is not registered
        """
        dependents = set()
        
        for name, service in self._registry.get_all_services().items():
            if service_name in service.dependencies:
                dependents.add(name)
        
        return dependents
    
    def check_dependencies(self, service_name: str) -> Dict[str, bool]:
        """
        Check if the dependencies of a service are available.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Dict[str, bool]: Dictionary mapping dependency names to availability
        
        Raises:
            ValueError: If the service is not registered
        """
        service = self._registry.get_service(service_name)
        result = {}
        
        # Check required dependencies
        for dependency in service.dependencies:
            try:
                result[dependency] = self._registry.is_service_running(dependency)
            except ValueError:
                # Dependency is not registered
                result[dependency] = False
        
        # Check optional dependencies
        for dependency in service.optional_dependencies:
            try:
                result[dependency] = self._registry.is_service_running(dependency)
            except ValueError:
                # Optional dependency is not registered
                result[dependency] = False
        
        return result
    
    def can_start_service(self, service_name: str) -> bool:
        """
        Check if a service can be started.
        
        A service can be started if all its required dependencies are running.
        
        Args:
            service_name: Name of the service
        
        Returns:
            bool: True if the service can be started, False otherwise
        
        Raises:
            ValueError: If the service is not registered
        """
        service = self._registry.get_service(service_name)
        
        # Check if all required dependencies are running
        for dependency in service.dependencies:
            try:
                if not self._registry.is_service_running(dependency):
                    return False
            except ValueError:
                # Dependency is not registered
                return False
        
        return True
    
    def _build_dependency_graph(self, services: Dict[str, ServiceMetadata]) -> Dict[str, Set[str]]:
        """
        Build a dependency graph from the services.
        
        Args:
            services: Dictionary of service metadata
        
        Returns:
            Dict[str, Set[str]]: Dependency graph
        """
        graph = defaultdict(set)
        
        for name, service in services.items():
            # Add the service to the graph
            if name not in graph:
                graph[name] = set()
            
            # Add dependencies
            for dependency in service.dependencies:
                graph[name].add(dependency)
                
                # Ensure the dependency is in the graph
                if dependency not in graph:
                    graph[dependency] = set()
        
        return graph
    
    def _check_circular_dependencies(self, graph: Dict[str, Set[str]]) -> None:
        """
        Check for circular dependencies in the graph.
        
        Args:
            graph: Dependency graph
        
        Raises:
            CircularDependencyError: If a circular dependency is detected
        """
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                cycle = self._find_cycle(graph, node)
                raise CircularDependencyError(f"Circular dependency detected: {' -> '.join(cycle)}")
            
            if node in visited:
                return
            
            temp_visited.add(node)
            
            for neighbor in graph[node]:
                visit(neighbor)
            
            temp_visited.remove(node)
            visited.add(node)
        
        for node in graph:
            if node not in visited:
                visit(node)
    
    def _find_cycle(self, graph: Dict[str, Set[str]], start: str) -> List[str]:
        """
        Find a cycle in the graph starting from a node.
        
        Args:
            graph: Dependency graph
            start: Starting node
        
        Returns:
            List[str]: List of nodes in the cycle
        """
        visited = {start}
        path = [start]
        
        def dfs(node):
            for neighbor in graph[node]:
                if neighbor == start:
                    path.append(neighbor)
                    return True
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    
                    if dfs(neighbor):
                        return True
                    
                    path.pop()
                    visited.remove(neighbor)
            
            return False
        
        dfs(start)
        return path
    
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """
        Perform a topological sort on the graph.
        
        Args:
            graph: Dependency graph
        
        Returns:
            List[str]: List of nodes in topological order
        """
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                return
            
            if node in visited:
                return
            
            temp_visited.add(node)
            
            for neighbor in graph[node]:
                visit(neighbor)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in graph:
            if node not in visited:
                visit(node)
        
        return list(reversed(result))