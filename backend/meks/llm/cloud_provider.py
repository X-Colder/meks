from typing import AsyncGenerator

import httpx

from meks.config import settings
from meks.llm.base import LLMProvider


class CloudProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.anthropic_api_key or settings.openai_api_key
        self.provider = "anthropic" if settings.anthropic_api_key else "openai"

    async def stream_completion(self, prompt: str) -> AsyncGenerator[str, None]:
        if self.provider == "anthropic":
            async for token in self._stream_anthropic(prompt):
                yield token
        else:
            async for token in self._stream_openai(prompt):
                yield token

    async def completion(self, prompt: str) -> str:
        tokens = []
        async for token in self.stream_completion(prompt):
            tokens.append(token)
        return "".join(tokens)

    async def _stream_anthropic(self, prompt: str) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "stream": True,
                    "messages": [{"role": "user", "content": prompt}],
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            yield data["delta"].get("text", "")

    async def _stream_openai(self, prompt: str) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "stream": True,
                    "messages": [{"role": "user", "content": prompt}],
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
