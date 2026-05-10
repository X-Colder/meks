from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMProvider(ABC):
    @abstractmethod
    async def stream_completion(self, prompt: str) -> AsyncGenerator[str, None]:
        yield ""

    @abstractmethod
    async def completion(self, prompt: str) -> str:
        ...
