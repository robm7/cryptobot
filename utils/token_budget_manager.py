import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class TokenBudgetManager:
    """
    Manages token budget allocation across different components and prioritizes information
    when approaching limits.
    
    This class is responsible for:
    - Tracking token usage across different components
    - Allocating tokens to different processing stages
    - Adjusting verbosity based on available token budget
    - Implementing prioritization logic for critical information
    """
    
    PRIORITY_LEVELS = {
        "critical": 100,   # Test failures and critical errors
        "high": 75,        # Error types and summaries
        "medium": 50,      # Warning messages
        "low": 25,         # Informational messages
        "verbose": 10      # Debug details
    }
    
    def __init__(self, max_token_budget: int = 76659):
        """
        Initialize the token budget manager with a maximum token budget.
        
        Args:
            max_token_budget (int): Maximum number of tokens allowed
        """
        self.max_token_budget = max_token_budget
        self.used_tokens = 0
        self.component_budgets: Dict[str, int] = {}
        self.component_usage: Dict[str, int] = {}
        self.reserve_percentage = 0.1  # Reserve 10% for critical information
        
        # Keep track of prioritized items
        self.prioritized_content: Dict[str, List[Tuple[str, int]]] = {
            level: [] for level in self.PRIORITY_LEVELS.keys()
        }
    
    def allocate_budget(self, components: List[str]) -> Dict[str, int]:
        """
        Allocate token budget to different components based on their importance.
        
        Args:
            components (List[str]): List of component names to allocate budget to
            
        Returns:
            Dict[str, int]: Dictionary mapping component names to their allocated budgets
        """
        # Reserve tokens for critical information
        reserve_tokens = int(self.max_token_budget * self.reserve_percentage)
        available_tokens = self.max_token_budget - reserve_tokens
        
        # Allocate remaining tokens evenly
        per_component = available_tokens // len(components)
        
        # Create allocation
        allocation = {component: per_component for component in components}
        
        # Save allocation
        self.component_budgets = allocation.copy()
        self.component_usage = {component: 0 for component in components}
        
        logger.info(f"Allocated token budget: {allocation}")
        logger.info(f"Reserved tokens for critical information: {reserve_tokens}")
        
        return allocation
    
    def allocate_chunk_budget(self, file_size: int, chunk_size: int, max_chunks: int = None) -> int:
        """
        Allocate token budget for processing file chunks.
        
        Args:
            file_size (int): Size of the file in bytes
            chunk_size (int): Size of each chunk in lines
            max_chunks (int, optional): Maximum number of chunks to process
            
        Returns:
            int: Token budget per chunk
        """
        # Calculate estimated number of chunks
        estimated_chunks = (file_size // (chunk_size * 100)) + 1  # Rough estimate: 100 bytes per line
        
        if max_chunks is not None and estimated_chunks > max_chunks:
            estimated_chunks = max_chunks
        
        # Allocate tokens per chunk, reserving 10% for important information
        chunk_budget = int((self.max_token_budget * 0.9) / estimated_chunks)
        
        logger.info(f"Allocated {chunk_budget} tokens per chunk for {estimated_chunks} estimated chunks")
        return chunk_budget
    
    def track_usage(self, component: str, tokens: int) -> bool:
        """
        Track token usage for a component and check if it's within budget.
        
        Args:
            component (str): Component name
            tokens (int): Number of tokens used
            
        Returns:
            bool: True if within budget, False otherwise
        """
        if component not in self.component_usage:
            self.component_usage[component] = 0
        
        self.component_usage[component] += tokens
        self.used_tokens += tokens
        
        if component in self.component_budgets:
            return self.component_usage[component] <= self.component_budgets[component]
        
        # If no specific budget was allocated, check against total
        return self.used_tokens <= self.max_token_budget
    
    def get_remaining_budget(self, component: Optional[str] = None) -> int:
        """
        Get remaining token budget for a component or overall.
        
        Args:
            component (str, optional): Component name. If None, returns overall remaining budget.
            
        Returns:
            int: Remaining token budget
        """
        if component is not None and component in self.component_budgets:
            used = self.component_usage.get(component, 0)
            return max(0, self.component_budgets[component] - used)
        
        return max(0, self.max_token_budget - self.used_tokens)
    
    def is_within_budget(self, component: Optional[str] = None) -> bool:
        """
        Check if a component is within its allocated budget.
        
        Args:
            component (str, optional): Component name. If None, checks overall budget.
            
        Returns:
            bool: True if within budget, False otherwise
        """
        if component is not None and component in self.component_budgets:
            used = self.component_usage.get(component, 0)
            return used <= self.component_budgets[component]
        
        return self.used_tokens <= self.max_token_budget
    
    def add_prioritized_content(self, content: str, priority_level: str, token_count: int) -> bool:
        """
        Add content with a specific priority level.
        
        Args:
            content (str): The content to add
            priority_level (str): Priority level ("critical", "high", "medium", "low", "verbose")
            token_count (int): Estimated token count for this content
            
        Returns:
            bool: True if content was added, False if rejected due to budget constraints
        """
        if priority_level not in self.PRIORITY_LEVELS:
            logger.warning(f"Invalid priority level: {priority_level}. Using 'medium'.")
            priority_level = "medium"
        
        # Always add critical content
        if priority_level == "critical":
            self.prioritized_content[priority_level].append((content, token_count))
            return True
        
        # For other priorities, check remaining budget
        remaining = self.get_remaining_budget()
        
        # Always keep space for critical content
        critical_reserve = int(self.max_token_budget * self.reserve_percentage)
        effective_remaining = remaining - critical_reserve
        
        if token_count <= effective_remaining:
            self.prioritized_content[priority_level].append((content, token_count))
            return True
        else:
            logger.warning(f"Rejected {priority_level} content due to budget constraints")
            return False
    
    def get_prioritized_content(self) -> List[str]:
        """
        Get all prioritized content in order of priority.
        
        Returns:
            List[str]: Prioritized content
        """
        result = []
        total_tokens = 0
        
        # Add content in order of priority
        for level in sorted(self.PRIORITY_LEVELS.keys(), 
                           key=lambda x: self.PRIORITY_LEVELS[x], reverse=True):
            for content, tokens in self.prioritized_content[level]:
                if total_tokens + tokens <= self.max_token_budget:
                    result.append(content)
                    total_tokens += tokens
                else:
                    # If we're out of budget, only add critical content
                    if level == "critical":
                        result.append(content)
                        total_tokens += tokens
        
        return result
    
    def adjust_verbosity(self, remaining_percentage: float) -> str:
        """
        Adjust verbosity level based on remaining token budget percentage.
        
        Args:
            remaining_percentage (float): Percentage of remaining token budget (0.0-1.0)
            
        Returns:
            str: Verbosity level ("full", "normal", "reduced", "minimal")
        """
        if remaining_percentage >= 0.7:
            return "full"      # Include all information
        elif remaining_percentage >= 0.4:
            return "normal"    # Include most information
        elif remaining_percentage >= 0.2:
            return "reduced"   # Include important information only
        else:
            return "minimal"   # Include critical information only