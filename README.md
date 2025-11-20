# Strands PostgreSQL Agent

Agente conversacional con Strands que se integra con PostgreSQL para responder preguntas sobre tus datos.

## Características

- 🔍 Consulta información de las tablas
- 📊 Ejecuta consultas SQL de forma natural
- 💬 Interfaz conversacional simple
- 🛡️ Solo permite consultas SELECT (lectura)

## Instalación

1. Instala las dependencias con uv:
```bash
uv sync --no-install-project
```

2. Crea tu archivo `.env` con las credenciales:
```bash
cp .env.example .env
# Edita .env con tus credenciales de PostgreSQL y OpenAI API key
```

## Uso

Ejecuta el agente con uv:
```bash
uv run python main.py
```

Luego puedes hacer preguntas como:
- "¿Qué tablas hay en la base de datos?"
- "Describe la tabla usuarios"
- "¿Cuántos registros hay en la tabla productos?"
- "Muéstrame los últimos 5 pedidos"

## Herramientas Disponibles

El agente tiene acceso a estas herramientas:

- **list_tables()**: Lista todas las tablas de la base de datos
- **describe_table(table_name)**: Muestra la estructura de una tabla
- **query_database(sql)**: Ejecuta consultas SELECT

## Seguridad

⚠️ El agente está configurado para ejecutar solo consultas SELECT. Sin embargo, siempre revisa que tu usuario de base de datos tenga permisos limitados de solo lectura en producción.

## Personalización

Puedes modificar el modelo de IA en `main.py`:
```python
agent = Agent(
    model="gpt-4o-mini",  # Cambia a "gpt-4" para mejor precisión
    ...
)
```
