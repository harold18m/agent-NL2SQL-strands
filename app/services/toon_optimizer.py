"""
TOON - Tool Output Optimization for Natural Language

Técnicas para reducir el consumo de tokens en las salidas de herramientas
sin perder información relevante para el LLM.

Referencia: https://arxiv.org/abs/2312.10997 (TOON Paper)
"""
import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)


class TOONOptimizer:
    """
    Optimizador de outputs de herramientas para reducir tokens.
    
    Técnicas implementadas:
    1. Compresión de datos tabulares
    2. Resumen de resultados grandes
    3. Eliminación de campos redundantes
    4. Formato compacto vs verbose
    """
    
    # Campos que raramente necesita el LLM para generar respuestas
    REDUNDANT_FIELDS = {
        "created_at", "updated_at", "deleted_at",  # Timestamps (a menos que se pregunte)
        "password", "password_hash", "token",       # Campos sensibles
        "metadata", "extra_data", "raw_data",       # Campos blob
    }
    
    # Campos que siempre deben mantenerse
    ESSENTIAL_FIELDS = {
        "id", "name", "nombre", "title", "titulo",
        "total", "count", "sum", "avg", "amount",
        "status", "estado", "type", "tipo",
    }
    
    def __init__(self, max_rows: int = 20, max_chars_per_field: int = 100):
        self.max_rows = max_rows
        self.max_chars_per_field = max_chars_per_field
    
    def optimize_query_result(
        self,
        data: List[Dict[str, Any]],
        question: str = "",
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Optimiza el resultado de una query SQL para el LLM.
        
        Args:
            data: Lista de diccionarios (rows)
            question: La pregunta original (para determinar relevancia)
            include_summary: Si incluir un resumen estadístico
            
        Returns:
            Dict con datos optimizados y metadata
        """
        if not data:
            return {
                "optimized_data": [],
                "row_count": 0,
                "truncated": False,
                "summary": "No results found."
            }
        
        original_rows = len(data)
        original_fields = len(data[0]) if data else 0
        
        # 1. Truncar filas si excede el límite
        truncated = original_rows > self.max_rows
        working_data = data[:self.max_rows] if truncated else data
        
        # 2. Filtrar campos redundantes (si no se preguntan específicamente)
        question_lower = question.lower()
        fields_to_keep = self._determine_relevant_fields(
            data[0].keys() if data else [],
            question_lower
        )
        
        # 3. Optimizar cada fila
        optimized_data = []
        for row in working_data:
            optimized_row = {}
            for key, value in row.items():
                if key in fields_to_keep:
                    optimized_row[key] = self._compress_value(value)
            optimized_data.append(optimized_row)
        
        # 4. Generar resumen si hay muchos datos
        summary = None
        if include_summary and original_rows > 5:
            summary = self._generate_summary(data, original_rows, truncated)
        
        result = {
            "optimized_data": optimized_data,
            "row_count": original_rows,
            "displayed_rows": len(optimized_data),
            "truncated": truncated,
            "fields_kept": len(fields_to_keep),
            "fields_removed": original_fields - len(fields_to_keep),
        }
        
        if summary:
            result["summary"] = summary
            
        return result
    
    def _determine_relevant_fields(
        self,
        all_fields: List[str],
        question: str
    ) -> set:
        """Determina qué campos son relevantes para la pregunta."""
        relevant = set(self.ESSENTIAL_FIELDS)
        
        # Siempre incluir campos mencionados en la pregunta
        for field in all_fields:
            field_lower = field.lower()
            # Si el campo está en la pregunta, mantenerlo
            if field_lower in question or field_lower.replace("_", " ") in question:
                relevant.add(field)
            # Si no es redundante y no tenemos muchos campos, mantenerlo
            elif field not in self.REDUNDANT_FIELDS:
                relevant.add(field)
        
        # Si pregunta por fechas, incluir campos de fecha
        date_keywords = ["fecha", "date", "cuando", "when", "último", "last", "primero", "first"]
        if any(kw in question for kw in date_keywords):
            for field in all_fields:
                if any(d in field.lower() for d in ["date", "fecha", "created", "updated", "time"]):
                    relevant.add(field)
        
        return relevant
    
    def _compress_value(self, value: Any) -> Any:
        """Comprime un valor si es muy largo."""
        if value is None:
            return None
        
        if isinstance(value, str):
            if len(value) > self.max_chars_per_field:
                return value[:self.max_chars_per_field] + "..."
            return value
        
        if isinstance(value, (dict, list)):
            json_str = json.dumps(value)
            if len(json_str) > self.max_chars_per_field:
                return f"[Complex object, {len(json_str)} chars]"
            return value
        
        return value
    
    def _generate_summary(
        self,
        data: List[Dict[str, Any]],
        total_rows: int,
        truncated: bool
    ) -> str:
        """Genera un resumen estadístico de los datos."""
        parts = [f"Total: {total_rows} rows"]
        
        if truncated:
            parts.append(f"(showing first {self.max_rows})")
        
        # Buscar campos numéricos para estadísticas básicas
        if data:
            numeric_fields = []
            for key, value in data[0].items():
                if isinstance(value, (int, float)) and key not in ["id"]:
                    numeric_fields.append(key)
            
            for field in numeric_fields[:2]:  # Max 2 campos
                values = [r.get(field) for r in data if r.get(field) is not None]
                if values:
                    avg_val = sum(values) / len(values)
                    parts.append(f"Avg {field}: {avg_val:.2f}")
        
        return " | ".join(parts)
    
    def optimize_schema(
        self,
        schema: str,
        question: str = "",
        max_tables: int = 10
    ) -> str:
        """
        Optimiza el schema para reducir tokens.
        
        Técnicas:
        1. Si hay muchas tablas, filtrar por relevancia a la pregunta
        2. Eliminar columnas de auditoría si no se preguntan
        3. Formato ultra-compacto
        """
        # Para un schema ya formateado, podemos aplicar filtros básicos
        lines = schema.split("\n")
        optimized_lines = []
        
        # Keywords de la pregunta para filtrar
        question_lower = question.lower()
        keywords = set(question_lower.split())
        
        # Siempre incluir palabras clave comunes
        keywords.update(["cliente", "client", "orden", "order", "producto", "product", 
                        "venta", "sale", "factura", "invoice", "pago", "payment"])
        
        current_table = None
        include_table = True
        tables_included = 0
        
        for line in lines:
            if line.startswith("Table:"):
                # Nueva tabla
                table_name = line.replace("Table:", "").strip().split()[0].lower()
                
                # Determinar si incluir esta tabla
                include_table = (
                    tables_included < max_tables and
                    (not question or any(kw in table_name for kw in keywords) or tables_included < 5)
                )
                
                if include_table:
                    tables_included += 1
                    current_table = table_name
                    optimized_lines.append(line)
            elif include_table:
                # Filtrar columnas de auditoría si no se preguntan
                skip_column = False
                if line.strip().startswith("-"):
                    col_name = line.strip().lstrip("- ").split()[0].lower()
                    audit_cols = ["created_at", "updated_at", "deleted_at", "created_by", "updated_by"]
                    if col_name in audit_cols and not any(a in question_lower for a in ["fecha", "date", "cuando", "created", "updated"]):
                        skip_column = True
                
                if not skip_column:
                    optimized_lines.append(line)
        
        return "\n".join(optimized_lines)
    
    def format_for_llm(
        self,
        data: List[Dict[str, Any]],
        format_type: str = "compact"
    ) -> str:
        """
        Formatea datos para consumo del LLM.
        
        format_type:
            - "compact": Mínimo de tokens, solo datos esenciales
            - "readable": Formato tabla legible
            - "json": JSON compacto
        """
        if not data:
            return "No data"
        
        if format_type == "compact":
            # Formato ultra-compacto: key=value separado por |
            lines = []
            for i, row in enumerate(data[:self.max_rows], 1):
                parts = [f"{k}={v}" for k, v in row.items() if v is not None]
                lines.append(f"{i}. " + " | ".join(parts))
            return "\n".join(lines)
        
        elif format_type == "readable":
            # Formato tabla markdown
            if not data:
                return "| No data |"
            headers = list(data[0].keys())
            lines = ["| " + " | ".join(headers) + " |"]
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in data[:self.max_rows]:
                values = [str(row.get(h, ""))[:50] for h in headers]
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)
        
        else:  # json
            return json.dumps(data[:self.max_rows], ensure_ascii=False, separators=(",", ":"))


# Singleton global
_toon_optimizer: Optional[TOONOptimizer] = None


def get_toon_optimizer() -> TOONOptimizer:
    """Obtiene la instancia global del optimizador TOON."""
    global _toon_optimizer
    if _toon_optimizer is None:
        _toon_optimizer = TOONOptimizer()
    return _toon_optimizer


def optimize_tool_output(
    data: List[Dict[str, Any]],
    question: str = ""
) -> Dict[str, Any]:
    """Shortcut para optimizar output de herramientas."""
    return get_toon_optimizer().optimize_query_result(data, question)
