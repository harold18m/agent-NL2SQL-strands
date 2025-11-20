import logging
from typing import List, Dict, Any, Optional
import psycopg2
from app.config.settings import get_config

logger = logging.getLogger(__name__)

# Cache para el esquema (opcional: evita consultar la BD en cada request)
_schema_cache: Optional[List[Dict[str, Any]]] = None


def extract_schema_from_db() -> List[Dict[str, Any]]:
    """
    Extract database schema automatically from PostgreSQL using information_schema.
    
    Queries the database to get:
    - All tables in the public schema
    - Columns with their types and nullability
    - Primary keys
    - Foreign keys
    - Column comments (if available)
    
    Returns:
        List of table definitions with complete metadata
    """
    config = get_config()
    schema_data = []
    
    try:
        conn = psycopg2.connect(
            host=config["postgres_host"],
            port=config["postgres_port"],
            database=config["postgres_db"],
            user=config["postgres_user"],
            password=config["postgres_password"]
        )
        
        with conn.cursor() as cursor:
            # Get all tables in public schema
            cursor.execute("""
                SELECT 
                    table_schema,
                    table_name,
                    obj_description((table_schema||'.'||table_name)::regclass, 'pg_class') as table_comment
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            
            for table_schema, table_name, table_comment in tables:
                logger.info(f"Extracting schema for table: {table_name}")
                
                # Get columns for this table
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        col_description((table_schema||'.'||table_name)::regclass::oid, ordinal_position) as column_comment
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position;
                """, (table_schema, table_name))
                
                columns_data = cursor.fetchall()
                columns = []
                
                for col_name, data_type, is_nullable, col_default, max_length, col_comment in columns_data:
                    type_str = data_type
                    if max_length:
                        type_str = f"{data_type}({max_length})"
                    
                    columns.append({
                        "Name": col_name,
                        "Type": type_str,
                        "Nullable": is_nullable == "YES",
                        "Default": col_default,
                        "Comment": col_comment or f"Column {col_name}"
                    })
                
                # Get primary keys
                cursor.execute("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s
                    ORDER BY kcu.ordinal_position;
                """, (table_schema, table_name))
                
                primary_keys = [{"column_name": row[0], "constraint": "primary key"} for row in cursor.fetchall()]
                
                # Get foreign keys
                cursor.execute("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s;
                """, (table_schema, table_name))
                
                foreign_keys = [
                    {
                        "column_name": row[0],
                        "references_table": row[1],
                        "references_column": row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Build table definition
                table_def = {
                    "database_name": config["postgres_db"],
                    "table_name": table_name,
                    "table_description": table_comment or f"Table {table_name}",
                    "columns": columns,
                    "relationships": {
                        "primary_key": primary_keys,
                        "foreign_key": foreign_keys
                    }
                }
                
                schema_data.append(table_def)
        
        conn.close()
        logger.info(f"Successfully extracted schema for {len(schema_data)} tables")
        return schema_data
        
    except psycopg2.Error as e:
        logger.error(f"Failed to extract schema from database: {e}")
        # Return empty schema on error
        return []


def load_schema(use_cache: bool = True, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Load the database schema (with optional caching).
    
    Args:
        use_cache: Whether to use cached schema (default: True)
        force_refresh: Force refresh from database even if cached (default: False)
    
    Returns:
        List of table definitions
    """
    global _schema_cache
    
    if force_refresh or not use_cache or _schema_cache is None:
        logger.info("Loading schema from database...")
        _schema_cache = extract_schema_from_db()
    else:
        logger.info("Using cached schema")
    
    return _schema_cache
