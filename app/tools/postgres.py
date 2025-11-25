from strands import tool # type: ignore
import psycopg2
import logging
from typing import Dict, Any
from app.config.settings import get_config
from app.config.database import get_db_connection
from app.services.sql_guardrails import validate_query
from app.services.sql_validator import validate_and_correct_query
from app.services.agent_context import get_agent_context
from app.services.toon_optimizer import get_toon_optimizer

logger = logging.getLogger(__name__)

# Configuración TOON
TOON_ENABLED = True  # Activar/desactivar optimización TOON

@tool # type: ignore
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
    
    # Validar y corregir queries de metadatos
    validation = validate_and_correct_query(query)
    if not validation["valid"]:
        logger.warning(f"Query tiene problemas potenciales: {validation['issues']}")
        logger.info(f"Usando query corregida: {validation['corrected_query']}")
        query = validation["corrected_query"]

    # GUARDRAIL DE PRODUCCIÓN: Límite forzado de filas
    # Evita que el agente traiga 5000 filas y consuma todos los tokens
    MAX_ROWS = 50
    if "LIMIT" not in query.upper() and "COUNT" not in query.upper():
        logger.info(f"Injecting LIMIT {MAX_ROWS} to query for safety")
        # Simple injection (podría ser más sofisticada con sqlparse, pero esto funciona para el 99% de casos generados)
        if ";" in query:
            query = query.replace(";", f" LIMIT {MAX_ROWS};")
        else:
            query = query + f" LIMIT {MAX_ROWS}"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                logger.info(f"Executing Postgres query: {query}")
                cursor.execute(query)
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description] # type: ignore
                    rows = cursor.fetchall()
                    data = [dict(zip(columns, row)) for row in rows] # type: ignore
                    
                    # Mensaje de contexto para el LLM si se truncaron resultados
                    result_msg = f"Query succeeded! Returned {len(data)} rows."
                    if len(data) >= MAX_ROWS:
                        result_msg += f" (NOTE: Results were truncated to {MAX_ROWS} rows for efficiency. If you need more specific data, refine your WHERE clause.)"
                    
                    logger.info(result_msg)
                    
                    # TOON Optimization: Reducir tokens en el output
                    optimized_data = data
                    toon_stats = None
                    if TOON_ENABLED and len(data) > 0:
                        toon = get_toon_optimizer()
                        # Obtener la pregunta del contexto si está disponible
                        ctx = get_agent_context()
                        question = getattr(ctx, 'current_question', '')
                        
                        toon_result = toon.optimize_query_result(data, question)
                        optimized_data = toon_result["optimized_data"]
                        toon_stats = {
                            "original_rows": len(data),
                            "optimized_rows": len(optimized_data),
                            "fields_removed": toon_result.get("fields_removed", 0),
                            "summary": toon_result.get("summary")
                        }
                        
                        if toon_stats["fields_removed"] > 0:
                            logger.info(f"TOON: Removed {toon_stats['fields_removed']} redundant fields")
                    
                    result = {
                        "success": True,
                        "data": optimized_data,
                        "raw_row_count": len(data),  # Para el frontend
                        "message": result_msg,
                        "query": query,
                        "toon_optimization": toon_stats
                    }
                    
                    # Record in context for structured response
                    context = get_agent_context()
                    context.record_sql_execution(query, result)
                    
                    return result
                else:
                    result = {
                        "success": True,
                        "data": [],
                        "message": "Query executed successfully (no results)",
                        "query": query
                    }
                    
                    # Record in context
                    context = get_agent_context()
                    context.record_sql_execution(query, result)
                    
                    return result
                    
    except Exception as e:
        logger.error(f"Postgres query failed: {e}")
        result = {
            "success": False,
            "error": str(e),
            "query": query
        }
        
        # Record error in context
        context = get_agent_context()
        context.record_sql_execution(query, result)
        
        return result
