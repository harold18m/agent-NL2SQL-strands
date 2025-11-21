"""
SQL Query Validator - Previene queries problemáticas y mejora la generación de SQL
"""
import re
from typing import Dict, List, Optional

class SQLQueryValidator:
    """Valida y sugiere mejoras para queries SQL generadas por el agente"""
    
    # Patrones problemáticos conocidos
    PROBLEMATIC_PATTERNS = {
        "missing_table_type": {
            "pattern": r"information_schema\.tables.*WHERE.*table_schema.*(?!.*table_type)",
            "issue": "Query cuenta todos los objetos, no solo tablas base",
            "suggestion": "Agregar: AND table_type = 'BASE TABLE'"
        },
        "missing_schema_filter": {
            "pattern": r"information_schema\.tables(?!.*WHERE.*table_schema)",
            "issue": "Query no filtra por schema, incluye schemas del sistema",
            "suggestion": "Agregar: WHERE table_schema = 'public'"
        }
    }
    
    @staticmethod
    def validate_metadata_query(query: str) -> Dict[str, any]:
        """
        Valida queries sobre metadatos (information_schema)
        
        Args:
            query: Query SQL a validar
            
        Returns:
            Dict con: valid (bool), issues (List[str]), corrected_query (str)
        """
        issues = []
        corrected_query = query
        
        # Verificar si es una query de metadatos
        if "information_schema.tables" in query.lower():
            
            # Verificar filtro de table_type
            if not re.search(r"table_type\s*=\s*['\"]BASE TABLE['\"]", query, re.IGNORECASE):
                if "table_schema" in query.lower():
                    issues.append("⚠️ Query cuenta todos los objetos (tablas + vistas). Falta: table_type = 'BASE TABLE'")
                    # Intentar corregir automáticamente
                    if re.search(r"WHERE\s+table_schema\s*=\s*['\"]public['\"]", query, re.IGNORECASE):
                        corrected_query = re.sub(
                            r"(WHERE\s+table_schema\s*=\s*['\"]public['\"])",
                            r"\1 AND table_type = 'BASE TABLE'",
                            query,
                            flags=re.IGNORECASE
                        )
            
            # Verificar filtro de schema
            if not re.search(r"table_schema\s*=\s*['\"]public['\"]", query, re.IGNORECASE):
                issues.append("⚠️ Query no filtra por schema público. Puede incluir schemas del sistema.")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "corrected_query": corrected_query if issues else query
        }
    
    @staticmethod
    def suggest_improvements(query: str) -> List[str]:
        """
        Sugiere mejoras para la query
        
        Args:
            query: Query SQL
            
        Returns:
            Lista de sugerencias
        """
        suggestions = []
        
        # Sugerencias para queries de conteo
        if re.search(r"SELECT\s+COUNT\(\*\)", query, re.IGNORECASE):
            if "information_schema.tables" in query.lower():
                if "table_type" not in query.lower():
                    suggestions.append("Considerar agregar filtro table_type = 'BASE TABLE' para contar solo tablas")
        
        # Sugerencias para queries sin ORDER BY
        if "SELECT" in query.upper() and "ORDER BY" not in query.upper() and "COUNT" not in query.upper():
            suggestions.append("Considerar agregar ORDER BY para resultados consistentes")
        
        return suggestions


def validate_and_correct_query(query: str) -> Dict[str, any]:
    """
    Función helper para validar y corregir queries
    
    Args:
        query: Query SQL a validar
        
    Returns:
        Dict con resultados de validación y query corregida si aplica
    """
    validator = SQLQueryValidator()
    result = validator.validate_metadata_query(query)
    
    if not result["valid"]:
        result["suggestions"] = validator.suggest_improvements(query)
    
    return result


# Casos de prueba para el validador
if __name__ == "__main__":
    print("=" * 80)
    print("TEST DEL VALIDADOR SQL")
    print("=" * 80)
    
    test_queries = [
        # Query incorrecta (la que genera el agente)
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';",
        
        # Query correcta
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';",
        
        # Query sin filtro de schema
        "SELECT COUNT(*) FROM information_schema.tables;",
        
        # Query normal de datos
        "SELECT * FROM clientes WHERE activo = true;"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: {query[:60]}...")
        print(f"{'='*80}")
        
        result = validate_and_correct_query(query)
        
        if result["valid"]:
            print("✅ Query válida")
        else:
            print("❌ Query con problemas:")
            for issue in result["issues"]:
                print(f"   {issue}")
            print(f"\n💡 Query corregida:")
            print(f"   {result['corrected_query']}")
