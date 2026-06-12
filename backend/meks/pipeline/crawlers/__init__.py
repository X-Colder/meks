from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class CrawlResult:
    external_id: str
    title: str
    authors: str
    abstract: str
    url: str
    published_date: date | None = None
    metadata: dict = field(default_factory=dict)


class BaseCrawler(ABC):
    @abstractmethod
    async def search(
        self, query: str, max_results: int = 20, watermark: str | None = None
    ) -> list[CrawlResult]: ...

    @abstractmethod
    async def download(self, result: CrawlResult) -> bytes: ...
