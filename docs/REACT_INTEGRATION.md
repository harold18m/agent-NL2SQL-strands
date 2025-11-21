# API de Integración con React

## Endpoint Principal: `/query`

### Request
```typescript
interface QueryRequest {
  question: string;           // Pregunta en lenguaje natural
  include_sql?: boolean;      // Incluir SQL en respuesta (default: true)
  format_response?: boolean;  // Sugerir visualización (default: true)
}
```

### Response
```typescript
interface AgentResponse {
  answer: string;                    // Respuesta en lenguaje natural
  sql_query: string | null;          // Query SQL ejecutado
  data: Array<Record<string, any>>;  // Datos crudos de la consulta
  visualization: VisualizationType;  // Tipo de visualización sugerida
  row_count: number;                 // Número de filas retornadas
  truncated: boolean;                // Si se truncaron resultados
  success: boolean;                  // Si la consulta fue exitosa
  error: string | null;              // Mensaje de error (si aplica)
  metadata: Record<string, any>;     // Metadatos adicionales
}

type VisualizationType = 
  | "table"       // Mostrar como tabla
  | "kpi"         // Mostrar como número grande (métrica)
  | "bar_chart"   // Gráfico de barras
  | "line_chart"  // Gráfico de líneas (series de tiempo)
  | "pie_chart"   // Gráfico circular
  | "text";       // Solo texto
```

## Ejemplos de Uso

### 1. Consulta Simple (KPI)

**Request:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuántos clientes hay?"}'
```

**Response:**
```json
{
  "answer": "There are 150 clients in the database.",
  "sql_query": "SELECT COUNT(*) FROM clientes;",
  "data": [{"count": 150}],
  "visualization": "kpi",
  "row_count": 1,
  "truncated": false,
  "success": true,
  "metadata": {
    "value": 150,
    "execution_time_seconds": 3.85
  }
}
```

**React Component:**
```tsx
function KPICard({ value, label }: { value: number; label: string }) {
  return (
    <div className="kpi-card">
      <h1>{value.toLocaleString()}</h1>
      <p>{label}</p>
    </div>
  );
}

// Uso:
<KPICard value={response.data[0].count} label="Total Clientes" />
```

---

### 2. Tabla de Datos

**Request:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Muestra los últimos 10 clientes"}'
```

**Response:**
```json
{
  "answer": "Here are the last 10 registered clients.",
  "sql_query": "SELECT * FROM clientes ORDER BY created_at DESC LIMIT 10;",
  "data": [
    {
      "id": 150,
      "nombre": "Juan Pérez",
      "email": "juan@example.com",
      "created_at": "2025-11-20T10:30:00Z"
    },
    // ... 9 more rows
  ],
  "visualization": "table",
  "row_count": 10,
  "truncated": false,
  "success": true,
  "metadata": {
    "column_count": 4,
    "row_count": 10,
    "execution_time_seconds": 4.12
  }
}
```

**React Component:**
```tsx
import { useTable } from 'react-table';

function DataTable({ data }: { data: Array<Record<string, any>> }) {
  const columns = React.useMemo(
    () =>
      Object.keys(data[0] || {}).map((key) => ({
        Header: key,
        accessor: key,
      })),
    [data]
  );

  const tableInstance = useTable({ columns, data });
  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } =
    tableInstance;

  return (
    <table {...getTableProps()}>
      <thead>
        {headerGroups.map((headerGroup) => (
          <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map((column) => (
              <th {...column.getHeaderProps()}>{column.render('Header')}</th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody {...getTableBodyProps()}>
        {rows.map((row) => {
          prepareRow(row);
          return (
            <tr {...row.getRowProps()}>
              {row.cells.map((cell) => (
                <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
```

---

### 3. Gráfico de Barras

**Request:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Ventas por mes en 2025"}'
```

**Response:**
```json
{
  "answer": "Here are the sales by month for 2025.",
  "sql_query": "SELECT EXTRACT(MONTH FROM fecha) as mes, SUM(total) as ventas FROM ventas WHERE EXTRACT(YEAR FROM fecha) = 2025 GROUP BY mes ORDER BY mes;",
  "data": [
    {"mes": 1, "ventas": 15000},
    {"mes": 2, "ventas": 18000},
    {"mes": 3, "ventas": 22000}
    // ...
  ],
  "visualization": "bar_chart",
  "row_count": 11,
  "truncated": false,
  "success": true,
  "metadata": {
    "category_column": "mes",
    "value_column": "ventas",
    "execution_time_seconds": 4.05
  }
}
```

**React Component (usando Recharts):**
```tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

function SalesChart({ data, metadata }: { data: any[]; metadata: any }) {
  return (
    <BarChart width={600} height={300} data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey={metadata.category_column} />
      <YAxis />
      <Tooltip />
      <Legend />
      <Bar dataKey={metadata.value_column} fill="#8884d8" />
    </BarChart>
  );
}
```

---

## Componente React Universal (Auto-render según tipo)

```tsx
import React from 'react';
import { AgentResponse, VisualizationType } from './types';

function QueryResult({ response }: { response: AgentResponse }) {
  if (!response.success) {
    return <ErrorAlert message={response.error || 'Unknown error'} />;
  }

  switch (response.visualization) {
    case 'kpi':
      return (
        <KPICard
          value={response.metadata.value}
          label={response.answer}
        />
      );

    case 'table':
      return (
        <>
          <p className="answer">{response.answer}</p>
          <DataTable data={response.data} />
        </>
      );

    case 'bar_chart':
      return (
        <>
          <p className="answer">{response.answer}</p>
          <SalesChart 
            data={response.data} 
            metadata={response.metadata} 
          />
        </>
      );

    case 'line_chart':
      return (
        <>
          <p className="answer">{response.answer}</p>
          <TimeSeriesChart 
            data={response.data} 
            metadata={response.metadata} 
          />
        </>
      );

    case 'pie_chart':
      return (
        <>
          <p className="answer">{response.answer}</p>
          <PieChart 
            data={response.data} 
            metadata={response.metadata} 
          />
        </>
      );

    default:
      return <p className="answer">{response.answer}</p>;
  }
}

// Hook para llamar al API
function useNL2SQL() {
  const [loading, setLoading] = React.useState(false);
  const [response, setResponse] = React.useState<AgentResponse | null>(null);

  const query = async (question: string) => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setResponse(data);
    } catch (error) {
      console.error('Query error:', error);
    } finally {
      setLoading(false);
    }
  };

  return { query, loading, response };
}

// App principal
function App() {
  const { query, loading, response } = useNL2SQL();
  const [question, setQuestion] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    query(question);
  };

  return (
    <div className="app">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your data..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Thinking...' : 'Ask'}
        </button>
      </form>

      {response && <QueryResult response={response} />}
      
      {/* Debug panel (optional) */}
      {response?.sql_query && (
        <details className="debug">
          <summary>SQL Query</summary>
          <pre>{response.sql_query}</pre>
        </details>
      )}
    </div>
  );
}
```

---

## Features Implementadas

✅ **Respuestas Estructuradas:** JSON listo para consumir en React  
✅ **Auto-detección de Visualización:** El backend sugiere el tipo de gráfico ideal  
✅ **CORS Habilitado:** Tu frontend puede conectarse sin problemas  
✅ **SQL Debugging:** Incluye el query ejecutado para transparencia  
✅ **Datos Crudos:** Acceso directo a los resultados para renderizar como quieras  
✅ **Metadata Rica:** Información adicional para configurar gráficos  
✅ **Manejo de Errores:** Respuestas consistentes incluso en caso de fallo  

---

## Próximos Pasos

1. **Testing:** Prueba el endpoint `/query` con `curl` o Postman
2. **Frontend:** Integra el hook `useNL2SQL()` en tu app React
3. **Librerías de Gráficos:** Instala `recharts`, `chart.js`, o `visx`
4. **Estilos:** Personaliza los componentes según tu diseño

¿Necesitas ayuda con algún componente específico? 🚀
