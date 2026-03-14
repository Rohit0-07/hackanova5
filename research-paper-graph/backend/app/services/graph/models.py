from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.crawler.models import PaperIdentifier


class GraphNode(BaseModel):
    """Paper node in citation graph"""

    node_id: str  # Unique ID (e.g., "paper_arxiv_2106.03762")
    paper_identifier: PaperIdentifier

    # Metadata
    title: str
    authors: List[str] = []
    publication_date: datetime
    venue: str = ""
    abstract: str = ""
    keywords: List[str] = []

    # Content references
    parsed_content_id: Optional[str] = None  # Link to PaperContent storage

    # Relationships
    outgoing_edges: List[str] = []  # IDs of papers this cites
    incoming_edges: List[str] = []  # IDs of papers citing this

    # Extracted analysis (for later phases)
    analysis_metadata: Dict[str, Any] = {}  # Extensible for future use

    # Audit
    created_at: datetime
    last_updated: datetime


class GraphEdge(BaseModel):
    """Citation relationship"""

    edge_id: str
    source_node_id: str  # Paper A
    target_node_id: str  # Paper B (cited by A)

    relationship_type: str  # "cites", "extends", "contradicts", etc.
    citation_context: str  # Quote showing how it was cited

    # Metadata
    is_bidirectional: bool = False  # If B also cites A
    strength: float  # 0-1 confidence in relationship


class GraphQuery(BaseModel):
    """Flexible query builder"""

    filters: Dict[str, Any] = {}  # {"author": "LeCun", "year_min": 2015}
    search_text: Optional[str] = None
    sort_by: str = "date"  # "date", "citations", "relevance"
    limit: int = 50


class GraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    avg_citations_per_paper: float
