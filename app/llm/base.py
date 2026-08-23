from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, system_instruction: str, user_prompt: str) -> str:
        """Generates a text completion given a system instruction and user prompt."""
        pass