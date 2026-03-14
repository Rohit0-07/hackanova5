import os
import hashlib
import httpx
import arxiv
import asyncio
from typing import List
from datetime import datetime
from loguru import logger

from app.services.crawler.sources.abstract_source import AbstractSource
from app.services.crawler.models import PaperMetadata, PaperIdentifier
from app.core.config import settings


class ArxivSource(AbstractSource):
    @property
    def source_name(self) -> str:
        return "arxiv"

    def _create_identifier(self, result: arxiv.Result) -> PaperIdentifier:
        authors = [author.name for author in result.authors]
        # Hash creation for unique identification
        hash_input = f"{result.title}{''.join(authors)}{result.published.isoformat()}"
        paper_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        return PaperIdentifier(
            arxiv_id=result.get_short_id(),
            doi=result.doi,
            title=result.title,
            authors=authors,
            hash=paper_hash,
        )

    def _convert_to_metadata(self, result: arxiv.Result) -> PaperMetadata:
        identifier = self._create_identifier(result)

        return PaperMetadata(
            identifier=identifier,
            title=result.title,
            authors=identifier.authors,
            publication_date=result.published,
            venue="arXiv",
            abstract=result.summary,
            reference_list=[],  # arXiv API doesn't provide references natively without crawling the PDF
            url=result.entry_id,
            pdf_url=result.pdf_url,
            source_api=self.source_name,
        )

    async def search(self, query: str, max_results: int = 10) -> List[PaperMetadata]:
        """Search arXiv using their official python wrapper (executed in thread to avoid blocking)"""
        logger.info(f"Searching arXiv for: {query} (max: {max_results})")

        def _sync_search():
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            return list(client.results(search))

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _sync_search)

        return [self._convert_to_metadata(r) for r in results]

    async def fetch_paper(self, paper_id: str) -> PaperMetadata:
        """Fetch a specific paper from arXiv by ID"""
        logger.info(f"Fetching arXiv paper: {paper_id}")

        def _sync_fetch():
            client = arxiv.Client()
            search = arxiv.Search(id_list=[paper_id])
            results = list(client.results(search))
            if not results:
                raise ValueError(f"Paper {paper_id} not found on arXiv")
            return results[0]

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_fetch)

        return self._convert_to_metadata(result)

    async def download_pdf(self, url: str, paper_id: str, output_dir: str) -> str:
        """Download PDF from arXiv"""
        if not url:
            raise ValueError(f"No PDF URL provided for paper {paper_id}")

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{paper_id}.pdf"
        output_path = os.path.join(output_dir, filename)

        # Don't download again if it already exists
        if os.path.exists(output_path):
            logger.info(f"PDF already exists at {output_path}")
            return output_path

        logger.info(f"Downloading PDF from {url} to {output_path}")

        timeout = settings.crawler.request_timeout_seconds if settings else 30
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        return output_path
