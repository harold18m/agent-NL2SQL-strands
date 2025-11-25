"""
Token Counter Service - Monitorea el consumo de tokens del agente.

Soporta estimación para modelos Gemini/GPT basado en tokenización aproximada.
"""
import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Registro de uso de tokens para una request."""
    timestamp: datetime = field(default_factory=datetime.now)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # Desglose detallado
    system_prompt_tokens: int = 0
    schema_tokens: int = 0
    user_query_tokens: int = 0
    tool_output_tokens: int = 0
    
    # Metadata
    question: str = ""
    model: str = "gemini-2.0-flash"
    
    @property
    def estimated_cost_usd(self) -> float:
        """Estima el costo en USD (precios Gemini 2.0 Flash aproximados)."""
        # Gemini 2.0 Flash: ~$0.075 per 1M input, ~$0.30 per 1M output
        input_cost = (self.input_tokens / 1_000_000) * 0.075
        output_cost = (self.output_tokens / 1_000_000) * 0.30
        return round(input_cost + output_cost, 6)


class TokenCounter:
    """
    Contador de tokens con estimación y tracking histórico.
    
    Nota: Gemini usa su propio tokenizador (SentencePiece), pero para estimaciones
    podemos usar ~4 caracteres = 1 token como aproximación razonable.
    """
    
    # Aproximación: caracteres por token (varía por idioma/contenido)
    CHARS_PER_TOKEN = 4
    
    def __init__(self):
        self.history: List[TokenUsage] = []
        self._session_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "estimated_cost_usd": 0.0
        }
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estima el número de tokens en un texto.
        
        Para una estimación más precisa con Gemini, podrías usar:
        - google.generativeai.count_tokens() (requiere API call)
        - tiktoken para GPT (diferente tokenizador)
        """
        if not text:
            return 0
        
        # Método simple: caracteres / 4
        char_estimate = len(text) // self.CHARS_PER_TOKEN
        
        # Ajuste por palabras (más preciso para inglés/español)
        words = len(text.split())
        word_estimate = int(words * 1.3)  # ~1.3 tokens por palabra
        
        # Promedio de ambos métodos
        return (char_estimate + word_estimate) // 2
    
    def count_schema_tokens(self, schema: str) -> int:
        """Cuenta tokens del schema (optimizado para formato compacto)."""
        return self.estimate_tokens(schema)
    
    def count_request(
        self,
        system_prompt: str,
        schema: str,
        user_query: str,
        tool_outputs: List[str],
        model_response: str,
        model: str = "gemini-2.0-flash"
    ) -> TokenUsage:
        """
        Cuenta y registra tokens para una request completa.
        
        Args:
            system_prompt: El prompt del sistema
            schema: El schema de la BD formateado
            user_query: La pregunta del usuario
            tool_outputs: Lista de outputs de herramientas (SQL results, etc.)
            model_response: La respuesta generada por el modelo
            model: Nombre del modelo usado
            
        Returns:
            TokenUsage con el desglose completo
        """
        # Contar tokens de entrada
        system_tokens = self.estimate_tokens(system_prompt)
        schema_tokens = self.estimate_tokens(schema)
        query_tokens = self.estimate_tokens(user_query)
        tool_tokens = sum(self.estimate_tokens(out) for out in tool_outputs)
        
        input_tokens = system_tokens + schema_tokens + query_tokens + tool_tokens
        output_tokens = self.estimate_tokens(model_response)
        total_tokens = input_tokens + output_tokens
        
        # Crear registro
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            system_prompt_tokens=system_tokens,
            schema_tokens=schema_tokens,
            user_query_tokens=query_tokens,
            tool_output_tokens=tool_tokens,
            question=user_query[:100],  # Truncar para storage
            model=model
        )
        
        # Actualizar histórico
        self.history.append(usage)
        self._session_totals["input_tokens"] += input_tokens
        self._session_totals["output_tokens"] += output_tokens
        self._session_totals["total_tokens"] += total_tokens
        self._session_totals["requests"] += 1
        self._session_totals["estimated_cost_usd"] += usage.estimated_cost_usd
        
        logger.info(
            f"Token usage - Input: {input_tokens}, Output: {output_tokens}, "
            f"Total: {total_tokens}, Cost: ${usage.estimated_cost_usd:.6f}"
        )
        
        return usage
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la sesión actual."""
        return {
            **self._session_totals,
            "avg_tokens_per_request": (
                self._session_totals["total_tokens"] // max(1, self._session_totals["requests"])
            ),
            "history_count": len(self.history)
        }
    
    def get_optimization_suggestions(self) -> List[str]:
        """
        Analiza el uso de tokens y sugiere optimizaciones.
        Implementa principios TOON.
        """
        suggestions = []
        stats = self.get_session_stats()
        
        if not self.history:
            return ["No hay suficientes datos para analizar."]
        
        # Analizar últimas requests
        recent = self.history[-10:] if len(self.history) >= 10 else self.history
        
        # 1. Schema muy grande
        avg_schema = sum(u.schema_tokens for u in recent) / len(recent)
        if avg_schema > 1000:
            suggestions.append(
                f"⚠️ Schema muy grande ({avg_schema:.0f} tokens). "
                "Considera: filtrar tablas relevantes, usar descripciones más cortas."
            )
        
        # 2. Tool outputs muy grandes
        avg_tool = sum(u.tool_output_tokens for u in recent) / len(recent)
        if avg_tool > 500:
            suggestions.append(
                f"⚠️ Outputs de herramientas grandes ({avg_tool:.0f} tokens). "
                "Considera: reducir LIMIT, seleccionar menos columnas."
            )
        
        # 3. Promedio general alto
        if stats["avg_tokens_per_request"] > 2000:
            suggestions.append(
                f"⚠️ Alto consumo promedio ({stats['avg_tokens_per_request']} tokens/request). "
                "Considera: implementar Schema RAG para seleccionar solo tablas relevantes."
            )
        
        # 4. Costo acumulado
        if stats["estimated_cost_usd"] > 0.10:
            suggestions.append(
                f"💰 Costo acumulado: ${stats['estimated_cost_usd']:.4f}. "
                "Considera: cachear respuestas frecuentes, usar modelos más económicos para queries simples."
            )
        
        if not suggestions:
            suggestions.append("✅ Uso de tokens dentro de rangos óptimos.")
        
        return suggestions
    
    def reset_session(self):
        """Reinicia contadores de sesión."""
        self.history = []
        self._session_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "estimated_cost_usd": 0.0
        }
    
    def export_history(self, filepath: str = "token_usage.json"):
        """Exporta historial a JSON."""
        export_data = {
            "session_stats": self.get_session_stats(),
            "optimization_suggestions": self.get_optimization_suggestions(),
            "history": [
                {
                    "timestamp": u.timestamp.isoformat(),
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "total_tokens": u.total_tokens,
                    "schema_tokens": u.schema_tokens,
                    "tool_output_tokens": u.tool_output_tokens,
                    "question": u.question,
                    "estimated_cost_usd": u.estimated_cost_usd
                }
                for u in self.history
            ]
        }
        
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Token history exported to {filepath}")
        return filepath


# Singleton global
_token_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Obtiene la instancia global del contador de tokens."""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter


def count_tokens(text: str) -> int:
    """Shortcut para estimar tokens de un texto."""
    return get_token_counter().estimate_tokens(text)
