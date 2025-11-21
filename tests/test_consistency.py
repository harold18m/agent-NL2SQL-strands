"""
Test de Consistencia: Ejecutar la misma pregunta múltiples veces
para ver si el agente da respuestas consistentes
"""
import requests
import re
from typing import Optional

def extract_number_from_response(response: str) -> Optional[int]:
    """Extrae el número de tablas de la respuesta del agente"""
    # Buscar patrones como "40 tablas", "Hay 40", etc.
    patterns = [
        r'(\d+)\s+tablas',
        r'Hay\s+(\d+)',
        r'son\s+(\d+)',
        r'total.*?(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None

def run_consistency_test(iterations: int = 5):
    """
    Ejecuta la misma pregunta múltiples veces y compara resultados
    """
    api_url = "http://localhost:8000/ask"
    question = "¿Cuántas tablas tengo en el schema public?"
    
    print("="*80)
    print(f"TEST DE CONSISTENCIA - {iterations} iteraciones")
    print("="*80)
    print(f"\n📝 Pregunta: {question}\n")
    print("Ejecutando múltiples consultas al agente...\n")
    
    results = []
    
    for i in range(1, iterations + 1):
        try:
            response = requests.post(
                api_url,
                json={"question": question},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                number = extract_number_from_response(answer)
                
                results.append({
                    "iteration": i,
                    "answer": answer.strip(),
                    "extracted_number": number
                })
                
                print(f"  Iteración {i}: {number} tablas")
            else:
                print(f"  Iteración {i}: ERROR HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  Iteración {i}: ERROR - {e}")
    
    print("\n" + "="*80)
    print("📊 ANÁLISIS DE RESULTADOS")
    print("="*80)
    
    # Extraer solo los números
    numbers = [r["extracted_number"] for r in results if r["extracted_number"] is not None]
    
    if numbers:
        print(f"\nNúmeros reportados: {numbers}")
        print(f"Valor mínimo: {min(numbers)}")
        print(f"Valor máximo: {max(numbers)}")
        print(f"Valores únicos: {set(numbers)}")
        print(f"Cantidad de respuestas diferentes: {len(set(numbers))}")
        
        if len(set(numbers)) == 1:
            print("\n✅ CONSISTENTE: El agente dio la misma respuesta en todas las iteraciones")
        else:
            print("\n❌ INCONSISTENTE: El agente dio respuestas diferentes!")
            print("\nDistribución de respuestas:")
            for num in set(numbers):
                count = numbers.count(num)
                percentage = (count / len(numbers)) * 100
                print(f"  {num} tablas: {count} veces ({percentage:.1f}%)")
        
        # Comparar con la verdad
        TRUE_COUNT = 33
        print(f"\n🎯 Valor real: {TRUE_COUNT} tablas")
        
        correct_count = numbers.count(TRUE_COUNT)
        if correct_count > 0:
            accuracy = (correct_count / len(numbers)) * 100
            print(f"✅ Precisión: {accuracy:.1f}% ({correct_count}/{len(numbers)} respuestas correctas)")
        else:
            print(f"❌ Precisión: 0% - El agente NUNCA acertó el número correcto")
            
        # Calcular error promedio
        avg_error = sum(abs(n - TRUE_COUNT) for n in numbers) / len(numbers)
        print(f"📉 Error promedio: ±{avg_error:.1f} tablas")
    
    print("\n" + "="*80)
    
    # Guardar resultados detallados
    import json
    with open("consistency_test_results.json", "w") as f:
        json.dump({
            "iterations": iterations,
            "question": question,
            "true_count": 33,
            "results": results,
            "summary": {
                "unique_values": list(set(numbers)) if numbers else [],
                "is_consistent": len(set(numbers)) == 1 if numbers else False,
                "accuracy": (numbers.count(33) / len(numbers) * 100) if numbers else 0
            }
        }, f, indent=2, ensure_ascii=False)
    
    print("💾 Resultados detallados guardados en: consistency_test_results.json")

if __name__ == "__main__":
    run_consistency_test(iterations=5)
