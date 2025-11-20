import logging

logger = logging.getLogger(__name__)

def is_readonly_query(query: str) -> bool:
    """
    Check if the query is a read-only query (SELECT).
    """
    query_upper = query.strip().upper()
    # Basic check, can be improved with sqlparse
    return query_upper.startswith(('SELECT', 'WITH', 'EXPLAIN'))

def validate_query(query: str) -> bool:
    """
    Validate that the query is safe to execute.
    """
    if not is_readonly_query(query):
        logger.warning(f"Blocked potentially unsafe query: {query}")
        return False
    return True
