# 🎯 Optimización de Tokens para NL2SQL Agent

## Tabla de Contenidos
1. [Descripciones en Prisma Schema](#1-descripciones-en-prisma-schema)
2. [Contador de Tokens](#2-contador-de-tokens)
3. [Técnica TOON (Tool Output Optimization for NL)](#3-técnica-toon)

---

## 1. Descripciones en Prisma Schema

### En tu archivo `schema.prisma` (Node.js Backend)

Prisma soporta comentarios con `///` que se sincronizan automáticamente con PostgreSQL:

```prisma
/// Clientes de la empresa - Personas o empresas que compran productos
model clientes {
  /// Identificador único del cliente (autoincremental)
  id            Int      @id @default(autoincrement())
  
  /// Razón social o nombre completo del cliente
  razon_social  String   @db.VarChar(255)
  
  /// RUC o DNI del cliente (único, usado para facturación)
  ruc           String   @unique @db.VarChar(20)
  
  /// Dirección fiscal del cliente
  direccion     String?  @db.Text
  
  /// Fecha de registro en el sistema
  created_at    DateTime @default(now())
  
  /// Última actualización del registro
  updated_at    DateTime @updatedAt
  
  /// Órdenes de compra del cliente
  ordenes       ordenes_compra[]
  
  @@map("clientes")
}

/// Órdenes de compra - Pedidos realizados por los clientes
model ordenes_compra {
  /// ID único de la orden
  id              Int      @id @default(autoincrement())
  
  /// Número de orden visible (formato: OC-2025-0001)
  numero_orden    String   @unique @db.VarChar(50)
  
  /// Cliente que realizó la orden
  cliente_id      Int
  cliente         clientes @relation(fields: [cliente_id], references: [id])
  
  /// Estado actual: PENDIENTE, EN_PROCESO, COMPLETADA, CANCELADA
  estado          String   @default("PENDIENTE") @db.VarChar(20)
  
  /// Monto total de la orden (incluye IGV)
  total           Decimal  @db.Decimal(12, 2)
  
  /// Fecha de creación de la orden
  created_at      DateTime @default(now())
  
  @@index([cliente_id])
  @@index([estado])
  @@index([created_at])
  @@map("ordenes_compra")
}
```

### Sincronizar Comentarios a PostgreSQL

Después de definir tu schema con comentarios, ejecuta:

```bash
# Generar migración que incluye los comentarios
npx prisma migrate dev --name add_schema_comments

# O aplicar directamente (solo desarrollo)
npx prisma db push
```

### Script SQL Manual (si ya tienes datos)

Si no quieres regenerar migraciones, ejecuta este SQL directamente:

```sql
-- Comentarios de tablas
COMMENT ON TABLE clientes IS 'Clientes de la empresa - Personas o empresas que compran productos';
COMMENT ON TABLE ordenes_compra IS 'Órdenes de compra - Pedidos realizados por los clientes';
COMMENT ON TABLE productos IS 'Catálogo de productos disponibles para venta';
COMMENT ON TABLE facturaciones IS 'Facturas emitidas por las ventas';

-- Comentarios de columnas (tabla clientes)
COMMENT ON COLUMN clientes.id IS 'Identificador único del cliente (autoincremental)';
COMMENT ON COLUMN clientes.razon_social IS 'Razón social o nombre completo del cliente';
COMMENT ON COLUMN clientes.ruc IS 'RUC o DNI del cliente (único, usado para facturación)';
COMMENT ON COLUMN clientes.direccion IS 'Dirección fiscal del cliente';
COMMENT ON COLUMN clientes.created_at IS 'Fecha de registro en el sistema';

-- Comentarios de columnas (tabla ordenes_compra)
COMMENT ON COLUMN ordenes_compra.id IS 'ID único de la orden';
COMMENT ON COLUMN ordenes_compra.numero_orden IS 'Número de orden visible (formato: OC-2025-0001)';
COMMENT ON COLUMN ordenes_compra.cliente_id IS 'FK: Cliente que realizó la orden';
COMMENT ON COLUMN ordenes_compra.estado IS 'Estado actual: PENDIENTE, EN_PROCESO, COMPLETADA, CANCELADA';
COMMENT ON COLUMN ordenes_compra.total IS 'Monto total de la orden (incluye IGV)';
COMMENT ON COLUMN ordenes_compra.created_at IS 'Fecha de creación de la orden';

-- Continúa con tus otras tablas...
```

### Script de Generación Automática

```javascript
// generate-comments.js (Node.js)
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Define tus descripciones aquí
const tableDescriptions = {
  clientes: 'Clientes de la empresa - Personas o empresas que compran productos',
  ordenes_compra: 'Órdenes de compra - Pedidos realizados por los clientes',
  productos: 'Catálogo de productos disponibles para venta',
  proveedores: 'Proveedores que suministran productos',
  facturaciones: 'Facturas emitidas por ventas realizadas',
  // Agrega todas tus tablas...
};

const columnDescriptions = {
  // formato: 'tabla.columna': 'descripción'
  'clientes.id': 'ID único autoincremental',
  'clientes.razon_social': 'Nombre o razón social',
  'clientes.ruc': 'RUC/DNI único para facturación',
  'clientes.created_at': 'Fecha de registro',
  'ordenes_compra.estado': 'Estado: PENDIENTE, EN_PROCESO, COMPLETADA, CANCELADA',
  'ordenes_compra.total': 'Monto total con IGV',
  // Agrega todas tus columnas importantes...
};

async function applyComments() {
  // Aplicar comentarios de tablas
  for (const [table, description] of Object.entries(tableDescriptions)) {
    await prisma.$executeRawUnsafe(
      `COMMENT ON TABLE "${table}" IS '${description.replace(/'/g, "''")}'`
    );
    console.log(`✅ Tabla: ${table}`);
  }
  
  // Aplicar comentarios de columnas
  for (const [key, description] of Object.entries(columnDescriptions)) {
    const [table, column] = key.split('.');
    await prisma.$executeRawUnsafe(
      `COMMENT ON COLUMN "${table}"."${column}" IS '${description.replace(/'/g, "''")}'`
    );
    console.log(`✅ Columna: ${key}`);
  }
  
  console.log('\n🎉 Comentarios aplicados exitosamente!');
}

applyComments()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
```

---

## 2. Contador de Tokens

El contador de tokens está implementado en `app/services/token_counter.py`.

### Uso en tu código

```python
from app.services.token_counter import get_token_counter, count_tokens

# Estimar tokens de un texto
tokens = count_tokens("SELECT * FROM clientes WHERE id = 1")
print(f"Tokens estimados: {tokens}")

# Contar una request completa
counter = get_token_counter()
usage = counter.count_request(
    system_prompt="You are an SQL assistant...",
    schema="Table: clientes (id, nombre, ruc)",
    user_query="¿Cuántos clientes hay?",
    tool_outputs=["{'count': 150}"],
    model_response="Hay 150 clientes en la base de datos."
)

print(f"Input tokens: {usage.input_tokens}")
print(f"Output tokens: {usage.output_tokens}")
print(f"Costo estimado: ${usage.estimated_cost_usd}")
```

### API Endpoints

```bash
# Ver estadísticas de tokens
curl http://localhost:8000/stats/tokens

# Resetear estadísticas
curl -X POST http://localhost:8000/stats/tokens/reset

# Exportar historial
curl http://localhost:8000/stats/tokens/export
```

### Ejemplo de Respuesta `/stats/tokens`

```json
{
  "session_stats": {
    "input_tokens": 12500,
    "output_tokens": 3200,
    "total_tokens": 15700,
    "requests": 10,
    "estimated_cost_usd": 0.001857,
    "avg_tokens_per_request": 1570
  },
  "optimization_suggestions": [
    "⚠️ Schema muy grande (1200 tokens). Considera: filtrar tablas relevantes.",
    "✅ Uso de tokens dentro de rangos óptimos para outputs."
  ],
  "toon_status": "enabled"
}
```

---

## 3. Técnica TOON (Tool Output Optimization for NL)

TOON es una técnica para reducir el consumo de tokens en las salidas de herramientas sin perder información relevante.

### ¿Por qué TOON?

| Problema | Sin TOON | Con TOON |
|----------|----------|----------|
| Query retorna 50 filas | ~2000 tokens | ~800 tokens |
| Schema con 33 tablas | ~1500 tokens | ~600 tokens |
| Campos redundantes (created_at, etc.) | Incluidos siempre | Filtrados si no se preguntan |

### Técnicas Implementadas

#### 1. **Filtrado de Campos Redundantes**
```python
# Campos que se eliminan automáticamente (si no se preguntan):
REDUNDANT_FIELDS = {
    "created_at", "updated_at", "deleted_at",
    "password", "password_hash", "token",
    "metadata", "extra_data", "raw_data",
}
```

#### 2. **Compresión de Valores Largos**
```python
# Antes (120 caracteres):
{"descripcion": "Este es un texto muy largo que describe el producto en detalle con muchas palabras innecesarias..."}

# Después (100 caracteres + indicador):
{"descripcion": "Este es un texto muy largo que describe el producto en detalle con muchas palabras..."}
```

#### 3. **Formato Compacto**
```python
toon = get_toon_optimizer()

# Formato ultra-compacto (menos tokens)
compact = toon.format_for_llm(data, format_type="compact")
# Output: "1. id=1 | nombre=Juan | total=150.00"

# Formato JSON compacto
json_compact = toon.format_for_llm(data, format_type="json")
# Output: [{"id":1,"nombre":"Juan","total":150.00}]
```

#### 4. **Resumen Estadístico**
Para queries grandes, TOON genera un resumen:
```
"Total: 500 rows (showing first 20) | Avg total: 1250.50"
```

### Configuración

En `app/tools/postgres.py`:

```python
# Activar/desactivar TOON globalmente
TOON_ENABLED = True

# O configurar límites personalizados
from app.services.toon_optimizer import TOONOptimizer

optimizer = TOONOptimizer(
    max_rows=20,           # Máximo filas a mostrar al LLM
    max_chars_per_field=100  # Truncar campos largos
)
```

### Ejemplo de Optimización

**Query Original:**
```sql
SELECT * FROM ordenes_compra ORDER BY created_at DESC LIMIT 10;
```

**Sin TOON (1200 tokens):**
```json
[
  {
    "id": 1,
    "numero_orden": "OC-2025-0001",
    "cliente_id": 5,
    "estado": "COMPLETADA",
    "total": 15000.00,
    "created_at": "2025-11-20T10:30:00Z",
    "updated_at": "2025-11-20T15:45:00Z",
    "deleted_at": null,
    "metadata": {"source": "web", "ip": "192.168.1.1", ...},
    ...
  },
  // 9 more rows with all fields
]
```

**Con TOON (400 tokens):**
```json
{
  "optimized_data": [
    {"id": 1, "numero_orden": "OC-2025-0001", "estado": "COMPLETADA", "total": 15000.00},
    // 9 more rows, campos relevantes solamente
  ],
  "row_count": 10,
  "summary": "Total: 10 rows | Avg total: 12500.00"
}
```

**Ahorro: 67% menos tokens** 🎉

---

## 4. Mejores Prácticas

### Para tu Schema Prisma

1. **Descripciones cortas pero informativas:**
   ```prisma
   /// Cliente - Comprador de productos (RUC único)
   model clientes { ... }
   ```

2. **Documenta valores de enums:**
   ```prisma
   /// Estado: PENDIENTE | EN_PROCESO | COMPLETADA | CANCELADA
   estado String @default("PENDIENTE")
   ```

3. **Marca campos importantes:**
   ```prisma
   /// FK: ID del cliente que realizó la orden
   cliente_id Int
   ```

### Para reducir tokens en runtime

1. **Selecciona solo columnas necesarias:**
   ```sql
   -- ❌ Mal
   SELECT * FROM clientes
   
   -- ✅ Bien
   SELECT id, nombre, ruc FROM clientes
   ```

2. **Usa agregaciones cuando sea posible:**
   ```sql
   -- ❌ Trae 5000 filas y cuenta en el LLM
   SELECT * FROM ordenes_compra
   
   -- ✅ Cuenta en la DB
   SELECT COUNT(*) FROM ordenes_compra
   ```

3. **Filtra en la query, no en el LLM:**
   ```sql
   -- ❌ Trae todo y filtra mentalmente
   SELECT * FROM clientes
   
   -- ✅ Filtra en SQL
   SELECT * FROM clientes WHERE estado = 'ACTIVO' LIMIT 10
   ```

---

## 5. Monitoreo de Costos

### Dashboard de Costos (Ejemplo React)

```tsx
function TokenDashboard() {
  const [stats, setStats] = useState(null);
  
  useEffect(() => {
    fetch('http://localhost:8000/stats/tokens')
      .then(res => res.json())
      .then(setStats);
  }, []);
  
  if (!stats) return <div>Loading...</div>;
  
  return (
    <div className="token-dashboard">
      <div className="stat-card">
        <h3>Total Tokens</h3>
        <p>{stats.session_stats.total_tokens.toLocaleString()}</p>
      </div>
      
      <div className="stat-card">
        <h3>Costo Estimado</h3>
        <p>${stats.session_stats.estimated_cost_usd.toFixed(4)}</p>
      </div>
      
      <div className="stat-card">
        <h3>Promedio/Request</h3>
        <p>{stats.session_stats.avg_tokens_per_request}</p>
      </div>
      
      <div className="suggestions">
        <h3>Sugerencias de Optimización</h3>
        <ul>
          {stats.optimization_suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

---

## Resumen de Archivos Creados

| Archivo | Propósito |
|---------|-----------|
| `app/services/token_counter.py` | Contador y estimador de tokens |
| `app/services/toon_optimizer.py` | Optimizador TOON para reducir tokens |
| `docs/TOKEN_OPTIMIZATION.md` | Esta documentación |

## Endpoints Agregados

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/stats/tokens` | GET | Estadísticas de tokens de la sesión |
| `/stats/tokens/reset` | POST | Reiniciar estadísticas |
| `/stats/tokens/export` | GET | Exportar historial a JSON |

---

## Próximos Pasos

1. ✅ **Implementar comentarios en Prisma** - Mejora la comprensión del LLM
2. ✅ **Activar TOON** - Ya está activo por defecto
3. 📊 **Monitorear costos** - Usa `/stats/tokens` regularmente
4. 🎯 **Schema RAG** (Fase avanzada) - Seleccionar solo tablas relevantes por pregunta

¿Necesitas ayuda implementando algo específico?
