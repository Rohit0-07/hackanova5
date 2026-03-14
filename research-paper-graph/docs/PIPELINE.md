# Multi-Agent Research Analysis Pipeline

## Overview

This system implements a sophisticated multi-agent pipeline that autonomously analyzes research papers, follows citation trails, and constructs a knowledge graph. Each agent is specialized for a specific task and executes sequentially, passing state through the pipeline.

## Pipeline Architecture

```
User Query
    ↓
[1. QueryRefinementAgent] → Refine query into search parameters
    ↓
[2. PaperFinderAgent] → Find papers from multiple sources (arXiv, Scholar, Semantic Scholar)
    ↓
[3. CitationTrailAgent] → Build citation tree and graph (parent-child relationships)
    ↓
[4. ContentExtractorAgent] → Extract images, tables, diagrams, equations
    ↓
[5. PipelineAnalysisAgent] → Analyze papers for key findings, methodology, claims
    ↓
[6. SectionExtractorAgent] → Extract relevant sections for the research topic
    ↓
[7. RelationshipAnalysisAgent] → Analyze feature relationships and citations patterns
    ↓
[8. GraphBuilderAgent] → Construct knowledge graph (nodes and edges)
    ↓
Knowledge Graph + Findings Report
```

## Agent Descriptions

### 1. Query Refinement Agent
**Purpose:** Transform vague user queries into structured search parameters
- Input: Raw user query (e.g., "attention mechanisms in 2023")
- Output: Refined search queries, key concepts, date ranges, target venues
- LLM Task: Structuring and expanding user intent

### 2. Paper Finder Agent
**Purpose:** Find papers across multiple academic sources
- Input: Refined search queries
- Output: List of papers with metadata (title, authors, URL, abstract)
- Sources: arXiv, Google Scholar, Semantic Scholar
- Technique: Deduplication by title and year

### 3. Citation Trail Agent
**Purpose:** Build citation graph and follow citation trails
- Input: Found papers (root papers)
- Output: Citation tree with parent-child relationships
- Depth: Configurable (default: 3 levels)
- Graph: Complete citation network with depth analysis

### 4. Content Extractor Agent
**Purpose:** Extract structured content from papers
- Input: Paper PDFs/content
- Output: Images, tables, diagrams, equations, captions
- Types: Figures, tables, flowcharts, mathematical formulas
- Architecture: Uses vision LLMs and text analysis

### 5. Pipeline Analysis Agent
**Purpose:** Extract structured findings from papers
- Input: Paper full text
- Output: Research question, methodology, key findings, contributions, limitations
- Analysis Depth: Quantitative + qualitative findings
- Confidence: Extraction reliability scores

### 6. Section Extractor Agent
**Purpose:** Extract relevant sections for the research topic
- Input: Papers and their analyses
- Output: Organized sections (abstract, intro, methods, results, discussion)
- Relevance: Topic-specific section scoring
- Storage: Structured sections per paper

### 7. Relationship Analysis Agent
**Purpose:** Analyze relationships between papers and features
- Input: Citation tree + analyses + previous findings
- Output: Feature relationships, citation hierarchy, research progressions
- Analysis: 
  - Foundational vs derivative papers
  - Methodological connections
  - Contradictions and complementary work
  - Citation influence patterns

### 8. Graph Builder Agent
**Purpose:** Construct knowledge graph from all data
- Input: All previous pipeline outputs
- Output: Neo4j nodes and edges
- Node Types:
  - Paper nodes (with all metadata)
  - Finding nodes (key results)
  - Concept nodes (keywords/topics)
  - Citation nodes (with depth info)
- Edge Types:
  - HAS_FINDING (paper → finding)
  - DISCUSSES (paper → concept)
  - CITES/CITED_BY (paper → paper)
  - RELATED (concept → concept)

## API Endpoints

### Analysis Endpoints

```
POST /api/v1/pipeline/analyze
Start a complete multi-agent analysis pipeline
Request:
{
  "query": "attention mechanisms 2024",
  "user_id": "researcher_123",
  "max_papers": 20,
  "max_citation_depth": 3
}
Response:
{
  "session_id": "uuid-abc123",
  "status": "queued",
  "message": "Pipeline analysis has been queued..."
}
```

```
GET /api/v1/pipeline/status/{session_id}
Get pipeline execution status and results
Response:
{
  "session_id": "uuid-abc123",
  "status": "completed",
  "query": "attention mechanisms 2024",
  "papers_found": 15,
  "analyses_complete": 15,
  "graph_nodes": 120,
  "graph_edges": 340,
  "errors": []
}
```

```
GET /api/v1/pipeline/results/{session_id}
Get complete analysis results including all intermediate data
```

```
GET /api/v1/pipeline/report/{session_id}?format=markdown
Get formatted report (markdown or json)
```

### Session Management

```
GET /api/v1/pipeline/sessions
List all available analysis sessions

GET /api/v1/pipeline/storage/stats
Get storage statistics

POST /api/v1/pipeline/storage/cleanup?days=30
Clean up old stored states
```

## Pipeline State

The `PipelineState` object flows through the pipeline, accumulating data:

```python
{
    "raw_query": str,
    "session_id": str,
    "user_id": str,
    
    # Agent outputs
    "refined_query": {/* refined params */},
    "papers": [{/* paper data */}],
    "citation_tree": {/* citation graph */},
    "extracted_artifacts": [{/* images, tables, etc */}],
    "analyses": {/* paper_id -> findings */},
    "sectioned_content": {/* paper_id -> sections */},
    "relationships": {/* relationship analysis */},
    "graph_nodes": {/* knowledge graph */},
    
    # State management
    "status": "completed|in_progress|failed",
    "created_at": str,
    "updated_at": str,
    "errors": [str]
}
```

## Storage & Persistence

### Storage Structure
```
./data/pipeline_storage/
├── states/           # Pipeline state snapshots
├── findings/         # Extracted findings reports
└── graphs/           # Knowledge graph exports
```

### Storage Manager Features
- Automatic state serialization
- Session-based retrieval
- Markdown/JSON report export
- Cleanup utilities for old data
- Storage statistics

## Data Flow Example

### Input
```
User Query: "What are latest advances in protein folding with deep learning?"
```

### Query Refinement
```
Refined Queries: [
  "protein folding deep learning 2024",
  "AlphaFold improvements 2024",
  "protein structure prediction neural networks",
  ...
]
Key Concepts: ["protein folding", "AlphaFold", "deep learning", ...]
Target Venues: ["Nature", "Science", "NeurIPS", "ICML"]
Date Range: 2023-2024
```

### Paper Finding
```
Found Papers: [{
  "title": "AlphaFold3: Structure Prediction...",
  "authors": ["Jumper, J.", ...],
  "year": 2024,
  "url": "https://...",
  "abstract": "...",
  "source": "arxiv"
}]
```

### Citation Analysis
```
Citation Tree:
├── Root: AlphaFold3 Paper
│   ├── Cites: [AlphaFold v2, ...]
│   ├── Cited By: [DeepSeek, ...]
│   └── Depth: 0
└── Level 1 & 2: Referenced and citing papers
```

### Paper Analysis
```
Analysis: {
  "research_question": "How to improve structure prediction?",
  "methodology": "Transformer with diffusion...",
  "key_findings": [
    "Achieves X% accuracy on CASP",
    "Predicts complex interactions...",
    ...
  ],
  "contributions": [...],
  "limitations": [...]
}
```

### Relationships
```
Feature Relationships: [
  {
    "feature1": "attention mechanisms",
    "feature2": "AlphaFold3",
    "relationship": "extends",
    "papers": ["paper_123", "paper_456"]
  }
]
```

### Knowledge Graph
```
Nodes:
- Papers: 50+ nodes with metadata
- Findings: 150+ finding nodes
- Concepts: 80+ topic nodes
- Citations: All referenced papers

Edges:
- HAS_FINDING: Paper → Finding (150+)
- DISCUSSES: Paper → Concept (200+)
- CITES: Paper → Paper (300+)
- RELATED: Concept → Concept (100+)
```

## Configuration

Edit `backend/config.yaml`:

```yaml
llm:
  provider: "ollama"  # or "gemini"
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma3:latest"
    vision_model: "llava:latest"

crawler:
  default_depth: 2
  default_max_papers: 20
  download_dir: "./data/papers"

rate_limits:
  semantic_scholar: 1.2
  arxiv: 3.0
  google_scholar: 5.0
```

## Usage Examples

### Python Client

```python
from backend.agents.pipeline_setup import create_research_pipeline
import asyncio

async def analyze_papers():
    # Create pipeline
    pipeline = create_research_pipeline(llm_provider="ollama")
    
    # Execute
    state = await pipeline.execute(
        query="attention mechanisms 2024",
        user_id="researcher_1",
        session_id="session_abc123"
    )
    
    # Results
    print(f"Papers found: {len(state.papers)}")
    print(f"Graph nodes: {state.graph_nodes['total_nodes']}")
    print(f"Errors: {state.errors}")

asyncio.run(analyze_papers())
```

### cURL

```bash
# Start analysis
curl -X POST http://localhost:8000/api/v1/pipeline/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer architectures 2024",
    "user_id": "user123",
    "max_papers": 20
  }'

# Get status
curl http://localhost:8000/api/v1/pipeline/status/{session_id}

# Get results
curl http://localhost:8000/api/v1/pipeline/results/{session_id}

# Export report
curl http://localhost:8000/api/v1/pipeline/report/{session_id}?format=markdown
```

## Performance Considerations

- **Query Refinement**: ~2-5 seconds (LLM call)
- **Paper Finding**: ~10-30 seconds (per source)
- **Citation Trail**: ~15-60 seconds (depends on depth)
- **Content Extraction**: ~20-120 seconds (per paper)
- **Analysis**: ~10-30 seconds (per paper)
- **Section Extraction**: ~10-25 seconds (per paper)
- **Relationship Analysis**: ~20-60 seconds (depends on paper count)
- **Graph Building**: ~5-15 seconds

**Total for 20 papers**: ~5-15 minutes (with parallel optimizations possible in future)

## Extension & Customization

### Adding Custom Agents

```python
from backend.agents.orchestrator import BaseAgent, PipelineState

class CustomAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__("CustomAgent", llm_client)
    
    async def execute(self, state: PipelineState) -> PipelineState:
        # Your custom logic
        state.custom_field = "value"
        return state
```

### Custom Pipelines

```python
from backend.agents.pipeline_setup import create_pipeline_with_agents

pipeline = create_pipeline_with_agents([
    "QueryRefinementAgent",
    "PaperFinderAgent",
    "PipelineAnalysisAgent",
    "GraphBuilderAgent"  # Skip citation trail agent
])

state = await pipeline.execute(...)
```

## Monitoring & Debugging

Pipeline execution generates detailed logs:

```
[QueryRefinementAgent] Refining query: 'attention mechanisms'
[PaperFinderAgent] Searching: 'attention mechanisms 2024'
[CitationTrailAgent] Building citation tree for 15 root papers
...
```

Check `./logs/` directory for complete execution logs.

## Best Practices

1. **Query Formulation**: Be specific with queries for better results
2. **Session Management**: Save session IDs for later retrieval
3. **Resource Usage**: Monitor storage growth; use cleanup utilities
4. **Error Handling**: Check pipeline errors for debugging
5. **LLM Model Selection**: Use smaller models for speed, larger for accuracy

## Troubleshooting

### Pipeline Hangs
- Check LLM service availability (Ollama running?)
- Check rate limits with academic sources
- Monitor system resources

### Low Paper Counts
- Try different query formulations
- Reduce max citation depth
- Check source availability

### Memory Issues
- Reduce max citations depth
- Process fewer papers at a time
- Use cleanup utilities regularly

## Future Enhancements

- [ ] Parallel agent execution where possible
- [ ] Incremental pipeline execution
- [ ] Interactive result refinement
- [ ] Real-time progress tracking
- [ ] Advanced visualization
- [ ] Multi-agent voting/consensus on findings
