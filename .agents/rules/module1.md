---
trigger: always_on
---

# Research Paper Citation Graph System - MVP Backend Implementation Guide

## 🎯 **Executive Summary**
Build a modular, extensible backend system that crawls research papers, constructs a citation graph, and enables rich querying/filtering. The system must support dynamic paper downloads, image extraction, and provide detailed node-level analysis accessible via REST API.

## 📋 **Project Context**

**Problem Statement:**
- Users need to analyze research literature systematically.
- Current approach: Build a graph of research papers, extract findings, and answer complex queries.
- MVP Goal: Create the foundation for crawling, parsing, graphing, and querying papers with full inspection capabilities.

**Architecture Phases:**
- **Phase 0 (MVP):** Crawl → Parse → Graph → Query (foundational only)
- **Phase 1 (Next):** Add NLP-based contradiction/similarity detection
- **Phase 2 (Later):** Advanced synthesis, temporal analysis, recommendation engines

---

## 📦 **MODULAR SYSTEM DESIGN**

### **Module 1: Crawler (`crawler/`)**

**Purpose:** Fetch papers from APIs, follow citation trails, manage downloads and image extraction dynamically.

**Responsibilities:**
- Query research APIs (arXiv, Semantic Scholar, PubMed, CrossRef)
- Implement depth-limited breadth-first search on citation graph
- Download PDFs when available
- Track papers by unique identifiers (DOI, arXivId, SHA256 hash of title+authors)
- Handle duplicates and rate limiting
- Report progress in real-time

**Key Classes:**

```python
# core classes structure (pseudocode)

class PaperIdentifier:
    """Unique identification for papers"""
    doi: Optional[str]
    arxiv_id: Optional[str]
    pubmed_id: Optional[str]
    title: str
    authors: List[str]
    hash: str  # SHA256(title + authors + date)

class PaperMetadata:
    """Raw metadata from crawl"""
    identifier: PaperIdentifier
    title: str
    authors: List[str]
    publication_date: datetime
    venue: str
    abstract: str
    reference_list: List[str]  # Raw citation strings
    url: str
    pdf_url: Optional[str]
    source_api: str  # "arxiv" | "semantic_scholar" | etc.
    
class PaperCrawler:
    """Main crawler orchestrator"""
    async def start_crawl(query: str, depth: int, max_papers: int) -> CrawlSession
    async def get_crawl_status(session_id: str) -> CrawlStatus
    async def pause_crawl(session_id: str)
    async def resume_crawl(session_id: str)
    async def get_frontier(session_id: str) -> List[PaperMetadata]

class CitationTrailManager:
    """Manages citation extraction and follow-up"""
    async def extract_citations(paper_id: str) -> List[CitationReference]
    async def fetch_cited_papers(citations: List[CitationReference], depth: int)
    async def validate_citation_link(source_id: str, target_id: str) -> bool

class ImageExtractor:
    """Dynamic image extraction from PDFs"""
    async def extract_figures(pdf_path: str) -> List[Figure]
    async def extract_tables(pdf_path: str) -> List[Table]
    async def get_figure_metadata(figure_id: str) -> FigureMetadata
```

**Libraries:**
- `httpx` / `aiohttp` - async HTTP requests
- `arxiv` - arXiv API client
- `scholarly` - Google Scholar scraping
- `semantic-scholar-api` or direct REST calls
- `pdf2image` - PDF to image conversion
- `asyncio`, `concurrent.futures` - parallelization

**API Endpoints:**

```
POST   /api/v1/crawl/start
       Body: {query: str, depth: int, max_papers: int}
       Returns: {session_id, status, estimated_time}

GET    /api/v1/crawl/status/{session_id}
       Returns: {progress_pct, papers_found, current_depth, estimated_time}

GET    /api/v1/crawl/frontier/{session_id}
       Returns: List of papers in processing queue

PATCH  /api/v1/crawl/{session_id}/pause
PATCH  /api/v1/crawl/{session_id}/resume

GET    /api/v1/crawl/paper/{paper_id}/raw-metadata
       Returns: Raw metadata from crawl
```

**Status Tracking Response Example:**

```json
{
  "session_id": "crawl_2026_03_13_001",
  "status": "in_progress",
  "progress": {
    "papers_found": 127,
    "papers_processed": 85,
    "percent_complete": 66.9,
    "current_depth": 1,
    "max_depth": 2
  },
  "frontier": {
    "queued": 42,
    "active": 1
  },
  "errors": {
    "download_failed": 3,
    "api_timeout": 2
  },
  "estimated_time_remaining_seconds": 840,
  "papers_in_current_batch": [
    {
      "paper_id": "arxiv_2106.03762",
      "title": "Attention Is All You Need",
      "status": "queued",
      "depth": 1
    }
  ]
}
```
