import json
from typing import AsyncGenerator

import httpx

from meks.config import settings
from meks.llm.base import LLMProvider

PROVIDER_DEFAULTS: dict[str, tuple[str, str]] = {
    "anthropic": ("api.anthropic.com", "claude-sonnet-4-20250514"),
    "openai": ("api.openai.com", "gpt-4o"),
    "deepseek": ("api.deepseek.com", "deepseek-chat"),
    "zhipu": ("open.bigmodel.cn/api/paas/v4", "glm-4-plus"),
    "qianwen": ("dashscope.aliyuncs.com/compatible-mode", "qwen-max"),
}


class CloudProvider(LLMProvider):
    def __init__(self):
        self.provider = settings.cloud_provider
        self.api_key = settings.effective_cloud_api_key
        if not self.api_key:
            raise RuntimeError(
                "云端 LLM API Key 未配置：请设置 MEKS_CLOUD_API_KEY、"
                "MEKS_OPENAI_API_KEY、OPENAI_API_KEY 或 CODEX_API_KEY"
            )
        default_base, default_model = PROVIDER_DEFAULTS.get(self.provider, PROVIDER_DEFAULTS["openai"])
        self.base_url = settings.effective_cloud_api_base or f"https://{default_base}"
        self.model = settings.effective_cloud_model or default_model
        self.wire_api = settings.effective_cloud_wire_api

    async def stream_completion(self, prompt: str) -> AsyncGenerator[str, None]:
        if self.provider == "anthropic":
            async for token in self._stream_anthropic(prompt):
                yield token
        elif self.wire_api == "responses":
            async for token in self._stream_openai_responses(prompt):
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
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "stream": True,
                    "messages": [{"role": "user", "content": prompt}],
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            yield data["delta"].get("text", "")

    async def _stream_openai(self, prompt: str) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "stream": True,
                    "messages": [{"role": "user", "content": prompt}],
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def _stream_openai_responses(self, prompt: str) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": prompt,
                    "stream": True,
                    "max_output_tokens": 4096,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    data = json.loads(line[6:])
                    event_type = data.get("type")
                    if event_type == "response.output_text.delta":
                        yield data.get("delta", "")
