"""
Configuration management for the NL2SQL agent.
Using python-dotenv so your .env loads automatically.
"""
import os
from dotenv import load_dotenv  # type: ignore
from typing import Dict, Any

# Carga automáticamente el archivo .env en os.environ
load_dotenv()

def get_config() -> Dict[str, Any]:
    """
    Returns config loaded from environment variables.
    .env > OS environment > defaults
    """
    return {
        # PostgreSQL
        "postgres_host": os.getenv("POSTGRES_HOST", "localhost"),
        "postgres_port": os.getenv("POSTGRES_PORT", "5432"),
        "postgres_db": os.getenv("POSTGRES_DB", "postgres"),
        "postgres_user": os.getenv("POSTGRES_USER", "postgres"),
        "postgres_password": os.getenv("POSTGRES_PASSWORD", ""),

        # Gemini API Key
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        
        # API Server Configuration
        "environment": os.getenv("ENV", "development"),  # development or production
        "api_host": os.getenv("API_HOST", "0.0.0.0"),
        "api_port": int(os.getenv("API_PORT", "8000")),
        "api_workers": int(os.getenv("API_WORKERS", "1")),
    }
