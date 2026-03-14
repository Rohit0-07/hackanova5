from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.services.parser.models import ExtractedFigure


class FindingItem(BaseModel):
    """Individual finding/piece of info"""

    key: str
    value: Any
    confidence: float
    extraction_method: str  # "pdf_miner", "heuristic", etc.
    source_section: str  # Where in paper this came from


class ExtractionMethod(BaseModel):
    """Record of what method was used to extract data"""

    method_name: str
    tool_used: str
    start_time: datetime
    end_time: datetime
    success: bool
    result_count: int


class ProcessingLogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str


class NodeFindings(BaseModel):
    """Comprehensive findings for a node"""

    node_id: str

    # Content findings
    content_findings: Dict[str, FindingItem] = {}

    # Image findings
    images: List[ExtractedFigure] = []
    figure_count: int = 0
    table_count: int = 0

    # Citation findings
    reference_count: int = 0
    top_cited_papers: List[str] = []

    # Metadata findings
    metadata_fields: Dict[str, Any] = {}

    # Audit trail
    extraction_methods: List[ExtractionMethod] = []
    processing_log: List[ProcessingLogEntry] = []
    quality_score: float = 0.0


class RawContent(BaseModel):
    node_id: str
    content: str
    raw_metadata: Dict[str, Any] = {}


class ComparisonResult(BaseModel):
    node_id_a: str
    node_id_b: str
    similarities: List[str] = []
    differences: List[str] = []
