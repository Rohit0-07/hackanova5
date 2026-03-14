"""Semantic Scholar API integration for fetching paper references and citations."""

import hashlib
import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from app.services.crawler.sources.abstract_source import AbstractSource
from app.services.crawler.models import PaperMetadata, PaperIdentifier


SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,externalIds,title,authors,year,abstract,venue,referenceCount,citationCount,references,citations,url"
REF_FIELDS = "paperId,externalIds,title,authors,year,abstract,venue,referenceCount,citationCount,url"


class SemanticScholarSource(AbstractSource):
    """Fetches paper details, references, and citations from Semantic Scholar."""

    def __init__(self):
        self._rate_limit_delay = 1.0  # seconds between requests to respect rate limits

    @property
    def source_name(self) -> str:
        return "semantic_scholar"

    def _create_identifier(self, paper_data: Dict[str, Any]) -> PaperIdentifier:
        authors = [a.get("name", "") for a in paper_data.get("authors", [])]
        title = paper_data.get("title", "Unknown")
        year = paper_data.get("year") or ""
        external_ids = paper_data.get("externalIds") or {}

        hash_input = f"{title}{''.join(authors)}{year}"
        paper_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        return PaperIdentifier(
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            pubmed_id=external_ids.get("PubMed"),
            title=title,
            authors=authors,
            hash=paper_hash,
        )

    def _convert_to_metadata(self, paper_data: Dict[str, Any]) -> PaperMetadata:
        identifier = self._create_identifier(paper_data)
        year = paper_data.get("year")
        pub_date = datetime(year, 1, 1) if year else datetime(1970, 1, 1)

        # Build reference_list from references array if present
        ref_list = []
        for ref in paper_data.get("references", []):
            if ref and ref.get("title"):
                ref_list.append(ref["title"])

        return PaperMetadata(
            identifier=identifier,
            title=identifier.title,
            authors=identifier.authors,
            publication_date=pub_date,
            venue=paper_data.get("venue") or "",
            abstract=paper_data.get("abstract") or "",
            reference_list=ref_list,
            url=paper_data.get("url") or "",
            pdf_url=None,
            source_api=self.source_name,
        )

    async def _api_get(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a rate-limited GET request to the Semantic Scholar API."""
        url = f"{SEMANTIC_SCHOLAR_API}{endpoint}"
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(3):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code == 429:
                        logger.warning(f"Semantic Scholar rate limited (attempt {attempt+1}) — waiting 5s")
                        await asyncio.sleep(5)
                        continue
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        # Re-raise 404 so caller can handle it
                        raise
                    if attempt < 2:
                        logger.warning(f"Semantic Scholar error {e.response.status_code}, retrying...")
                        await asyncio.sleep(2)
                        continue
                    raise
            raise Exception("Max retries exceeded for Semantic Scholar API")

    async def search(self, query: str, max_results: int = 10) -> List[PaperMetadata]:
        """Search Semantic Scholar for papers matching a query."""
        logger.info(f"Searching Semantic Scholar for: {query}")
        data = await self._api_get(
            "/paper/search",
            params={
                "query": query,
                "limit": min(max_results, 100),
                "fields": REF_FIELDS,
            },
        )
        papers = data.get("data", [])
        return [self._convert_to_metadata(p) for p in papers if p]

    async def fetch_paper(self, paper_id: str) -> PaperMetadata:
        """Fetch full details for a single paper.

        paper_id can be: Semantic Scholar ID, ArXiv:XXXX, DOI:XXXX, etc.
        """
        # Strip version suffixes like v1, v2 from ArXiv IDs for S2
        if paper_id.startswith("ArXiv:"):
            import re
            paper_id = re.sub(r"v\d+$", "", paper_id)
            
        logger.info(f"Fetching Semantic Scholar paper: {paper_id}")
        data = await self._api_get(f"/paper/{paper_id}", params={"fields": FIELDS})
        return self._convert_to_metadata(data)

    async def fetch_references(
        self, paper_id: str, limit: int = 100
    ) -> List[PaperMetadata]:
        """Fetch all papers referenced BY this paper (outgoing citations).

        paper_id can be: S2 ID, ArXiv:XXXX, DOI:XXXX, PMID:XXXX, etc.
        """
        logger.info(f"Fetching references for paper: {paper_id}")
        data = await self._api_get(
            f"/paper/{paper_id}/references",
            params={"fields": REF_FIELDS, "limit": limit},
        )
        results = []
        for entry in data.get("data", []):
            cited_paper = entry.get("citedPaper")
            if cited_paper and cited_paper.get("title"):
                results.append(self._convert_to_metadata(cited_paper))
        return results

    async def fetch_citations(
        self, paper_id: str, limit: int = 100
    ) -> List[PaperMetadata]:
        """Fetch all papers that CITE this paper (incoming citations).

        paper_id can be: S2 ID, ArXiv:XXXX, DOI:XXXX, PMID:XXXX, etc.
        """
        logger.info(f"Fetching citations for paper: {paper_id}")
        data = await self._api_get(
            f"/paper/{paper_id}/citations",
            params={"fields": REF_FIELDS, "limit": limit},
        )
        results = []
        for entry in data.get("data", []):
            citing_paper = entry.get("citingPaper")
            if citing_paper and citing_paper.get("title"):
                results.append(self._convert_to_metadata(citing_paper))
        return results

    async def download_pdf(self, url: str, paper_id: str, output_dir: str) -> str:
        raise NotImplementedError("Semantic Scholar does not host PDFs directly")
