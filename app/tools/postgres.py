from strands import tool # type: ignore
import psycopg2
import logging
from typing import Dict, Any
from app.config.settings import get_config
from app.services.sql_guardrails import validate_query

logger = logging.getLogger(__name__)

@tool
def run_postgres_query(query: str) -> Dict[str, Any]:
    """
    Execute a SQL query on PostgreSQL database.
    
    Args:
        query: SQL query string to execute
    
    Returns:
        Dict containing either query results or error information
    """
    if not validate_query(query):
        return {
            "success": False,
            "error": "Query blocked by guardrails (only SELECT allowed)",
            "query": query
        }

    config = get_config()
    
    try:
        conn = psycopg2.connect(
            host=config["postgres_host"],
            port=config["postgres_port"],
            database=config["postgres_db"],
            user=config["postgres_user"],
            password=config["postgres_password"]
        )
        
        with conn:
            with conn.cursor() as cursor:
                logger.info(f"Executing Postgres query: {query}")
                cursor.execute(query)
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description] # type: ignore
                    rows = cursor.fetchall()
                    data = [dict(zip(columns, row)) for row in rows] # type: ignore
                    
                    logger.info(f"Query succeeded! Returned {len(data)} rows") # type: ignore
                    return {
                        "success": True,
                        "data": data,
                        "query": query
                    }
                else:
                    return {
                        "success": True,
                        "data": [],
                        "message": "Query executed successfully (no results)",
                        "query": query
                    }
                    
    except psycopg2.Error as e:
        logger.error(f"Postgres query failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }
    finally:
        if 'conn' in locals():
            conn.close() # type: ignore
