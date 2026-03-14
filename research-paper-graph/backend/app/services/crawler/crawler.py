"""Research Crawler — autonomous BFS citation trail engine.

This is the core pipeline:
  User Query → QueryAgent → Multi-Source Search → BFS Citation Crawl
  → Content Extraction → Analysis Agent → Result
"""

import re
import os
import uuid
import asyncio
import time
from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from loguru import logger
from collections import deque

from app.services.crawler.models import (
    PaperMetadata,
    PaperIdentifier,
    ReferenceDetail,
    ResearchConfig,
    ResearchSession,
    AnalyzedPaper,
    # Legacy models still used by old routes
    CrawlStatus,
    CrawlStatusProgress,
    CrawlStatusFrontier,
    PaperInBatch,
    EnrichedPaper,
)
from app.services.crawler.sources.arxiv_source import ArxivSource
from app.services.crawler.sources.semantic_scholar_source import SemanticScholarSource
from app.core.rate_limiter import rate_limiter
from app.agents.query_agent import QueryAgent
from app.agents.analysis_agent import AnalysisAgent


def _clean_arxiv_id(paper_id: str) -> str:
    """Strip version suffix from arXiv IDs (e.g. 2304.15010v1 → 2304.15010)."""
    return re.sub(r"v\d+$", "", paper_id)


def _paper_key(meta: PaperMetadata) -> str:
    """Stable key for deduplication."""
    if meta.identifier.arxiv_id:
        return f"arxiv:{_clean_arxiv_id(meta.identifier.arxiv_id)}"
    if meta.identifier.doi:
        return f"doi:{meta.identifier.doi}"
    return f"hash:{meta.identifier.hash}"


def _metadata_to_ref_detail(meta: PaperMetadata) -> ReferenceDetail:
    return ReferenceDetail(
        paper_id=meta.identifier.arxiv_id
        or meta.identifier.doi
        or meta.identifier.hash,
        title=meta.title,
        authors=meta.authors,
        year=meta.publication_date.year if meta.publication_date.year > 1970 else None,
        venue=meta.venue,
        abstract=meta.abstract[:500] if meta.abstract else "",
        doi=meta.identifier.doi,
        arxiv_id=meta.identifier.arxiv_id,
        url=meta.url,
        source_api=meta.source_api,
    )


class ResearchCrawler:
    """Autonomous research pipeline with BFS citation trail following."""

    def __init__(self):
        self.arxiv = ArxivSource()
        self.s2 = SemanticScholarSource()
        self._google_scholar = None  # lazy
        self.query_agent = QueryAgent()
        self.analysis_agent = AnalysisAgent()
        self.sessions: Dict[str, ResearchSession] = {}
        # Store for analyzed papers across sessions
        self.paper_store: Dict[str, AnalyzedPaper] = {}

    def _get_google_scholar(self):
        if self._google_scholar is None:
            try:
                from app.services.crawler.sources.google_scholar_source import (
                    GoogleScholarSource,
                )

                self._google_scholar = GoogleScholarSource()
            except Exception as e:
                logger.warning(f"Google Scholar unavailable: {e}")
        return self._google_scholar

    def _log(self, session: ResearchSession, msg: str):
        """Append to session progress log and logger."""
        session.progress_log.append(f"[{datetime.utcnow().isoformat()}] {msg}")
        logger.info(f"[{session.session_id}] {msg}")

    # ─────────────────────────────────────────
    # Main pipeline
    # ─────────────────────────────────────────

    async def run_research(self, config: ResearchConfig) -> str:
        """Start a full research session and return the session ID.

        This launches the pipeline as a background task.
        """
        session_id = f"research_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        session = ResearchSession(
            session_id=session_id,
            config=config,
            status="starting",
        )
        self.sessions[session_id] = session
        asyncio.create_task(self._pipeline(session))
        return session_id

    async def _pipeline(self, session: ResearchSession):
        """The full autonomous research pipeline."""
        config = session.config
        start_time = time.monotonic()

        try:
            # ── Step 1: Refine query ─────────────────────
            session.status = "refining_query"
            self._log(session, f"Step 1: Refining query: '{config.query}'")

            refined = await self.query_agent.refine_query(config.query)
            session.refined_query = refined
            search_queries = refined.get("refined_queries", [config.query])
            self._log(session, f"Refined into {len(search_queries)} search queries")

            # ── Step 2: Multi-source search ──────────────
            session.status = "searching"
            self._log(session, "Step 2: Searching across sources")

            # Reserve BFS budget for deeper levels — seed search gets a fraction
            seed_limit = max(3, config.max_papers // (config.max_depth + 1))
            self._log(
                session,
                f"  Seed limit: {seed_limit} papers (reserving budget for depth {config.max_depth})",
            )

            seed_papers: Dict[str, PaperMetadata] = {}
            for query in search_queries[:3]:  # use top 3 refined queries
                await self._search_sources(
                    query, config.sources, seed_papers, seed_limit
                )
                # Check time limit
                if (
                    time.monotonic() - start_time
                    > config.stop_conditions.max_time_seconds
                ):
                    self._log(session, "Time limit reached during search")
                    break

            # Cap seeds to seed_limit (search may return more across queries)
            if len(seed_papers) > seed_limit:
                seed_list = list(seed_papers.items())[:seed_limit]
                seed_papers = dict(seed_list)

            session.papers_discovered = len(seed_papers)
            self._log(
                session,
                f"Found {len(seed_papers)} unique seed papers (capped to {seed_limit})",
            )

            # ── Step 3: BFS citation trail following ─────
            session.status = "crawling"
            self._log(
                session,
                f"Step 3: Following citation trails (max_depth={config.max_depth})",
            )

            # BFS budget = total max papers (seeds + deeper levels)
            bfs_budget = config.stop_conditions.max_papers
            self._log(session, f"  BFS budget: {bfs_budget} total papers")

            all_papers = await self._bfs_citation_trail(
                session=session,
                seed_papers=list(seed_papers.values()),
                max_depth=config.max_depth,
                max_papers=bfs_budget,
                start_time=start_time,
                time_limit=config.stop_conditions.max_time_seconds,
            )
            session.papers_discovered = len(all_papers)
            self._log(session, f"Total papers after BFS: {len(all_papers)}")

            # Store ALL discovered papers in session for the graph
            session.analyzed_papers = list(all_papers.values())
            for p in session.analyzed_papers:
                self.paper_store[p.paper_id] = p

            # ── Step 4: Analyze top papers with LLM ──────
            session.status = "analyzing"
            # Sort by citation count (proxy for importance) and take top N
            papers_sorted = sorted(
                session.analyzed_papers,
                key=lambda p: p.citation_count,
                reverse=True,
            )
            top_papers = papers_sorted[: config.top_papers_to_analyze]
            self._log(
                session, f"Step 4: Analyzing top {len(top_papers)} papers with LLM"
            )

            for i, paper in enumerate(top_papers):
                if (
                    time.monotonic() - start_time
                    > config.stop_conditions.max_time_seconds
                ):
                    self._log(session, "Time limit reached during analysis")
                    break

                self._log(
                    session,
                    f"  Analyzing [{i + 1}/{len(top_papers)}]: {paper.metadata.title[:60]}",
                )

                if config.analyze_with_llm:
                    # Try to get paper text for LLM analysis
                    paper_text = await self._get_paper_text(paper)
                    if paper_text:
                        analysis = await self.analysis_agent.analyze_paper(
                            paper_text=paper_text,
                            paper_title=paper.metadata.title,
                            paper_id=paper.paper_id,
                        )
                        paper.analysis = analysis
                        paper.parsed = True

                session.papers_analyzed += 1

            # ── Step 5: Persist to Neo4j ─────────────────
            session.status = "storing_graph"
            self._log(session, "Step 5: Persisting knowledge graph to Neo4j")
            try:
                from app.services.graph.db.neo4j_impl import neo4j_db

                await neo4j_db.store_session_graph(
                    session.session_id, session.analyzed_papers
                )
                self._log(session, "Graph saved to Neo4j successfully")
            except Exception as e:
                self._log(session, f"Failed to save to Neo4j (is it running?): {e}")

            # ── Step 6: Synthesis Agent ──────────────────
            if config.analyze_with_llm:
                session.status = "synthesizing"
                self._log(
                    session,
                    "Step 6: Generating literature synthesis, contradictions, and gaps",
                )
                try:
                    from app.agents.synthesis_agent import SynthesisAgent

                    synthesis_agent = SynthesisAgent()
                    # Pass the analyzed papers to the synthesis agent (top parsed ones)
                    parsed_papers = [p for p in session.analyzed_papers if p.parsed]
                    if parsed_papers:
                        synthesis = await synthesis_agent.generate_synthesis(
                            config.query, parsed_papers
                        )
                        session.synthesis = synthesis
                        self._log(session, "Synthesis report generated successfully")
                    else:
                        self._log(session, "No parsed papers available for synthesis")
                except Exception as e:
                    self._log(session, f"Synthesis generation failed: {e}")

            # ── Done ─────────────────────────────────────
            session.status = "completed"
            elapsed = round(time.monotonic() - start_time, 1)
            self._log(
                session,
                f"Pipeline completed in {elapsed}s. "
                f"Discovered: {session.papers_discovered}, "
                f"Analyzed: {session.papers_analyzed}",
            )

        except Exception as e:
            session.status = "failed"
            session.errors.append(str(e))
            self._log(session, f"Pipeline failed: {e}")
            logger.exception(f"Research pipeline failed: {e}")

    # ─────────────────────────────────────────
    # Multi-source search
    # ─────────────────────────────────────────

    async def _search_sources(
        self,
        query: str,
        sources: List[str],
        results: Dict[str, PaperMetadata],
        max_per_source: int = 10,
    ):
        """Search multiple sources, deduplicate into results dict."""

        if "arxiv" in sources:
            try:
                await rate_limiter.acquire("arxiv")
                arxiv_papers = await self.arxiv.search(
                    query, max_results=max_per_source
                )
                for p in arxiv_papers:
                    key = _paper_key(p)
                    if key not in results:
                        results[key] = p
            except Exception as e:
                logger.warning(f"arXiv search failed: {e}")

        if "semantic_scholar" in sources:
            try:
                await rate_limiter.acquire("semantic_scholar")
                s2_papers = await self.s2.search(query, max_results=max_per_source)
                for p in s2_papers:
                    key = _paper_key(p)
                    if key not in results:
                        results[key] = p
            except Exception as e:
                logger.warning(f"Semantic Scholar search failed: {e}")

        if "google_scholar" in sources:
            gs = self._get_google_scholar()
            if gs:
                try:
                    gs_papers = await gs.search(
                        query, max_results=min(max_per_source, 5)
                    )
                    for p in gs_papers:
                        key = _paper_key(p)
                        if key not in results:
                            results[key] = p
                except Exception as e:
                    logger.warning(f"Google Scholar search failed: {e}")

    # ─────────────────────────────────────────
    # BFS Citation Trail
    # ─────────────────────────────────────────

    async def _bfs_citation_trail(
        self,
        session: ResearchSession,
        seed_papers: List[PaperMetadata],
        max_depth: int,
        max_papers: int,
        start_time: float,
        time_limit: float,
    ) -> Dict[str, AnalyzedPaper]:
        """Breadth-first search on citation graph.

        Level 0: seed papers from search
        Level 1: references of seed papers
        Level N: references of level N-1 papers
        Stops at max_depth OR max_papers OR time limit
        """
        all_papers: Dict[str, AnalyzedPaper] = {}
        visited: Set[str] = set()
        queue: deque = deque()  # (PaperMetadata, depth)

        # Enqueue seed papers at depth 0
        for paper in seed_papers:
            key = _paper_key(paper)
            if key not in visited:
                visited.add(key)
                queue.append((paper, 0))

        self._log(
            session,
            f"BFS: {len(queue)} seed papers queued, budget={max_papers}, max_depth={max_depth}",
        )

        while queue and len(all_papers) < max_papers:
            if time.monotonic() - start_time > time_limit:
                self._log(session, "BFS: time limit reached")
                break

            paper, depth = queue.popleft()

            # Skip if beyond max depth (shouldn't happen, but safety check)
            if depth > max_depth:
                continue

            session.current_depth = max(session.current_depth, depth)
            paper_id = (
                paper.identifier.arxiv_id
                or paper.identifier.doi
                or paper.identifier.hash
            )

            self._log(
                session,
                f"BFS depth={depth}: processing '{paper.title[:50]}' ({paper_id})",
            )

            # Fetch references for this paper via S2
            references: List[ReferenceDetail] = []
            citations: List[ReferenceDetail] = []

            s2_id = self._resolve_s2_id(paper)
            if s2_id:
                try:
                    await rate_limiter.acquire("semantic_scholar")
                    ref_papers = await self.s2.fetch_references(s2_id, limit=30)
                    references = [_metadata_to_ref_detail(r) for r in ref_papers]
                except Exception as e:
                    logger.warning(f"S2 references failed for {paper_id}: {e}")

                try:
                    await rate_limiter.acquire("semantic_scholar")
                    cite_papers = await self.s2.fetch_citations(s2_id, limit=30)
                    citations = [_metadata_to_ref_detail(c) for c in cite_papers]
                except Exception as e:
                    logger.warning(f"S2 citations failed for {paper_id}: {e}")

            # Store this paper
            analyzed = AnalyzedPaper(
                paper_id=paper_id,
                metadata=paper,
                references=references,
                reference_count=len(references),
                citations=citations,
                citation_count=len(citations),
                crawl_depth=depth,
                source=paper.source_api,
            )
            key = _paper_key(paper)
            all_papers[key] = analyzed

            # Enqueue references at next depth
            next_depth = depth + 1
            if next_depth <= max_depth:
                enqueued = 0
                # Limit how many refs per paper we follow to avoid explosion
                refs_to_follow = references[:10]
                for ref in refs_to_follow:
                    # Only stop enqueuing if we've already PROCESSED enough
                    # (allow queue to grow beyond max_papers — the while loop gates processing)
                    if len(all_papers) >= max_papers:
                        break
                    # Build a PaperMetadata for the reference to enqueue
                    ref_key = (
                        f"arxiv:{_clean_arxiv_id(ref.arxiv_id)}"
                        if ref.arxiv_id
                        else f"hash:{ref.paper_id}"
                    )
                    if ref_key not in visited:
                        visited.add(ref_key)
                        ref_meta = PaperMetadata(
                            identifier=PaperIdentifier(
                                doi=ref.doi,
                                arxiv_id=ref.arxiv_id,
                                title=ref.title,
                                authors=ref.authors,
                                hash=ref.paper_id,
                            ),
                            title=ref.title,
                            authors=ref.authors,
                            publication_date=datetime(ref.year, 1, 1)
                            if ref.year and ref.year > 1900
                            else datetime(1970, 1, 1),
                            venue=ref.venue,
                            abstract=ref.abstract,
                            url=ref.url,
                            source_api=ref.source_api or "semantic_scholar",
                        )
                        queue.append((ref_meta, next_depth))
                        enqueued += 1

                if enqueued > 0:
                    self._log(
                        session,
                        f"  → Enqueued {enqueued} references for depth {next_depth} (queue size: {len(queue)})",
                    )

        self._log(
            session,
            f"BFS complete: {len(all_papers)} papers across depths 0-{session.current_depth}",
        )
        return all_papers

    def _resolve_s2_id(self, paper: PaperMetadata) -> Optional[str]:
        if paper.identifier.arxiv_id:
            clean = _clean_arxiv_id(paper.identifier.arxiv_id)
            return f"ArXiv:{clean}"
        if paper.identifier.doi:
            return f"DOI:{paper.identifier.doi}"
        return None

    # ─────────────────────────────────────────
    # Paper text extraction
    # ─────────────────────────────────────────

    async def _get_paper_text(self, paper: AnalyzedPaper) -> Optional[str]:
        """Try to download and extract text from a paper's PDF."""
        if not paper.metadata.pdf_url:
            # Return abstract as fallback
            return paper.metadata.abstract or None

        try:
            data_dir = "./data/papers"
            await rate_limiter.acquire("arxiv")
            pdf_path = await self.arxiv.download_pdf(
                paper.metadata.pdf_url, paper.paper_id, data_dir
            )
            paper.pdf_path = pdf_path

            # Use the text extractor
            from app.services.parser.extractors.text_extractor import TextExtractor

            extractor = TextExtractor()
            text_results = await extractor.extract_text(pdf_path)
            return text_results.get("best", "")
        except Exception as e:
            logger.warning(f"Could not extract text for {paper.paper_id}: {e}")
            return paper.metadata.abstract or None

    # ─────────────────────────────────────────
    # Session management
    # ─────────────────────────────────────────

    async def get_session(self, session_id: str) -> Optional[ResearchSession]:
        return self.sessions.get(session_id)

    async def stop_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session and session.status not in ("completed", "failed", "stopped"):
            session.status = "stopped"
            self._log(session, "Session stopped by user")
            return True
        return False

    async def list_sessions(self) -> List[str]:
        return list(self.sessions.keys())


# ──────────────────────────────────────────────
# Keep legacy PaperCrawler for backward compat
# ──────────────────────────────────────────────


class PaperCrawler:
    """Legacy crawler — kept for old /crawl/ routes."""

    def __init__(self):
        self.sources = {"arxiv": ArxivSource()}
        self.sessions: Dict[str, CrawlStatus] = {}
        self._crawled_hashes: Set[str] = set()
        self.s2 = SemanticScholarSource()
        self.paper_store: Dict[str, EnrichedPaper] = {}

    def _paper_id(self, paper: PaperMetadata) -> str:
        return (
            paper.identifier.arxiv_id or paper.identifier.doi or paper.identifier.hash
        )

    async def start_crawl(self, query: str, depth: int, max_papers: int) -> str:
        session_id = f"crawl_{datetime.utcnow().strftime('%Y_%m_%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.sessions[session_id] = CrawlStatus(
            session_id=session_id,
            status="starting",
            progress=CrawlStatusProgress(max_depth=depth),
            estimated_time_remaining_seconds=max_papers * 5,
        )
        asyncio.create_task(self._crawl_worker(session_id, query, depth, max_papers))
        return session_id

    async def _crawl_worker(
        self, session_id: str, query: str, max_depth: int, max_papers: int
    ):
        status = self.sessions[session_id]
        status.status = "in_progress"
        try:
            papers = await self.sources["arxiv"].search(query, max_results=max_papers)
            for paper in papers:
                if paper.identifier.hash in self._crawled_hashes:
                    continue
                self._crawled_hashes.add(paper.identifier.hash)
                status.progress.papers_found += 1
                pid = self._paper_id(paper)
                status.papers_in_current_batch.append(
                    PaperInBatch(
                        paper_id=pid, title=paper.title, status="completed", depth=0
                    )
                )
                status.progress.papers_processed += 1
                status.progress.percent_complete = min(
                    100.0, (status.progress.papers_processed / max_papers) * 100
                )
        except Exception as e:
            status.status = "failed"
            status.errors["error"] = 1
        else:
            status.status = "completed"

    async def get_crawl_status(self, session_id: str) -> Optional[CrawlStatus]:
        return self.sessions.get(session_id)

    async def pause_crawl(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id].status = "paused"

    async def resume_crawl(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id].status = "in_progress"

    async def get_frontier(self, session_id: str) -> List[PaperInBatch]:
        if session_id in self.sessions:
            return self.sessions[session_id].papers_in_current_batch
        return []

    async def get_enriched_paper(self, paper_id: str) -> Optional[EnrichedPaper]:
        return self.paper_store.get(paper_id)

    async def get_all_enriched_papers(self) -> List[EnrichedPaper]:
        return list(self.paper_store.values())
