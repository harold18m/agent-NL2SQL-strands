"""
Enhanced agent wrapper that captures tool execution results.
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context object to capture tool execution results during agent run."""
    
    last_sql_query: Optional[str] = None
    last_query_data: List[Dict[str, Any]] = field(default_factory=list)
    last_query_success: bool = False
    last_query_error: Optional[str] = None
    truncated: bool = False
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    def reset(self):
        """Reset context for new query."""
        self.last_sql_query = None
        self.last_query_data = []
        self.last_query_success = False
        self.last_query_error = None
        self.truncated = False
        self.tool_calls = []
    
    def record_sql_execution(self, query: str, result: Dict[str, Any]):
        """Record SQL query execution."""
        self.last_sql_query = query
        
        if result.get("success"):
            self.last_query_success = True
            self.last_query_data = result.get("data", [])
            
            # Check if truncated
            message = result.get("message", "")
            if "truncated" in message.lower():
                self.truncated = True
        else:
            self.last_query_success = False
            self.last_query_error = result.get("error", "Unknown error")
        
        # Record tool call
        self.tool_calls.append({
            "tool": "run_postgres_query",
            "query": query,
            "result": result
        })


# Global context instance (thread-safe in single-threaded FastAPI)
_agent_context = AgentContext()


def get_agent_context() -> AgentContext:
    """Get the global agent context."""
    return _agent_context


def reset_agent_context():
    """Reset the global agent context."""
    _agent_context.reset()
