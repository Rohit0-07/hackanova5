from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from pydantic import BaseModel
from app.services.crawler.models import PaperIdentifier, PaperMetadata


class SectionContent(BaseModel):
    """Extracted section from paper"""

    section_name: str  # "Introduction", "Methods", etc.
    content: str
    subsections: Dict[str, str] = {}
    confidence: float


class ExtractedFigure(BaseModel):
    """Figure extracted from PDF"""

    figure_id: str
    figure_number: int
    caption: str
    image_path: str  # Local or S3 path
    page_number: int
    dimensions: Tuple[int, int]
    format: str  # "png", "jpg"


class ExtractedTable(BaseModel):
    table_id: str
    table_number: int
    caption: str
    content: str
    page_number: int


class ParsedReference(BaseModel):
    """Normalized citation reference"""

    raw_text: str
    normalized_form: str
    authors: List[str] = []
    year: Optional[int] = None
    title: Optional[str] = None
    venue: Optional[str] = None
    potential_matches: List[PaperIdentifier] = []


class ExtractionAudit(BaseModel):
    """Audit log for how content was extracted"""

    extraction_time: datetime
    parser_version: str
    methods_used: List[str]  # ["pdfminer", "fitz", "pdfplumber"]
    confidence_scores: Dict[str, float]
    errors: List[str] = []
    warnings: List[str] = []


class PaperContent(BaseModel):
    """Fully parsed paper"""

    paper_id: str
    metadata: PaperMetadata
    sections: Dict[str, SectionContent] = {}
    abstract: str = ""
    introduction: str = ""
    methodology: str = ""
    results: str = ""
    conclusion: str = ""
    references: List[ParsedReference] = []
    figures: List[ExtractedFigure] = []
    tables: List[ExtractedTable] = []
    extraction_audit: ExtractionAudit
