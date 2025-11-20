from typing import Optional
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agents.nl2sql_agent import create_nl2sql_agent

logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    """Request body for /ask endpoint"""
    question: str


class AskResponse(BaseModel):
    """Response body for /ask endpoint"""
    answer: str
    success: bool = True


app = FastAPI(
    title="NL2SQL Agent API",
    description="Natural Language to SQL Agent powered by Strands and Gemini",
    version="0.1.0"
)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "nl2sql-agent"}


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


def get_app() -> FastAPI:
    return app
