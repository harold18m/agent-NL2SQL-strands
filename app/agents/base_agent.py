from abc import ABC, abstractmethod
from strands import Agent

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.agent = None

    @abstractmethod
    def create_agent(self) -> Agent:
        pass

    def run(self, input_text: str):
        if not self.agent:
            self.agent = self.create_agent()
        return self.agent(input_text)
