from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from app.services.crawler.models import PaperMetadata


class AbstractSource(ABC):
    """Abstract interface for all research paper sources"""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the source API"""
        pass

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[PaperMetadata]:
        """Search the source for papers matching a query"""
        pass

    @abstractmethod
    async def fetch_paper(self, paper_id: str) -> PaperMetadata:
        """Fetch metadata for a specific paper by its source ID"""
        pass

    @abstractmethod
    async def download_pdf(self, url: str, paper_id: str, output_dir: str) -> str:
        """Download the PDF to the specified directory and return the path"""
        pass
