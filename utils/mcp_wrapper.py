import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class MCPWrapper:
    """
    Wrapper for MCP (Model Context Protocol) server interactions.
    Provides fallback functionality when MCP tools are not available.
    """
    
    def __init__(self):
        """Initialize the MCP wrapper with local storage for fallback functionality."""
        self.mcp_available = self._check_mcp_availability()
        self.local_storage_dir = os.path.join(os.path.dirname(__file__), "../.mcp_local_storage")
        
        if not os.path.exists(self.local_storage_dir):
            os.makedirs(self.local_storage_dir)
            
        # Initialize local storage files
        self.memory_storage_path = os.path.join(self.local_storage_dir, "memory_entities.json")
        self.token_usage_path = os.path.join(self.local_storage_dir, "token_usage.json")
        
        # Initialize storage files if they don't exist
        self._initialize_storage()
    
    def _check_mcp_availability(self) -> bool:
        """Check if MCP tools are available."""
        try:
            # Attempt to import the MCP toolkit
            import roo_toolkit
            return True
        except ImportError:
            logger.warning("roo_toolkit not available. Using local fallback storage.")
            return False
    
    def _initialize_storage(self):
        """Initialize local storage files if they don't exist."""
        # Initialize memory storage
        if not os.path.exists(self.memory_storage_path):
            with open(self.memory_storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "entities": [],
                    "relations": []
                }, f, indent=2)
        
        # Initialize token usage storage
        if not os.path.exists(self.token_usage_path):
            with open(self.token_usage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "budget": 76659,
                    "current_usage": 0,
                    "usage_history": []
                }, f, indent=2)
    
    def store_entities(self, entities: List[Dict[str, Any]]) -> bool:
        """
        Store entities in Memory_Server or local fallback.
        
        Args:
            entities: List of entity dictionaries with name, entityType, and observations
            
        Returns:
            bool: Success status
        """
        if self.mcp_available:
            try:
                # Use MCP to store entities
                from roo_toolkit import use_mcp_tool
                
                result = use_mcp_tool(
                    server_name="Memory_Server",
                    tool_name="create_entities",
                    arguments={"entities": entities}
                )
                
                return True
            except Exception as e:
                logger.error(f"Error using Memory_Server MCP: {str(e)}")
                logger.info("Falling back to local storage")
        
        # Fallback to local storage
        try:
            with open(self.memory_storage_path, 'r', encoding='utf-8') as f:
                storage = json.load(f)
            
            # Add new entities
            storage["entities"].extend(entities)
            
            # Save updated storage
            with open(self.memory_storage_path, 'w', encoding='utf-8') as f:
                json.dump(storage, f, indent=2)
            
            logger.info(f"Stored {len(entities)} entities in local storage")
            return True
        except Exception as e:
            logger.error(f"Error using local storage for entities: {str(e)}")
            return False
    
    def store_relations(self, relations: List[Dict[str, str]]) -> bool:
        """
        Store relations in Memory_Server or local fallback.
        
        Args:
            relations: List of relation dictionaries with from, to, and relationType
            
        Returns:
            bool: Success status
        """
        if self.mcp_available:
            try:
                # Use MCP to store relations
                from roo_toolkit import use_mcp_tool
                
                result = use_mcp_tool(
                    server_name="Memory_Server",
                    tool_name="create_relations",
                    arguments={"relations": relations}
                )
                
                return True
            except Exception as e:
                logger.error(f"Error using Memory_Server MCP: {str(e)}")
                logger.info("Falling back to local storage")
        
        # Fallback to local storage
        try:
            with open(self.memory_storage_path, 'r', encoding='utf-8') as f:
                storage = json.load(f)
            
            # Add new relations
            storage["relations"].extend(relations)
            
            # Save updated storage
            with open(self.memory_storage_path, 'w', encoding='utf-8') as f:
                json.dump(storage, f, indent=2)
            
            logger.info(f"Stored {len(relations)} relations in local storage")
            return True
        except Exception as e:
            logger.error(f"Error using local storage for relations: {str(e)}")
            return False
    
    def track_token_usage(self, tokens: int, service: str = "OpenAI") -> Tuple[bool, bool]:
        """
        Track token usage with API_Monitoring MCP or local fallback.
        
        Args:
            tokens: Number of tokens to track
            service: Service name
            
        Returns:
            Tuple[bool, bool]: (tracking_success, under_budget)
        """
        if self.mcp_available:
            try:
                # Use MCP to track token usage
                from roo_toolkit import use_mcp_tool
                
                # Track API call
                track_result = use_mcp_tool(
                    server_name="API_Monitoring",
                    tool_name="track_api_call",
                    arguments={
                        "service": service,
                        "endpoint": "/v1/chat/completions",
                        "method": "POST",
                        "cost": tokens * 0.000002,  # Approximate cost
                        "environment": "development"
                    }
                )
                
                # Get usage report
                usage_report = use_mcp_tool(
                    server_name="API_Monitoring",
                    tool_name="get_usage_report",
                    arguments={
                        "period": "day",
                        "environment": "all"
                    }
                )
                
                total_usage = usage_report.get("total_tokens", 0)
                budget = 76659  # Default budget
                
                # Get budget from API_Monitoring if available
                try:
                    budget_info = use_mcp_tool(
                        server_name="API_Monitoring",
                        tool_name="get_budget_thresholds",
                        arguments={}
                    )
                    if budget_info and service in budget_info:
                        budget = budget_info[service]
                except Exception:
                    logger.warning("Could not retrieve budget from API_Monitoring")
                
                under_budget = total_usage < budget
                return True, under_budget
            
            except Exception as e:
                logger.error(f"Error using API_Monitoring MCP: {str(e)}")
                logger.info("Falling back to local storage")
        
        # Fallback to local storage
        try:
            with open(self.token_usage_path, 'r', encoding='utf-8') as f:
                usage_data = json.load(f)
            
            # Update token usage
            usage_data["current_usage"] += tokens
            
            # Add usage record
            usage_data["usage_history"].append({
                "timestamp": datetime.now().isoformat(),
                "tokens": tokens,
                "service": service
            })
            
            # Check if we're under budget
            under_budget = usage_data["current_usage"] < usage_data["budget"]
            
            # Save updated usage data
            with open(self.token_usage_path, 'w', encoding='utf-8') as f:
                json.dump(usage_data, f, indent=2)
            
            logger.info(f"Tracked {tokens} tokens in local storage. " + 
                       f"Current usage: {usage_data['current_usage']}/{usage_data['budget']}")
            
            return True, under_budget
        
        except Exception as e:
            logger.error(f"Error using local storage for token tracking: {str(e)}")
            return False, True  # Assume under budget on error
    
    def set_token_budget(self, budget: int, service: str = "OpenAI") -> bool:
        """
        Set token budget with API_Monitoring MCP or local fallback.
        
        Args:
            budget: Budget threshold in tokens
            service: Service name
            
        Returns:
            bool: Success status
        """
        if self.mcp_available:
            try:
                # Use MCP to set budget threshold
                from roo_toolkit import use_mcp_tool
                
                set_result = use_mcp_tool(
                    server_name="API_Monitoring",
                    tool_name="set_budget_threshold",
                    arguments={
                        "service": service,
                        "threshold": budget
                    }
                )
                
                return True
            except Exception as e:
                logger.error(f"Error using API_Monitoring MCP: {str(e)}")
                logger.info("Falling back to local storage")
        
        # Fallback to local storage
        try:
            with open(self.token_usage_path, 'r', encoding='utf-8') as f:
                usage_data = json.load(f)
            
            # Update budget
            usage_data["budget"] = budget
            
            # Save updated usage data
            with open(self.token_usage_path, 'w', encoding='utf-8') as f:
                json.dump(usage_data, f, indent=2)
            
            logger.info(f"Set token budget to {budget} in local storage")
            return True
        
        except Exception as e:
            logger.error(f"Error setting budget in local storage: {str(e)}")
            return False
    
    def get_memory_entities(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get entities from Memory_Server or local fallback.
        
        Args:
            query: Optional search query
            
        Returns:
            List[Dict[str, Any]]: List of matching entities
        """
        if self.mcp_available:
            try:
                # Use MCP to search nodes or get all
                from roo_toolkit import use_mcp_tool
                
                if query:
                    result = use_mcp_tool(
                        server_name="Memory_Server",
                        tool_name="search_nodes",
                        arguments={"query": query}
                    )
                else:
                    result = use_mcp_tool(
                        server_name="Memory_Server",
                        tool_name="read_graph",
                        arguments={}
                    )
                
                return result.get("entities", [])
            
            except Exception as e:
                logger.error(f"Error retrieving from Memory_Server MCP: {str(e)}")
                logger.info("Falling back to local storage")
        
        # Fallback to local storage
        try:
            with open(self.memory_storage_path, 'r', encoding='utf-8') as f:
                storage = json.load(f)
            
            entities = storage.get("entities", [])
            
            # Filter by query if provided
            if query:
                filtered_entities = []
                for entity in entities:
                    # Check if query matches name or observations
                    if (query.lower() in entity.get("name", "").lower() or 
                        any(query.lower() in obs.lower() for obs in entity.get("observations", []))):
                        filtered_entities.append(entity)
                return filtered_entities
            
            return entities
        
        except Exception as e:
            logger.error(f"Error retrieving from local storage: {str(e)}")
            return []
    
    def get_token_usage(self) -> Dict[str, Any]:
        """
        Get token usage from API_Monitoring MCP or local fallback.
        
        Returns:
            Dict[str, Any]: Token usage information
        """
        if self.mcp_available:
            try:
                # Use MCP to get usage report
                from roo_toolkit import use_mcp_tool
                
                usage_report = use_mcp_tool(
                    server_name="API_Monitoring",
                    tool_name="get_usage_report",
                    arguments={
                        "period": "month",
                        "environment": "all"
                    }
                )
                
                return usage_report
            
            except Exception as e:
                logger.error(f"Error retrieving from API_Monitoring MCP: {str(e)}")
                logger.info("Falling back to local storage")
        
        # Fallback to local storage
        try:
            with open(self.token_usage_path, 'r', encoding='utf-8') as f:
                usage_data = json.load(f)
            
            return {
                "current_usage": usage_data["current_usage"],
                "budget": usage_data["budget"],
                "usage_history": usage_data["usage_history"][-10:]  # Return last 10 records
            }
        
        except Exception as e:
            logger.error(f"Error retrieving from local storage: {str(e)}")
            return {
                "current_usage": 0,
                "budget": 76659,
                "usage_history": []
            }