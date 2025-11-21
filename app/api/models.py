"""
Models for API responses and requests.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class VisualizationType(str, Enum):
    """Types of visualizations suggested by the agent"""
    TABLE = "table"
    KPI = "kpi"
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    TEXT = "text"


class AgentResponse(BaseModel):
    """Structured response from the NL2SQL agent for React frontend consumption"""
    
    answer: str = Field(
        ..., 
        description="Natural language answer to the user's question"
    )
    
    sql_query: Optional[str] = Field(
        None, 
        description="Generated SQL query for debugging/transparency"
    )
    
    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Raw query results as list of dictionaries"
    )
    
    visualization: VisualizationType = Field(
        default=VisualizationType.TEXT,
        description="Suggested visualization type for the frontend"
    )
    
    row_count: int = Field(
        default=0,
        description="Number of rows returned"
    )
    
    truncated: bool = Field(
        default=False,
        description="Whether results were truncated due to row limit"
    )
    
    success: bool = Field(
        default=True,
        description="Whether the query executed successfully"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if query failed"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (execution time, etc.)"
    )


class AskRequest(BaseModel):
    """Request body for asking questions to the agent"""
    question: str = Field(
        ..., 
        description="Natural language question about the database"
    )
    
    include_sql: bool = Field(
        default=True,
        description="Whether to include the generated SQL in the response"
    )
    
    format_response: bool = Field(
        default=True,
        description="Whether to format the response for visualization"
    )


class AskResponse(BaseModel):
    """Legacy response format for backward compatibility"""
    answer: str
    success: bool = True
