"""Google Scholar source using scholarly library with anti-blocking measures."""

import hashlib
import asyncio
import random
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from app.services.crawler.sources.abstract_source import AbstractSource
from app.services.crawler.models import PaperMetadata, PaperIdentifier
from app.core.rate_limiter import rate_limiter


class GoogleScholarSource(AbstractSource):
    """Fetches paper metadata and citations from Google Scholar.

    Uses the `scholarly` library with rate limiting and randomized delays
    to avoid getting blocked. Falls back gracefully on errors.
    """

    def __init__(self):
        self._scholarly = None  # lazy import

    def _get_scholarly(self):
        if self._scholarly is None:
            try:
                import scholarly as _scholarly_mod

                self._scholarly = _scholarly_mod
            except ImportError:
                raise ImportError(
                    "scholarly is not installed. Run: pip install scholarly"
                )
        return self._scholarly

    @property
    def source_name(self) -> str:
        return "google_scholar"

    def _create_identifier(self, pub: Dict[str, Any]) -> PaperIdentifier:
        bib = pub.get("bib", {})
        title = bib.get("title", "Unknown")
        authors = bib.get("author", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(" and ")]
        year = bib.get("pub_year", "")

        hash_input = f"{title}{''.join(authors)}{year}"
        paper_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        return PaperIdentifier(
            doi=None,
            arxiv_id=None,
            pubmed_id=None,
            title=title,
            authors=authors,
            hash=paper_hash,
        )

    def _convert_to_metadata(self, pub: Dict[str, Any]) -> PaperMetadata:
        identifier = self._create_identifier(pub)
        bib = pub.get("bib", {})
        year_str = bib.get("pub_year", "")
        try:
            pub_date = (
                datetime(int(year_str), 1, 1) if year_str else datetime(1970, 1, 1)
            )
        except (ValueError, TypeError):
            pub_date = datetime(1970, 1, 1)

        return PaperMetadata(
            identifier=identifier,
            title=identifier.title,
            authors=identifier.authors,
            publication_date=pub_date,
            venue=bib.get("venue", "") or bib.get("journal", "") or "",
            abstract=bib.get("abstract", "") or "",
            reference_list=[],
            url=pub.get("pub_url", "") or pub.get("eprint_url", "") or "",
            pdf_url=pub.get("eprint_url"),
            source_api=self.source_name,
        )

    async def search(self, query: str, max_results: int = 10) -> List[PaperMetadata]:
        """Search Google Scholar for papers matching a query."""
        logger.info(f"Searching Google Scholar for: {query} (max: {max_results})")
        await rate_limiter.acquire("google_scholar", add_jitter=True)

        scholarly = self._get_scholarly()

        def _sync_search():
            results = []
            try:
                search_query = scholarly.search_pubs(query)
                for _ in range(max_results):
                    try:
                        pub = next(search_query)
                        results.append(pub)
                    except StopIteration:
                        break
            except Exception as e:
                logger.warning(f"Google Scholar search error: {e}")
            return results

        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(None, _sync_search)

        papers = []
        for pub in raw_results:
            try:
                papers.append(self._convert_to_metadata(pub))
            except Exception as e:
                logger.warning(f"Failed to convert GS result: {e}")

        logger.info(f"Google Scholar returned {len(papers)} results")
        return papers

    async def fetch_paper(self, paper_id: str) -> PaperMetadata:
        """Search for a specific paper by title on Google Scholar."""
        logger.info(f"Fetching paper from Google Scholar: {paper_id}")
        await rate_limiter.acquire("google_scholar", add_jitter=True)

        scholarly = self._get_scholarly()

        def _sync_fetch():
            search_query = scholarly.search_pubs(paper_id)
            try:
                pub = next(search_query)
                return pub
            except StopIteration:
                return None

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_fetch)

        if not result:
            raise ValueError(f"Paper not found on Google Scholar: {paper_id}")

        return self._convert_to_metadata(result)

    async def get_citing_papers(
        self, title: str, max_results: int = 20
    ) -> List[PaperMetadata]:
        """Get papers that cite a given paper (by title search).

        This is Google Scholar's unique strength — it tracks citations
        even for papers not on arXiv or S2.
        """
        logger.info(f"Getting citing papers for: {title[:60]}...")
        await rate_limiter.acquire("google_scholar", add_jitter=True)

        scholarly = self._get_scholarly()

        def _sync_get_citations():
            results = []
            try:
                search_query = scholarly.search_pubs(title)
                pub = next(search_query)
                # Fill the publication to get citedby link
                pub_filled = scholarly.fill(pub)
                citations = scholarly.citedby(pub_filled)
                for _ in range(max_results):
                    try:
                        citing = next(citations)
                        results.append(citing)
                    except StopIteration:
                        break
            except Exception as e:
                logger.warning(f"Google Scholar citation fetch error: {e}")
            return results

        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(None, _sync_get_citations)

        papers = []
        for pub in raw_results:
            try:
                papers.append(self._convert_to_metadata(pub))
            except Exception as e:
                logger.warning(f"Failed to convert GS citation: {e}")

        logger.info(f"Found {len(papers)} citing papers")
        return papers

    async def download_pdf(self, url: str, paper_id: str, output_dir: str) -> str:
        raise NotImplementedError(
            "Google Scholar does not directly host PDFs. Use the eprint_url if available."
        )
