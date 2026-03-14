---
trigger: always_on
---

### **Module 2: Parser (`parser/`)**

**Purpose:** Extract structured content from PDFs/metadata, prepare for graph storage.

**Responsibilities:**

- Parse PDF structure: extract sections, text, metadata
- Identify and extract figures, tables, and captions
- Parse reference section, normalize citation strings
- Extract key metadata fields with confidence scores
- Generate extraction audit logs

**Key Classes:**

```python
class SectionContent:
    """Extracted section from paper"""
    section_name: str  # "Introduction", "Methods", etc.
    content: str
    subsections: Dict[str, str]
    confidence: float

class ExtractedFigure:
    """Figure extracted from PDF"""
    figure_id: str
    figure_number: int
    caption: str
    image_path: str  # Local or S3 path
    page_number: int
    dimensions: Tuple[int, int]
    format: str  # "png", "jpg"

class PaperContent:
    """Fully parsed paper"""
    paper_id: str
    metadata: PaperMetadata

    sections: Dict[str, SectionContent]
    abstract: str
    introduction: str
    methodology: str
    results: str
    conclusion: str
    references: List[ParsedReference]

    figures: List[ExtractedFigure]
    tables: List[ExtractedTable]

    extraction_audit: ExtractionAudit

class ExtractionAudit:
    """Audit log for how content was extracted"""
    extraction_time: datetime
    parser_version: str
    methods_used: List[str]  # ["pdf_miner", "fitz", "pdfplumber"]
    confidence_scores: Dict[str, float]
    errors: List[str]
    warnings: List[str]

class PaperParser:
    """Main parser"""
    async def parse_paper(pdf_path: str) -> PaperContent
    async def extract_sections(pdf_content: bytes) -> Dict[str, str]
    async def extract_references(pdf_content: bytes) -> List[ParsedReference]
    async def extract_images(pdf_path: str) -> List[ExtractedFigure]

class ParsedReference:
    """Normalized citation reference"""
    raw_text: str
    normalized_form: str
    authors: List[str]
    year: Optional[int]
    title: Optional[str]
    venue: Optional[str]
    potential_matches: List[PaperIdentifier]  # Papers this might reference
```

**Libraries:**

- `pdfplumber` - PDF structure and table extraction
- `PyMuPDF` (fitz) - Fast PDF rendering and text
- `pdf2image` - Convert pages to images
- `pytesseract` / `paddleOCR` - OCR for scanned papers
- `pydantic` - Data validation
- `loguru` - Structured logging

**API Endpoints:**

```
POST   /api/v1/parser/parse-paper/{paper_id}
       Returns: {parse_status, section_count, figure_count, reference_count}

GET    /api/v1/parser/paper/{paper_id}/content
       Returns: Full PaperContent (sections, figures, metadata)

GET    /api/v1/parser/paper/{paper_id}/sections
       Query params: ?section_names=intro,methods
       Returns: Filtered sections

GET    /api/v1/parser/paper/{paper_id}/figures
       Returns: List of figures with thumbnails

GET    /api/v1/parser/paper/{paper_id}/references
       Returns: List of extracted references

GET    /api/v1/parser/paper/{paper_id}/audit
       Returns: Extraction audit log with confidence scores

POST   /api/v1/parser/batch-parse
       Body: {paper_ids: []}
       Returns: Batch parse job ID
```

**Example Response:**

```json
{
  "paper_id": "arxiv_2106.03762",
  "extraction_status": "success",
  "sections": {
    "introduction": {
      "section_name": "Introduction",
      "content": "The dominant sequence transduction models...",
      "confidence": 0.98,
      "subsections_found": 2
    },
    "methodology": {
      "section_name": "Methodology",
      "content": "...",
      "confidence": 0.95
    }
  },
  "references_extracted": 127,
  "figures_extracted": 15,
  "tables_extracted": 3,
  "audit": {
    "extraction_time_ms": 2300,
    "parser_version": "1.0.0",
    "methods_used": ["pdfplumber", "fitz", "pdf2image"],
    "confidence_scores": {
      "text_extraction": 0.97,
      "section_identification": 0.95,
      "reference_parsing": 0.92
    },
    "warnings": ["Figure 5 OCR confidence low: 0.72"]
  }
}
```

---