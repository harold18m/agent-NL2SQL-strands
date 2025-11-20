import dotenv
import os
from strands import Agent
from strands.models.gemini import GeminiModel
from strands_tools import calculator

dotenv.load_dotenv()

model = GeminiModel(
    client_args={
        "api_key": os.getenv("GEMINI_API_KEY"),
    },
    # **model_config
    model_id="gemini-2.5-flash"
)

agent = Agent(model=model, tools=[calculator])
response = agent("What is 2+2")
print(response)