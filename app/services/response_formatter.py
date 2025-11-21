"""
Service for analyzing query results and determining appropriate visualizations.
"""
import logging
from typing import List, Dict, Any, Tuple
from app.api.models import VisualizationType

logger = logging.getLogger(__name__)


def analyze_result_for_visualization(
    data: List[Dict[str, Any]], 
    sql_query: str,
    question: str
) -> Tuple[VisualizationType, Dict[str, Any]]:
    """
    Analyze query results and determine the best visualization type.
    
    Args:
        data: Query results as list of dictionaries
        sql_query: The SQL query that was executed
        question: The original user question
        
    Returns:
        Tuple of (visualization_type, metadata)
    """
    metadata = {}
    
    # No data or empty result
    if not data or len(data) == 0:
        return VisualizationType.TEXT, {"reason": "no_data"}
    
    # Single row, single column -> KPI
    if len(data) == 1 and len(data[0]) == 1:
        return VisualizationType.KPI, {"value": list(data[0].values())[0]}
    
    # Single row with multiple columns but all numeric except one -> KPI with context
    if len(data) == 1:
        numeric_cols = [k for k, v in data[0].items() if isinstance(v, (int, float))]
        if len(numeric_cols) >= 1:
            return VisualizationType.KPI, {
                "primary_value": data[0][numeric_cols[0]],
                "context": {k: v for k, v in data[0].items() if k not in numeric_cols}
            }
    
    # Multiple rows, two columns (category + value) -> BAR_CHART or PIE_CHART
    if len(data) > 1 and len(data[0]) == 2:
        cols = list(data[0].keys())
        first_col_vals = [row[cols[0]] for row in data]
        second_col_vals = [row[cols[1]] for row in data]
        
        # Check if second column is numeric
        if all(isinstance(v, (int, float)) for v in second_col_vals):
            # If categories are few (< 10), suggest pie chart
            if len(data) <= 8:
                metadata["category_column"] = cols[0]
                metadata["value_column"] = cols[1]
                return VisualizationType.PIE_CHART, metadata
            else:
                metadata["category_column"] = cols[0]
                metadata["value_column"] = cols[1]
                return VisualizationType.BAR_CHART, metadata
    
    # Time series detection: Has a date column + numeric column
    date_keywords = ['date', 'time', 'created', 'updated', 'timestamp', 'fecha']
    date_cols = [k for k in data[0].keys() if any(kw in k.lower() for kw in date_keywords)]
    
    if date_cols:
        numeric_cols = [k for k, v in data[0].items() if isinstance(v, (int, float)) and k not in date_cols]
        if numeric_cols:
            metadata["date_column"] = date_cols[0]
            metadata["value_column"] = numeric_cols[0]
            return VisualizationType.LINE_CHART, metadata
    
    # COUNT queries -> KPI
    if "COUNT" in sql_query.upper() and len(data) == 1:
        return VisualizationType.KPI, {"value": list(data[0].values())[0]}
    
    # SUM, AVG, MAX, MIN aggregations -> KPI
    aggregation_keywords = ["SUM", "AVG", "MAX", "MIN", "TOTAL"]
    if any(kw in sql_query.upper() for kw in aggregation_keywords) and len(data) == 1:
        return VisualizationType.KPI, {"value": list(data[0].values())[0]}
    
    # Default: Show as table
    metadata["reason"] = "default_table"
    metadata["column_count"] = len(data[0]) if data else 0
    metadata["row_count"] = len(data)
    
    return VisualizationType.TABLE, metadata


def extract_sql_from_agent_logs(agent_response: str) -> str:
    """
    Try to extract SQL query from agent response/logs.
    This is a fallback for when we can't intercept the tool call directly.
    
    Args:
        agent_response: The full text response from the agent
        
    Returns:
        Extracted SQL query or empty string
    """
    # Look for SQL patterns in the response
    lines = agent_response.split('\n')
    sql_lines = []
    in_sql_block = False
    
    for line in lines:
        upper_line = line.upper().strip()
        
        # Detect SQL start
        if upper_line.startswith('SELECT'):
            in_sql_block = True
            sql_lines.append(line.strip())
        elif in_sql_block:
            # Continue until we hit a terminator or non-SQL line
            if ';' in line or not line.strip():
                if ';' in line:
                    sql_lines.append(line.strip())
                break
            sql_lines.append(line.strip())
    
    return ' '.join(sql_lines) if sql_lines else ""
