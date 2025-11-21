"""
Tool for retrieving schema information.
"""
from strands import tool # type: ignore
import logging
from typing import List, Dict, Any, Union
from app.services.schema_loader import load_schema, format_schema_for_llm

logger = logging.getLogger(__name__)

@tool
def get_schema(refresh: bool = False) -> str:
    """
    Retrieve the database schema automatically from PostgreSQL.
    
    This tool queries the database's information_schema to extract:
    - All tables in the public schema
    - Column names, types, and nullability
    - Primary keys and foreign keys
    - Table and column comments
    
    Returns a compact string representation of the schema optimized for LLM understanding.
    
    Args:
        refresh (bool): If True, forces a reload of the schema from the database.
                       Otherwise, returns the cached schema if available.
    """
    try:
        logger.info(f"Fetching schema (refresh={refresh})...")
        # Use cache by default, force refresh if requested
        schema_data = load_schema(use_cache=True, force_refresh=refresh)
        
        # Format the schema for the LLM to reduce token usage and latency
        formatted_schema = format_schema_for_llm(schema_data)
        
        logger.info(f"Schema fetched successfully. Size: {len(formatted_schema)} chars")
        return formatted_schema
    except Exception as e:
        logger.error(f"Error fetching schema: {e}")
        return f"Error fetching schema: {str(e)}"
