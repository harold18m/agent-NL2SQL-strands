from typing import Optional, List, Dict, Any
import logging
import json
import re
import time

from fastapi import FastAPI, HTTPException

from app.agents.nl2sql_agent import create_nl2sql_agent
from app.api.models import AskRequest, AskResponse, AgentResponse, VisualizationType
from app.services.response_formatter import analyze_result_for_visualization
from app.services.agent_context import get_agent_context, reset_agent_context
from app.services.token_counter import get_token_counter
from app.services.toon_optimizer import get_toon_optimizer

logger = logging.getLogger(__name__)


app = FastAPI(
    title="NL2SQL Agent API",
    description="Natural Language to SQL Agent powered by Strands and Gemini",
    version="0.2.0"
)

@app.get("/")
def root():
    """Root endpoint - API info"""
    return {
        "service": "nl2sql-agent",
        "version": "0.2.0",
        "description": "NL2SQL Agent API - Ask natural language questions about your database."
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "nl2sql-agent"}


@app.get("/stats/tokens")
def get_token_stats():
    """
    Get token usage statistics for the current session.
    
    Returns:
        - Total tokens used (input/output)
        - Average tokens per request
        - Estimated cost in USD
        - Optimization suggestions
    """
    counter = get_token_counter()
    stats = counter.get_session_stats()
    suggestions = counter.get_optimization_suggestions()
    
    return {
        "session_stats": stats,
        "optimization_suggestions": suggestions,
        "toon_status": "enabled"
    }


@app.post("/stats/tokens/reset")
def reset_token_stats():
    """Reset token statistics for a new session."""
    counter = get_token_counter()
    counter.reset_session()
    return {"message": "Token statistics reset successfully"}


@app.get("/stats/tokens/export")
def export_token_stats():
    """Export token usage history to JSON file."""
    counter = get_token_counter()
    filepath = counter.export_history()
    return {"message": f"Token history exported to {filepath}"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """Ask a natural language question about your database.
    
    The agent will:
    1. Retrieve the database schema
    2. Generate appropriate SQL query
    3. Execute the query
    4. Return the results
    
    Example request:
    ```json
    {
        "question": "How many clients do we have?"
    }
    ```
    """
    try:
        logger.info(f"Received question: {request.question}")
        
        # Create and invoke the agent
        agent = create_nl2sql_agent()
        response = agent(request.question)
        
        logger.info(f"Agent response generated successfully")
        return AskResponse(answer=str(response), success=True)
        
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing your question: {str(e)}"
        )


@app.post("/query", response_model=AgentResponse)
def query(request: AskRequest):
    """Ask a question and get structured JSON response for React frontend.
    
    Returns structured data including:
    - Natural language answer
    - SQL query (for debugging)
    - Raw data (for tables/charts)
    - Visualization suggestion
    
    Example request:
    ```json
    {
        "question": "How many clients do we have?",
        "include_sql": true,
        "format_response": true
    }
    ```
    
    Example response:
    ```json
    {
        "answer": "There are 150 clients in the database.",
        "sql_query": "SELECT COUNT(*) FROM clientes;",
        "data": [{"count": 150}],
        "visualization": "kpi",
        "row_count": 1,
        "truncated": false,
        "success": true
    }
    ```
    """
    start_time = time.time()
    
    # Reset context for this new query
    reset_agent_context()
    
    try:
        logger.info(f"Received query: {request.question}")
        
        # Create and invoke the agent
        agent = create_nl2sql_agent()
        response_text = agent(request.question)
        
        # Get the captured context from tool executions
        context = get_agent_context()
        
        # Build structured response from context
        structured_response = _build_response_from_context(
            response_text=str(response_text),
            context=context,
            question=request.question,
            include_sql=request.include_sql,
            format_response=request.format_response
        )
        
        # Add execution time to metadata
        execution_time = time.time() - start_time
        structured_response.metadata["execution_time_seconds"] = round(execution_time, 2)
        
        logger.info(
            f"Query processed successfully in {execution_time:.2f}s. "
            f"Visualization: {structured_response.visualization}, "
            f"Rows: {structured_response.row_count}"
        )
        
        return structured_response
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return AgentResponse(
            answer=f"Sorry, I encountered an error: {str(e)}",
            success=False,
            error=str(e),
            visualization=VisualizationType.TEXT,
            metadata={"execution_time_seconds": round(time.time() - start_time, 2)}
        )




def _build_response_from_context(
    response_text: str,
    context: Any,
    question: str,
    include_sql: bool = True,
    format_response: bool = True
) -> AgentResponse:
    """
    Build structured response using captured context from tool executions.
    This is more reliable than parsing text output.
    """
    sql_query = context.last_sql_query if include_sql else None
    data = context.last_query_data
    row_count = len(data)
    truncated = context.truncated
    success = context.last_query_success
    error = context.last_query_error
    
    # Determine visualization type
    visualization = VisualizationType.TEXT
    viz_metadata = {}
    
    if format_response and data and success:
        visualization, viz_metadata = analyze_result_for_visualization(
            data=data,
            sql_query=sql_query or "",
            question=question
        )
    elif data and success:
        visualization = VisualizationType.TABLE
    
    return AgentResponse(
        answer=response_text.strip(),
        sql_query=sql_query,
        data=data,
        visualization=visualization,
        row_count=row_count,
        truncated=truncated,
        success=success,
        error=error,
        metadata=viz_metadata
    )


def _parse_agent_response(
    response_text: str,
    question: str,
    include_sql: bool = True,
    format_response: bool = True
) -> AgentResponse:
    """
    Parse the agent's text response and extract structured data.
    
    The agent's response may contain embedded tool results from run_postgres_query.
    We need to extract:
    - The natural language answer
    - The SQL query that was executed
    - The raw data from the query results
    """
    # Try to extract data from tool call results embedded in the response
    # The Strands SDK may include tool results in the response
    
    sql_query = None
    data = []
    truncated = False
    row_count = 0
    
    # Look for SQL query patterns in the response
    sql_pattern = r'SELECT\s+.*?(?:;|$)'
    sql_matches = re.findall(sql_pattern, response_text, re.IGNORECASE | re.DOTALL)
    if sql_matches:
        sql_query = sql_matches[0].strip()
    
    # Try to find embedded JSON data (from tool results)
    # The tool returns {"success": true, "data": [...], ...}
    try:
        # Look for JSON-like structures
        json_pattern = r'\{[^{}]*"data"[^{}]*\[[^\]]*\][^{}]*\}'
        json_matches = re.findall(json_pattern, response_text)
        
        for match in json_matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict) and "data" in parsed:
                    data = parsed["data"]
                    row_count = len(data)
                    # Check if results were truncated
                    if "message" in parsed and "truncated" in parsed["message"].lower():
                        truncated = True
                    break
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.warning(f"Could not extract data from response: {e}")
    
    # Determine visualization type
    visualization = VisualizationType.TEXT
    viz_metadata = {}
    
    if format_response and data:
        visualization, viz_metadata = analyze_result_for_visualization(
            data=data,
            sql_query=sql_query or "",
            question=question
        )
    elif data:
        visualization = VisualizationType.TABLE
    
    # Clean up the answer text (remove tool call artifacts)
    answer = response_text
    # Remove JSON artifacts from the answer
    answer = re.sub(r'\{[^{}]*"success"[^{}]*\}', '', answer)
    answer = answer.strip()
    
    return AgentResponse(
        answer=answer,
        sql_query=sql_query if include_sql else None,
        data=data,
        visualization=visualization,
        row_count=row_count,
        truncated=truncated,
        success=True,
        metadata=viz_metadata
    )


def get_app() -> FastAPI:
    return app
