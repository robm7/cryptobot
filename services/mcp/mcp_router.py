import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

class MCPRouter:
    """Handles routing to appropriate MCP servers based on task and context"""
    
    def __init__(self, config_path: str = ".roo/mcp.json"):
        self.config = self._load_config(config_path)
        self.cache = {}
        
    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load MCP configuration from JSON file"""
        try:
            with open(path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "mcp_routing": {},
                "server_configs": {}
            }
            
    def get_server_for_task(self, task: str, file_path: Optional[str] = None) -> str:
        """Determine which MCP server to use for a given task"""
        # Check cache first
        cache_key = f"{task}:{file_path}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # Check all configured routes
        for server_name, route_config in self.config.get("mcp_routing", {}).items():
            if server_name == "default":
                continue
                
            # Check task content matches
            if any(keyword.lower() in task.lower() 
                  for keyword in route_config.get("conditions", {}).get("task_contains", [])):
                self.cache[cache_key] = server_name
                return server_name
                
            # Check file pattern matches
            if file_path and route_config.get("conditions", {}).get("file_pattern"):
                if Path(file_path).match(route_config["conditions"]["file_pattern"]):
                    self.cache[cache_key] = server_name
                    return server_name
                    
        # Fall back to default
        default_server = self.config.get("mcp_routing", {}).get("default", {}).get("server")
        if default_server:
            self.cache[cache_key] = default_server
            return default_server
            
        raise ValueError("No MCP server configured for this task")
        
    def get_server_config(self, server_name: str) -> Dict[str, Any]:
        """Get configuration for a specific MCP server"""
        return self.config.get("server_configs", {}).get(server_name, {})