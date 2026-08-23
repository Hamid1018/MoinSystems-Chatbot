from groq import AsyncGroq
from app.core.config import settings
from app.llm.base import BaseLLMProvider

class GroqProvider(BaseLLMProvider):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        # llama-3.3-70b-versatile provides high intelligence and strict guardrail adherence
       # The standard 8B model is incredibly fast and perfect for RAG tasks
        self.model_name = "openai/gpt-oss-20b"

    async def generate_response(self, system_instruction: str, user_prompt: str) -> str:
        chat_completion = await self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            model=self.model_name,
            temperature=0.2,
        )
        return chat_completion.choices[0].message.content or ""