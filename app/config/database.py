"""
Database connection management using connection pooling.
"""
import logging
from contextlib import contextmanager
from typing import Generator, Any
import psycopg2
from psycopg2 import pool
from app.config.settings import get_config

logger = logging.getLogger(__name__)

class DatabasePool:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize the connection pool if it doesn't exist"""
        if self._pool is None:
            try:
                config = get_config()
                self._pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=20,
                    host=config["postgres_host"],
                    port=config["postgres_port"],
                    database=config["postgres_db"],
                    user=config["postgres_user"],
                    password=config["postgres_password"]
                )
                logger.info("Database connection pool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise

    def get_connection(self):
        """Get a connection from the pool"""
        if self._pool is None:
            self.initialize()
        return self._pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self._pool is not None:
            self._pool.putconn(conn)

    def close_all(self):
        """Close all connections in the pool"""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("Database connection pool closed")

# Global instance
db_pool = DatabasePool()

@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    """
    Context manager for getting a database connection from the pool.
    Usage:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(...)
    """
    conn = None
    try:
        conn = db_pool.get_connection()
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            db_pool.return_connection(conn)
