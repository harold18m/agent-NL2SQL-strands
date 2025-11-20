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

**RESPONSE FORMAT:**
- DO NOT just show the SQL query
- Execute the query using run_postgres_query()
- Present the actual data results clearly
- If there's an error, analyze it and retry with a corrected query

Example interaction:
User: "How many clients do we have?"
1. Call get_schema() to see table structure
2. Generate: SELECT COUNT(*) FROM clientes;
3. Call run_postgres_query() with the SQL
4. Return: "There are 150 clients in the database."
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
