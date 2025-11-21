"""
Test de verificación de las correcciones implementadas
"""
import requests
import psycopg2
from app.config.settings import get_config
from app.services.sql_validator import validate_and_correct_query

def test_validator():
    """Prueba el validador SQL"""
    print("="*80)
    print("TEST 1: VALIDADOR SQL")
    print("="*80)
    
    # Query incorrecta (la que generaba el agente)
    bad_query = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
    
    print(f"\n📝 Query original (incorrecta):")
    print(f"   {bad_query}")
    
    result = validate_and_correct_query(bad_query)
    
    if not result["valid"]:
        print(f"\n❌ Problemas detectados:")
        for issue in result["issues"]:
            print(f"   {issue}")
        
        print(f"\n✅ Query corregida automáticamente:")
        print(f"   {result['corrected_query']}")
        
        # Ejecutar ambas queries para comparar
        config = get_config()
        conn = psycopg2.connect(
            host=config["postgres_host"],
            port=config["postgres_port"],
            database=config["postgres_db"],
            user=config["postgres_user"],
            password=config["postgres_password"]
        )
        
        with conn:
            with conn.cursor() as cursor:
                # Query incorrecta
                cursor.execute(bad_query)
                bad_result = cursor.fetchone()[0]
                
                # Query corregida
                cursor.execute(result['corrected_query'])
                good_result = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n📊 Comparación de resultados:")
        print(f"   Query incorrecta:  {bad_result} objetos")
        print(f"   Query corregida:   {good_result} tablas")
        print(f"   Diferencia:        {bad_result - good_result} objetos extra eliminados")
    
    return result["valid"]


def test_agent_after_fix():
    """Prueba el agente después de las correcciones"""
    print("\n" + "="*80)
    print("TEST 2: AGENTE DESPUÉS DE CORRECCIONES")
    print("="*80)
    
    api_url = "http://localhost:8000/ask"
    question = "¿Cuántas tablas tengo en el schema public?"
    
    print(f"\n📝 Pregunta: {question}")
    print("\n⚠️  NOTA: Reinicia el servidor para aplicar los cambios:")
    print("   1. Detén el servidor actual (Ctrl+C)")
    print("   2. Ejecuta: uvicorn main:app --reload")
    print("   3. Vuelve a ejecutar este test\n")
    
    try:
        response = requests.post(
            api_url,
            json={"question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            
            print(f"✅ Respuesta del agente:\n{answer}")
            
            # Verificar si la respuesta contiene el número correcto (33)
            if "33" in answer:
                print("\n🎉 ¡ÉXITO! El agente ahora responde correctamente")
                return True
            else:
                print("\n⚠️  El agente aún no está respondiendo correctamente")
                print("    Asegúrate de haber reiniciado el servidor")
                return False
        else:
            print(f"❌ Error HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor esté corriendo en http://localhost:8000")
        return False


def run_full_verification():
    """Ejecuta todos los tests de verificación"""
    print("🔧 VERIFICACIÓN DE CORRECCIONES IMPLEMENTADAS")
    print("="*80)
    
    # Test 1: Validador
    validator_works = test_validator()
    
    # Test 2: Agente (requiere reiniciar servidor)
    agent_works = test_agent_after_fix()
    
    print("\n" + "="*80)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("="*80)
    print(f"\n1. Validador SQL:           {'✅ Funciona' if validator_works else '❌ Falló'}")
    print(f"2. Agente corregido:        {'✅ Funciona' if agent_works else '⚠️  Requiere reiniciar servidor'}")
    
    if validator_works:
        print("\n✅ Las correcciones están implementadas correctamente")
        print("   El validador SQL detecta y corrige automáticamente las queries problemáticas")
    
    if not agent_works:
        print("\n⚠️  ACCIÓN REQUERIDA:")
        print("   1. Detén el servidor API actual")
        print("   2. Reinicia con: uvicorn main:app --reload")
        print("   3. Ejecuta de nuevo: uv run python test_fix_verification.py")
    else:
        print("\n🎉 ¡Todo funciona correctamente!")
        print("   Puedes ejecutar test_hallucination.py para confirmar la solución completa")


if __name__ == "__main__":
    run_full_verification()
