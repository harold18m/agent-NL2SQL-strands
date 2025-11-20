"""
Tool for retrieving schema information.
"""
from strands import tool # type: ignore
import logging
from typing import List, Dict, Any
from app.services.schema_loader import load_schema

logger = logging.getLogger(__name__)

@tool
def get_schema(refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieve the database schema automatically from PostgreSQL.
    
    This tool queries the database's information_schema to extract:
    - All tables in the public schema
    - Column names, types, and nullability
    - Primary keys and foreign keys
    - Table and column comments
    
    Args:
        refresh: Whether to force a refresh of the schema from the database.
                 If False, uses cached schema (if available).
        
    Returns:
        List of table definitions with complete metadata
    """
    logger.info(f"Retrieving database schema (refresh={refresh})")
    return load_schema(use_cache=True, force_refresh=refresh)
