"""Pydantic models for the crawler module."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib


# ──────────────────────────────────────────────
# Core Identifiers
# ──────────────────────────────────────────────


class PaperIdentifier(BaseModel):
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pubmed_id: Optional[str] = None
    title: str
    authors: List[str] = []
    hash: str = ""


class PaperMetadata(BaseModel):
    """Raw metadata from any crawl source."""

    identifier: PaperIdentifier
    title: str
    authors: List[str]
    publication_date: datetime
    venue: str = ""
    abstract: str = ""
    reference_list: List[str] = []
    url: str = ""
    pdf_url: Optional[str] = None
    source_api: str = ""


# ──────────────────────────────────────────────
# Reference / Citation Detail
# ──────────────────────────────────────────────


class ReferenceDetail(BaseModel):
    """A single reference with full metadata for drill-down."""

    paper_id: str
    title: str
    authors: List[str] = []
    year: Optional[int] = None
    venue: str = ""
    abstract: str = ""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: str = ""
    source_api: str = ""


class CitationReference(BaseModel):
    source_paper_id: str
    cited_paper_title: str = ""
    cited_paper_authors: List[str] = []
    cited_paper_year: Optional[int] = None
    raw_text: str = ""


# ──────────────────────────────────────────────
# Research Session Config & Status
# ──────────────────────────────────────────────


class StopConditions(BaseModel):
    """Conditions under which the crawler should stop."""

    max_papers: int = 50
    max_depth: int = 3
    max_time_seconds: int = 600


class ResearchConfig(BaseModel):
    """Configuration for a full research session."""

    query: str
    max_depth: int = 2
    max_papers: int = 20
    top_papers_to_analyze: int = 10
    sources: List[str] = Field(default=["arxiv", "semantic_scholar"])
    stop_conditions: StopConditions = StopConditions()
    analyze_with_llm: bool = True


class AnalyzedPaper(BaseModel):
    """A paper that has been fully processed by the pipeline."""

    paper_id: str
    metadata: PaperMetadata
    references: List[ReferenceDetail] = []
    reference_count: int = 0
    citations: List[ReferenceDetail] = []
    citation_count: int = 0
    analysis: Dict[str, Any] = {}
    crawl_depth: int = 0
    source: str = ""
    pdf_path: Optional[str] = None
    parsed: bool = False


class ResearchSession(BaseModel):
    """Tracks the state of a full research pipeline run."""

    session_id: str
    status: str = "starting"  # starting, searching, crawling, analyzing, completed, stopped, failed
    config: ResearchConfig
    refined_query: Dict[str, Any] = {}
    papers_discovered: int = 0
    papers_analyzed: int = 0
    current_depth: int = 0
    progress_log: List[str] = []
    errors: List[str] = []
    analyzed_papers: List[AnalyzedPaper] = []
    synthesis: Dict[str, Any] = {}


# ──────────────────────────────────────────────
# Legacy models kept for backward compat
# ──────────────────────────────────────────────


class CrawlStatusProgress(BaseModel):
    papers_found: int = 0
    papers_processed: int = 0
    percent_complete: float = 0.0
    current_depth: int = 0
    max_depth: int = 1


class CrawlStatusFrontier(BaseModel):
    queued: int = 0
    active: int = 0


class PaperInBatch(BaseModel):
    paper_id: str
    title: str
    status: str = "queued"
    depth: int = 0


class CrawlStatus(BaseModel):
    session_id: str
    status: str = "starting"
    progress: CrawlStatusProgress = CrawlStatusProgress()
    frontier: CrawlStatusFrontier = CrawlStatusFrontier()
    errors: Dict[str, int] = {}
    estimated_time_remaining_seconds: int = 0
    papers_in_current_batch: List[PaperInBatch] = []


class FigureMetadata(BaseModel):
    figure_id: str
    caption: str = ""
    page_number: int = 0
    dimensions: tuple = (0, 0)


class Figure(BaseModel):
    figure_id: str
    image_bytes: bytes = b""
    metadata: FigureMetadata = FigureMetadata(figure_id="")


class Table(BaseModel):
    table_id: str
    content: str


class EnrichedPaper(BaseModel):
    """Legacy model — use AnalyzedPaper for new code."""

    identifier: PaperIdentifier
    title: str
    authors: List[str]
    publication_date: datetime
    venue: str = ""
    abstract: str = ""
    url: str = ""
    pdf_url: Optional[str] = None
    source_api: str = ""
    references: List[ReferenceDetail] = []
    reference_count: int = 0
    citations: List[ReferenceDetail] = []
    citation_count: int = 0
    crawl_depth: int = 0
