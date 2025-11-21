"""
Test de Performance: Mide el tiempo de respuesta del agente
"""
import requests
import time
import statistics

def test_performance(iterations: int = 5):
    api_url = "http://localhost:8000/ask"
    question = "¿Cuántos clientes hay?"
    
    print("="*80)
    print(f"TEST DE PERFORMANCE - {iterations} iteraciones")
    print("="*80)
    print(f"Pregunta: {question}\n")
    
    times = []
    
    for i in range(1, iterations + 1):
        start_time = time.time()
        try:
            response = requests.post(
                api_url,
                json={"question": question},
                timeout=30
            )
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                print(f"  Iteración {i}: {duration:.2f} segundos ✅")
                times.append(duration)
            else:
                print(f"  Iteración {i}: ERROR HTTP {response.status_code} ({duration:.2f}s) ❌")
                
        except Exception as e:
            print(f"  Iteración {i}: ERROR {e} ❌")
    
    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        print("\n" + "-"*80)
        print(f"📊 RESULTADOS:")
        print(f"   Promedio: {avg_time:.2f} segundos")
        print(f"   Mínimo:   {min_time:.2f} segundos")
        print(f"   Máximo:   {max_time:.2f} segundos")
        print("-" * 80)
        
        if avg_time < 2.0:
            print("🚀 Performance EXCELENTE (< 2s)")
        elif avg_time < 5.0:
            print("✅ Performance ACEPTABLE (< 5s)")
        else:
            print("⚠️  Performance LENTO (> 5s)")

if __name__ == "__main__":
    print("⚠️  NOTA: Asegúrate de reiniciar el servidor para aplicar las optimizaciones de DB Pool")
    test_performance()
