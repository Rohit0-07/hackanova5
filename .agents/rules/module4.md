---
trigger: always_on
---

### **Module 4: Node Analysis & Findings (`analysis/`)**

**Purpose:** Track extraction methods, findings, and metadata per node for detailed inspection.

**Responsibilities:**

- Record extraction methodology and results per node
- Store structured findings (sections, images, metrics)
- Expose audit trails for transparency
- Enable deep inspection of paper analysis

**Key Classes:**

```python
class FindingItem:
    """Individual finding/piece of info"""
    key: str
    value: Any
    confidence: float
    extraction_method: str  # "pdf_miner", "heuristic", etc.
    source_section: str  # Where in paper this came from

class NodeFindings:
    """Comprehensive findings for a node"""
    node_id: str

    # Content findings
    content_findings: Dict[str, FindingItem]
    {
        "methodology": FindingItem(...),
        "results_summary": FindingItem(...),
        "datasets_used": FindingItem(...)
    }

    # Image findings
    images: List[ExtractedFigure]
    figure_count: int
    table_count: int

    # Citation findings
    reference_count: int
    top_cited_papers: List[str]

    # Metadata findings
    metadata_fields: Dict[str, Any]
    {
        "h_index_authors": 45,
        "citation_velocity": 150  # Citations per year
    }

    # Audit trail
    extraction_methods: List[ExtractionMethod]
    processing_log: List[ProcessingLogEntry]
    quality_score: float  # Overall quality

class ExtractionMethod:
    """Record of what method was used to extract data"""
    method_name: str
    tool_used: str
    start_time: datetime
    end_time: datetime
    success: bool
    result_count: int

class NodeInspector:
    """Main analysis inspector"""
    async def analyze_node(node_id: str) -> NodeFindings
    async def get_node_extraction_audit(node_id: str) -> List[ExtractionMethod]
    async def get_node_raw_content(node_id: str) -> RawContent
    async def compare_nodes(node_id_a: str, node_id_b: str) -> ComparisonResult
```

**Libraries:**

- `pydantic` - Data models
- `loguru` - Structured logging
- `json` - Serialization
- `dataclasses` - Clean data classes

**API Endpoints:**

```
GET    /api/v1/analysis/node/{node_id}
       Returns: Complete NodeFindings with all discoveries

GET    /api/v1/analysis/node/{node_id}/audit
       Returns: Extraction audit trail, methods used, timings

GET    /api/v1/analysis/node/{node_id}/raw
       Returns: Raw extracted data (unprocessed)

GET    /api/v1/analysis/node/{node_id}/images
       Returns: List of extracted images with metadata

GET    /api/v1/analysis/node/{node_id}/findings/{finding_key}
       Returns: Specific finding with details

POST   /api/v1/analysis/compare-nodes
       Body: {node_id_a, node_id_b}
       Returns: Comparative analysis
```

**Example Response:**

```json
{
  "node_id": "paper_arxiv_2106.03762",
  "findings": {
    "methodology": {
      "key": "methodology",
      "value": "Introduced multi-head attention mechanism...",
      "confidence": 0.96,
      "extraction_method": "section_extraction",
      "source_section": "Methodology"
    },
    "key_contributions": {
      "value": ["Multi-head attention", "Positional encoding"],
      "confidence": 0.94
    }
  },
  "images": {
    "count": 15,
    "figures": [
      {
        "figure_id": "fig_001",
        "caption": "Multi-Head Attention...",
        "image_url": "/api/v1/media/fig_001.png",
        "page_number": 3
      }
    ]
  },
  "citations": {
    "outgoing_count": 127,
    "incoming_count": 89420,
    "top_cited_by": ["Paper A", "Paper B"]
  },
  "extraction_audit": {
    "total_methods_used": 5,
    "methods": [
      {
        "method": "pdfplumber_extraction",
        "tool": "pdfplumber v0.9.0",
        "start_time": "2026-03-13T10:00:00Z",
        "end_time": "2026-03-13T10:00:02Z",
        "success": true,
        "result_count": 8
      }
    ],
    "processing_time_ms": 2300,
    "quality_score": 0.96
  }
}
```

---
