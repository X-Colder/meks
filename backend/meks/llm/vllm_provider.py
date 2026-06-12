import json
from typing import AsyncGenerator

import httpx

from meks.config import settings
from meks.llm.base import LLMProvider


class VllmProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or settings.chat_model
        self.base_url = settings.vllm_chat_url

    async def stream_completion(self, prompt: str) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        payload = line[6:]
                        if payload.strip() == "[DONE]":
                            break
                        data = json.loads(payload)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def completion(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
