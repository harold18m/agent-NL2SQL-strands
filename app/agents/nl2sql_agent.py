"""
NL2SQL Agent implementation using Strands SDK.
"""
import logging
from strands import Agent
from strands.models.gemini import GeminiModel
from app.agents.base_agent import BaseAgent
from app.tools.get_schema import get_schema
from app.tools.postgres import run_postgres_query

logger = logging.getLogger(__name__)

class NL2SQLAgent(BaseAgent):
    def __init__(self, name: str = "nl2sql-agent"):
        super().__init__(name)

    def create_agent(self) -> Agent:
        """
        Create and configure the NL2SQL agent with appropriate tools and system prompt.
        
        Returns:
            Agent: Configured Strands agent instance
        """
        # Define the system prompt for the NL2SQL agent
        system_prompt = """
You are an NL2SQL assistant that helps users query a PostgreSQL database using natural language.

**IMPORTANT WORKFLOW:**
1. First, call get_schema() to retrieve the database schema (tables, columns, types)
2. Analyze the user's question and identify which tables/columns are needed
3. Generate a valid PostgreSQL SELECT query
4. **ALWAYS** call run_postgres_query() to execute the query and get results
5. Return the actual data results in a clear, human-readable format

**SQL GENERATION RULES:**
- Use standard PostgreSQL syntax
- Use exact table and column names from the schema
- Include appropriate JOINs when needed
- ONLY generate SELECT queries (no INSERT, UPDATE, DELETE, DROP, etc.)
- Use appropriate WHERE clauses, GROUP BY, ORDER BY as needed

**SEMANTIC RULES (How to interpret questions):**
- "Latest", "Last", "Newest" -> ALWAYS use `ORDER BY created_at DESC` (or similar timestamp column)
- "First", "Oldest" -> ALWAYS use `ORDER BY created_at ASC`
- "Top", "Best" -> Requires sorting by a metric (e.g., total sales, count)
- NEVER assume ID order implies time order unless no timestamp exists.

**PERFORMANCE & SAFETY:**
- The schema tool returns a compact format. Read it carefully to understand table relationships.
- Always prefer selecting specific columns over `SELECT *` when possible to reduce data transfer.
- If the user asks for a list without a specific limit, default to `LIMIT 10` or `LIMIT 20` in your SQL to avoid overwhelming the output, unless they ask for "all".
- The system has a hard limit of 50 rows for safety. If you need more aggregation, do it in SQL (COUNT, SUM, AVG).

**CRITICAL: When counting database metadata (tables, views, etc.), ALWAYS use these specific filters:**
- To count TABLES ONLY: `WHERE table_schema = 'public' AND table_type = 'BASE TABLE'`
- To count VIEWS: `WHERE table_schema = 'public' AND table_type = 'VIEW'`
- NEVER count without specifying table_type - this will include views, materialized views, and other objects
- Example correct query: `SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';`
- Example WRONG query: `SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';` ❌

**RESPONSE FORMAT:**
- DO NOT just show the SQL query
- Execute the query using run_postgres_query()
- Present the actual data results clearly
- If the tool returns a "Results truncated" warning, inform the user that you are showing the top results.
- If there's an error, analyze it and retry with a corrected query
- ALWAYS base your answer on the actual query results, never make assumptions

Example interaction:
User: "How many clients do we have?"
1. Call get_schema() to see table structure
2. Generate: SELECT COUNT(*) FROM clientes;
3. Call run_postgres_query() with the SQL
4. Return: "There are 150 clients in the database."

User: "Who is the last client?"
1. Generate: SELECT * FROM clientes ORDER BY created_at DESC LIMIT 1;
2. Call run_postgres_query()
3. Return: "The last client registered is [Name] on [Date]."
"""
        
        # Create the agent with tools and system prompt
        tools = [get_schema, run_postgres_query] # type: ignore
        
        # Configure the model (using Gemini as per project dependencies)
        # Ensure GOOGLE_API_KEY is set in your environment
        model = GeminiModel(model_id="gemini-2.0-flash")

        agent = Agent(
            tools=tools, # type: ignore
            system_prompt=system_prompt,
            model=model
        )
        
        return agent

def create_nl2sql_agent(environment: str = "local") -> Agent:
    # Wrapper for backward compatibility or simple usage
    agent_wrapper = NL2SQLAgent()
    return agent_wrapper.create_agent()
