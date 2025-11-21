import logging
from typing import List, Dict, Any, Optional
import psycopg2
from app.config.settings import get_config
from app.config.database import get_db_connection

logger = logging.getLogger(__name__)

# Cache para el esquema (opcional: evita consultar la BD en cada request)
_schema_cache: Optional[List[Dict[str, Any]]] = None


def extract_schema_from_db() -> List[Dict[str, Any]]:
    """
    Extract database schema automatically from PostgreSQL using information_schema.
    Optimized to use connection pooling and fewer queries.
    """
    schema_data = []
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Get all tables in public schema
                cursor.execute("""
                    SELECT 
                        table_name,
                        obj_description((table_schema||'.'||table_name)::regclass, 'pg_class') as table_comment
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                tables = cursor.fetchall()
                
                if not tables:
                    return []

                # 2. Get all columns for all tables in one query
                cursor.execute("""
                    SELECT 
                        table_name,
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        col_description((table_schema||'.'||table_name)::regclass::oid, ordinal_position) as column_comment
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position;
                """)
                all_columns = cursor.fetchall()
                
                # Group columns by table
                columns_by_table = {}
                for row in all_columns:
                    t_name = row[0]
                    if t_name not in columns_by_table:
                        columns_by_table[t_name] = []
                    
                    col_name, data_type, is_nullable, col_default, max_length, col_comment = row[1:]
                    type_str = data_type
                    if max_length:
                        type_str = f"{data_type}({max_length})"
                        
                    columns_by_table[t_name].append({
                        "Name": col_name,
                        "Type": type_str,
                        "Nullable": is_nullable == "YES",
                        "Default": col_default,
                        "Comment": col_comment or f"Column {col_name}"
                    })

                # 3. Get all primary keys in one query
                cursor.execute("""
                    SELECT tc.table_name, kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = 'public'
                    ORDER BY tc.table_name, kcu.ordinal_position;
                """)
                all_pks = cursor.fetchall()
                
                pks_by_table = {}
                for t_name, col_name in all_pks:
                    if t_name not in pks_by_table:
                        pks_by_table[t_name] = []
                    pks_by_table[t_name].append({
                        "column_name": col_name,
                        "constraint": "primary key"
                    })

                # Assemble final schema structure
                for table_name, table_comment in tables:
                    schema_data.append({
                        "database_name": "postgres", # Generic name or from config
                        "table_name": table_name,
                        "table_description": table_comment or f"Table {table_name}",
                        "columns": columns_by_table.get(table_name, []),
                        "relationships": {
                            "primary_key": pks_by_table.get(table_name, []),
                            "foreign_key": [] # TODO: Implement FK extraction if needed
                        }
                    })
                    
    except Exception as e:
        logger.error(f"Error extracting schema: {e}")
        # Return empty list or cached version if available on error
        return []
        
    return schema_data


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


def format_schema_for_llm(schema: List[Dict[str, Any]]) -> str:
    """
    Format the schema into a compact string representation optimized for LLMs.
    Reduces token usage significantly compared to raw JSON.
    """
    lines = []
    for table in schema:
        table_name = table["table_name"]
        desc = table.get("table_description", "")
        if desc and desc != f"Table {table_name}":
            lines.append(f"Table: {table_name} ({desc})")
        else:
            lines.append(f"Table: {table_name}")
            
        # Columns
        cols = []
        for col in table["columns"]:
            c_name = col["Name"]
            c_type = col["Type"]
            extras = []
            if not col["Nullable"]:
                extras.append("NOT NULL")
            
            # Check for PK
            is_pk = False
            for pk in table["relationships"]["primary_key"]:
                if pk["column_name"] == c_name:
                    is_pk = True
                    break
            if is_pk:
                extras.append("PK")
                
            extra_str = f" [{', '.join(extras)}]" if extras else ""
            cols.append(f"  - {c_name} ({c_type}){extra_str}")
            
        lines.extend(cols)
        lines.append("") # Empty line between tables
        
    return "\n".join(lines)
