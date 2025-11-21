"""
Test de Alucinación: Comparar resultados SQL directo vs Agente API
Objetivo: Verificar que el agente no alucine sobre el número de tablas en el schema public
"""
import psycopg2
import requests
from app.config.settings import get_config
from typing import Dict, Any
import json

def get_tables_direct_sql() -> Dict[str, Any]:
    """
    Método 1: Consulta SQL directa para contar tablas en schema public
    """
    config = get_config()
    
    query = """
    SELECT COUNT(*) as total_tables 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """
    
    try:
        conn = psycopg2.connect(
            host=config["postgres_host"],
            port=config["postgres_port"],
            database=config["postgres_db"],
            user=config["postgres_user"],
            password=config["postgres_password"]
        )
        
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                total_tables = result[0] if result else 0
                
                # También obtener los nombres de las tablas
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
        conn.close()
        
        return {
            "success": True,
            "method": "SQL Directo",
            "total_tables": total_tables,
            "table_names": tables
        }
                    
    except psycopg2.Error as e:
        return {
            "success": False,
            "method": "SQL Directo",
            "error": str(e)
        }


def get_tables_via_agent(api_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Método 2: Preguntar al agente a través del API
    """
    endpoint = f"{api_url}/ask"
    question = "¿Cuántas tablas tengo en el schema public?"
    
    try:
        response = requests.post(
            endpoint,
            json={"question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "method": "Agente API",
                "raw_response": data.get("answer", ""),
                "question": question
            }
        else:
            return {
                "success": False,
                "method": "Agente API",
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "method": "Agente API",
            "error": str(e)
        }


def run_hallucination_test():
    """
    Ejecuta el test completo y compara resultados
    """
    print("="*80)
    print("TEST DE ALUCINACIÓN - NL2SQL Agent")
    print("="*80)
    print("\n📊 Pregunta: ¿Cuántas tablas tenemos en el schema public?\n")
    
    # Test 1: SQL Directo
    print("🔍 Test 1: Ejecutando consulta SQL directa...")
    direct_result = get_tables_direct_sql()
    
    if direct_result["success"]:
        print(f"✅ Resultado SQL Directo: {direct_result['total_tables']} tablas")
        print(f"📋 Tablas encontradas: {', '.join(direct_result['table_names'])}")
    else:
        print(f"❌ Error en SQL directo: {direct_result['error']}")
        return
    
    print("\n" + "-"*80 + "\n")
    
    # Test 2: Agente API
    print("🤖 Test 2: Consultando al agente a través del API...")
    print("⚠️  Asegúrate de que el servidor esté corriendo en http://localhost:8000\n")
    
    agent_result = get_tables_via_agent()
    
    if agent_result["success"]:
        print(f"✅ Respuesta del Agente:\n{agent_result['raw_response']}")
    else:
        print(f"❌ Error en consulta al agente: {agent_result['error']}")
        print("\n💡 Tip: Inicia el servidor con: uvicorn main:app --reload")
        return
    
    print("\n" + "="*80)
    print("📊 COMPARACIÓN DE RESULTADOS")
    print("="*80)
    
    print(f"\n1️⃣  SQL Directo: {direct_result['total_tables']} tablas")
    print(f"2️⃣  Agente API: {agent_result['raw_response']}")
    
    print("\n" + "="*80)
    print("🔍 ANÁLISIS")
    print("="*80)
    print("\n➡️  Verifica manualmente si la respuesta del agente coincide con el conteo real.")
    print("➡️  El agente NO debería inventar tablas que no existen.")
    print("➡️  El agente DEBERÍA reportar el mismo número que la consulta directa.")
    
    # Guardar resultados en archivo
    results = {
        "direct_sql": direct_result,
        "agent_api": agent_result
    }
    
    with open("test_hallucination_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n💾 Resultados guardados en: test_hallucination_results.json")
    print("="*80)


if __name__ == "__main__":
    run_hallucination_test()
