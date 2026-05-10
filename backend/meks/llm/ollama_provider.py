from typing import AsyncGenerator

import httpx

from meks.config import settings
from meks.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or settings.chat_model
        self.base_url = settings.ollama_base_url

    async def stream_completion(self, prompt: str) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": True},
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break

    async def completion(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json()["response"]
