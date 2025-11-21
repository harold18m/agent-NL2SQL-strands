"""
Test de reproducción: "Último cliente"
Verifica qué query genera el agente para "el último cliente"
"""
import requests
import json

def test_last_client():
    api_url = "http://localhost:8000/ask"
    question = "¿Cuál es el último cliente registrado? Muéstrame su razón social y fecha de creación."
    
    print("="*80)
    print("TEST: ÚLTIMO CLIENTE")
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
            print("✅ Respuesta del agente:\n")
            print(data.get("answer", ""))
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_last_client()
