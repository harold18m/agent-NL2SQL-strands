"""
Entry point for the NL2SQL agent.
"""
import argparse
import logging
import sys
import os

# Add the project root to the python path so imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agents.nl2sql_agent import create_nl2sql_agent
from app.config.logger import setup_logging
from app.config.settings import get_config

def main():
    """
    Main entry point for the NL2SQL agent.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="NL2SQL Agent using Strands SDK")
    parser.add_argument("--question", "-q", type=str, help="Natural language question to convert to SQL")
    parser.add_argument("--serve", action="store_true", help="Run HTTP API server for the agent")
    parser.add_argument("--host", type=str, help="Host to bind the server (default: from ENV or 0.0.0.0)")
    parser.add_argument("--port", type=int, help="Port to bind the server (default: from ENV or 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, help="Number of worker processes (default: from ENV or 1)")
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting NL2SQL agent")

    # If serve flag is passed, run FastAPI app via uvicorn
    if args.serve:
        try:
            import uvicorn
        except Exception:
            logger.error("uvicorn is not installed. Install it with `pip install uvicorn[standard]`.")
            return

        config = get_config()
        host = args.host or config.get("api_host", "0.0.0.0")
        port = args.port or config.get("api_port", 8000)
        workers = args.workers or config.get("api_workers", 1)
        is_dev = config.get("environment", "development") == "development"
        
        # Enable reload only in development or if explicitly requested
        reload = args.reload or (is_dev and not args.workers)
        
        logger.info(f"Starting API server on http://{host}:{port}")
        logger.info(f"Environment: {config.get('environment', 'development')}")
        logger.info(f"Workers: {workers if not reload else 1} (reload: {reload})")
        
        uvicorn.run(
            "app.api.routes:app",
            host=host,
            port=port,
            reload=reload,
            workers=1 if reload else workers,  # Workers don't work with reload
            log_level="info"
        )
        return

    # Create the agent for a single-run CLI invocation
    agent = create_nl2sql_agent()

    # If a question was provided, process it
    if args.question:
        logger.info(f"Processing question: {args.question}")
        response = agent(args.question)
        print(f"\nResponse:\n{response}")

    logger.info("NL2SQL agent finished")

if __name__ == "__main__":
    main()
