"""
Test script for the new /query endpoint with structured responses.
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title: str):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_query(question: str, description: str):
    """Test a query and print the structured response."""
    print(f"📝 {description}")
    print(f"   Pregunta: '{question}'")
    
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"question": question},
            timeout=30
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ Response en {elapsed:.2f}s")
            print(f"   Answer: {data.get('answer', 'N/A')[:100]}...")
            print(f"   Visualization: {data.get('visualization', 'N/A')}")
            print(f"   Row Count: {data.get('row_count', 0)}")
            print(f"   Truncated: {data.get('truncated', False)}")
            
            if data.get('sql_query'):
                print(f"   SQL: {data['sql_query'][:80]}...")
            
            if data.get('data'):
                print(f"\n   📊 Data Sample (first row):")
                print(f"   {json.dumps(data['data'][0], indent=6)}")
            
            if data.get('metadata'):
                print(f"\n   🔧 Metadata:")
                for key, value in data['metadata'].items():
                    print(f"      {key}: {value}")
            
        else:
            print(f"\n❌ Error {response.status_code}")
            print(f"   {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se pudo conectar al servidor.")
        print("   Asegúrate de que el servidor esté corriendo: uv run python main.py --serve")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
    
    print()

def main():
    print_section("TEST: ENDPOINT /query CON RESPUESTAS ESTRUCTURADAS")
    
    # Check health first
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print("✅ Servidor conectado\n")
        else:
            print("⚠️  Servidor responde pero con problemas\n")
    except:
        print("❌ Servidor no disponible. Ejecuta: uv run python main.py --serve\n")
        return
    
    # Test 1: KPI Query (single value)
    print_section("TEST 1: Consulta KPI (Valor Único)")
    test_query(
        "¿Cuántos clientes hay?",
        "Debería devolver visualization='kpi' con un solo número"
    )
    
    # Test 2: Table Query (multiple rows)
    print_section("TEST 2: Consulta de Tabla (Múltiples Filas)")
    test_query(
        "Muestra los últimos 5 clientes",
        "Debería devolver visualization='table' con lista de clientes"
    )
    
    # Test 3: Aggregation Query
    print_section("TEST 3: Consulta de Agregación")
    test_query(
        "¿Cuál es el promedio de edad de los clientes?",
        "Debería devolver un KPI si existe la columna edad"
    )
    
    # Test 4: Chart Query (if possible)
    print_section("TEST 4: Consulta para Gráfico")
    test_query(
        "Cuenta cuántos clientes hay por ciudad",
        "Debería sugerir bar_chart o pie_chart"
    )
    
    # Test 5: Error handling
    print_section("TEST 5: Manejo de Errores")
    test_query(
        "¿Cuántos dinosaurios hay en la tabla inexistente?",
        "Debería manejar el error gracefully"
    )
    
    print_section("TESTS COMPLETADOS")
    print("💡 Tip: Revisa los logs del servidor para ver el procesamiento interno\n")

if __name__ == "__main__":
    main()
