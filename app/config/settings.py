"""
Configuration management for the NL2SQL agent.
Using python-dotenv so your .env loads automatically.
"""
import os
from urllib.parse import urlparse
from dotenv import load_dotenv  # type: ignore
from typing import Dict, Any

# Carga automáticamente el archivo .env en os.environ
load_dotenv()


def parse_database_url(url: str) -> Dict[str, Any]:
    """
    Parse a DATABASE_URL into individual connection parameters.
    Format: postgresql://user:password@host:port/database
    """
    parsed = urlparse(url)
    return {
        "postgres_host": parsed.hostname or "localhost",
        "postgres_port": str(parsed.port or 5432),
        "postgres_db": parsed.path.lstrip("/") if parsed.path else "postgres",
        "postgres_user": parsed.username or "postgres",
        "postgres_password": parsed.password or "",
    }


def get_config() -> Dict[str, Any]:
    """
    Returns config loaded from environment variables.
    DATABASE_URL is required for database connection.
    """
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    db_config = parse_database_url(database_url)
    
    return {
        # PostgreSQL (parsed from DATABASE_URL)
        **db_config,
        "database_url": database_url,

        # Gemini API Key
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        
        # API Server Configuration
        "environment": os.getenv("ENV", "development"),
        "api_host": os.getenv("API_HOST", "0.0.0.0"),
        "api_port": int(os.getenv("API_PORT", "8000")),
        "api_workers": int(os.getenv("API_WORKERS", "1")),
    }
