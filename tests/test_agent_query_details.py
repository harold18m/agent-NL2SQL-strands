"""
Test adicional: Ver la query SQL que genera el agente
"""
import requests
import json

def test_agent_with_detailed_logging():
    """
    Hace la misma pregunta al agente y revisa la respuesta completa
    """
    api_url = "http://localhost:8000/ask"
    question = "¿Cuántas tablas tengo en el schema public? Muéstrame la query SQL que ejecutaste."
    
    print("="*80)
    print("TEST DETALLADO - Query SQL del Agente")
    print("="*80)
    print(f"\n📝 Pregunta: {question}\n")
    
    try:
        response = requests.post(
            api_url,
            json={"question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta completa del agente:\n")
            print(data.get("answer", ""))
            print("\n" + "="*80)
            
            # Guardar respuesta
            with open("agent_detailed_response.json", "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print("\n💾 Respuesta guardada en: agent_detailed_response.json")
        else:
            print(f"❌ Error HTTP {response.status_code}:")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_agent_with_detailed_logging()
