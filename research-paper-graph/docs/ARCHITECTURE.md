# System Architecture Overview

## Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [Component Details](#component-details)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Scalability Considerations](#scalability-considerations)

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          FastAPI Server                          │
│                     (backend/main.py)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┬─────────────────────┐
        ↓                     ↓                     ↓
   ┌─────────┐         ┌─────────┐         ┌──────────────┐
   │ Crawler │         │ Parser  │         │ Multi-Agent  │
   │ Routes  │         │ Routes  │         │ Pipeline     │
   │         │         │         │         │ Routes       │
   └────┬────┘         └────┬────┘         └──────┬───────┘
        │                   │                     │
        └─────────────────────────────────────────┘
                        ↓
        ┌────────────────────────────────────┐
        │   Agent Orchestration Layer        │
        │  (backend/agents/orchestrator.py) │
        │                                    │
        │  • PipelineState Management        │
        │  • BaseAgent Interface             │
        │  • AgentPipeline Execution         │
        └────────────┬───────────────────────┘
                     ↓
        ┌────────────────────────────────────┐
        │     Pipeline Agents (Sequential)   │
        │  ┌──────────────────────────────┐  │
        │  │ 1. QueryRefinementAgent      │  │
        │  │ 2. PaperFinderAgent          │  │
        │  │ 3. CitationTrailAgent        │  │
        │  │ 4. ContentExtractorAgent     │  │
        │  │ 5. PipelineAnalysisAgent     │  │
        │  │ 6. SectionExtractorAgent     │  │
        │  │ 7. RelationshipAnalysisAgent │  │
        │  │ 8. GraphBuilderAgent         │  │
        │  └──────────────────────────────┘  │
        └────────────┬───────────────────────┘
                     ↓
        ┌────────────────────────────────────┐
        │   LLM Integration Layer            │
        │  (backend/parser/extractors/)      │
        │                                    │
        │  • OllamaClient                    │
        │  • GeminiClient                    │
        │  • LLM Response Processing         │
        └────────────┬───────────────────────┘
                     ↓
        ┌────────────────────────────────────┐
        │   External Services & Data         │
        │                                    │
        │  • Ollama (LLM)                    │
        │  • arXiv API                       │
        │  • Google Scholar                  │
        │  • Semantic Scholar                │
        │  • Neo4j (Graph DB)                │
        │  • PostgreSQL                      │
        └────────────────────────────────────┘
                     ↓
        ┌────────────────────────────────────┐
        │   Persistent Storage               │
        │  (backend/agents/storage_manager) │
        │                                    │
        │  • Pipeline State Files            │
        │  • Findings Reports                │
        │  • Knowledge Graphs                │
        │  • Temporary Artifacts             │
        └────────────────────────────────────┘
```

## Component Details

### 1. API Layer (FastAPI)
- **Location**: `backend/routes/`
- **Components**:
  - `pipeline.py` - Multi-agent pipeline endpoints
  - `crawler.py` - Paper crawling endpoints
  - `parser.py` - Document parsing
  - `chat.py` - Conversational interface
  - `research.py` - Research endpoints

### 2. Agent Orchestration
- **Location**: `backend/agents/`
- **Core Components**:
  - `orchestrator.py` - Base classes and pipeline engine
  - `pipeline_setup.py` - Pipeline factory and configuration
  - `storage_manager.py` - State persistence and retrieval

### 3. Individual Agents
- **Location**: `backend/agents/`
- **Agents**:
  1. `query_refinement_agent.py` - Query processing
  2. `paper_finder_agent.py` - Paper discovery
  3. `citation_trail_agent.py` - Citation graph building
  4. `content_extractor_agent.py` - Artifact extraction
  5. `pipeline_analysis_agent.py` - Paper analysis
  6. `section_extractor_agent.py` - Section organization
  7. `relationship_analysis_agent.py` - Relationship analysis
  8. `graph_builder_agent.py` - Knowledge graph construction

### 4. LLM Integration
- **Location**: `backend/parser/extractors/`
- **Components**:
  - `llm_extractor.py` - LLM client abstraction
  - Support for Ollama and Gemini
  - Vision model support for image analysis

### 5. Paper Collection
- **Location**: `backend/crawler/`
- **Sources**:
  - arXiv
  - Google Scholar
  - Semantic Scholar
- **Features**:
  - Rate limiting per source
  - Deduplication
  - Concurrent downloads

### 6. Storage Layer
- **Location**: `backend/agents/storage_manager.py`
- **Capabilities**:
  - State snapshots (JSON)
  - Report export (Markdown/JSON)
  - Graph serialization
  - Session management

## Data Flow

### Complete Query-to-Graph Flow

```
1. User Query Input
   │
   ├─→ QueryRefinementAgent
   │   Input: raw_query
   │   Output: refined_query (structured params)
   │
   ├─→ PaperFinderAgent
   │   Input: refined_query
   │   Output: papers (metadata list)
   │
   ├─→ CitationTrailAgent
   │   Input: papers
   │   Output: citation_tree (graph with depth)
   │
   ├─→ ContentExtractorAgent
   │   Input: papers
   │   Output: extracted_artifacts (images, tables, etc)
   │
   ├─→ PipelineAnalysisAgent
   │   Input: papers
   │   Output: analyses (findings, methodology, etc)
   │
   ├─→ SectionExtractorAgent
   │   Input: papers, analyses
   │   Output: sectioned_content (organized sections)
   │
   ├─→ RelationshipAnalysisAgent
   │   Input: papers, analyses, citation_tree
   │   Output: relationships (feature connections)
   │
   └─→ GraphBuilderAgent
       Input: all previous outputs
       Output: graph_nodes (nodes + edges)
```

### State Accumulation

```
Initial State:
{
  query: "user query",
  status: "initialized",
  errors: []
}
     ↓
After QueryRefi nementAgent:
{
  + refined_query: {...}
}
     ↓
After PaperFinderAgent:
{
  + papers: [{...}, ...]
}
     ↓
After CitationTrailAgent:
{
  + citation_tree: {...}
}
     ↓
... (each agent adds output) ...
     ↓
Final State:
{
  query, refined_query, papers, analyses,
  citation_tree, relationships, graph_nodes,
  extracted_artifacts, sectioned_content,
  status: "completed", errors: [...]
}
```

## Technology Stack

### Backend Framework
- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation and serialization
- **Uvicorn** - ASGI server

### LLM & AI
- **Ollama** - Local LLM engine
- **LLavA** - Vision model support
- **Qwen/Mistral** - Text models

### Data & Storage
- **Neo4j** - Knowledge graph database
- **PostgreSQL** - Relational data (optional)
- **JSON** - State serialization

### APIs & Services
- **arXiv API** - Academic papers
- **Google Scholar** - Research database
- **Semantic Scholar** - AI-powered indexing

### Libraries
- **loguru** - Logging
- **httpx** - Async HTTP
- **tenacity** - Retry logic
- **pdfplumber** - PDF processing
- **scholarly** - Google Scholar interface

## Scalability Considerations

### Current Architecture (Single Machine)
- Sequential agent execution
- Local LLM (no API rate limits)
- File-based state storage
- Suitable for: Research, small teams, educational use

### Scalability Improvements (Future)

**1. Parallel Agent Execution**
```python
# Execute independent agents in parallel
# e.g., ContentExtractor and Analyzer on different papers
```

**2. Distributed Pipeline**
```python
# Deploy agents as microservices
# Use message queue (RabbitMQ) for orchestration
# Scale horizontally by agent type
```

**3. Caching Layer**
```python
# Cache LLM responses
# Cache paper metadata
# Reduce redundant computations
```

**4. Database Optimization**
```python
# Move from file storage to database
# Add indexing for faster retrieval
# Enable concurrent state updates
```

**5. Load Balancing**
```python
# Multiple API instances behind load balancer
# Distributed state management
# Horizontal scaling
```

## Memory & Resource Usage

### Typical Requirements
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 10-100GB depending on usage
- **Bandwidth**: ~1GB per 100 papers
- **LLM Model**: 4-13GB GPU/CPU

### Optimization Tips
1. Use smaller LLM models for speed
2. Limit citation tree depth
3. Batch process papers
4. Regular storage cleanup
5. Monitor resource usage

## Security Considerations

### Current Implementation
- No authentication (local use assumed)
- CORS enabled for development
- No input validation beyond Pydantic
- File system access relatively open

### Production Hardening
- Add authentication/authorization
- Validate all API inputs
- Restrict CORS
- Add rate limiting
- Secure configuration management
- Input sanitization
- Error message filtering

## Integration Points

### External APIs
1. **Ollama** - LLM inference
2. **arXiv** - Paper access
3. **Google Scholar** - Research indexing
4. **Semantic Scholar** - Academic metadata
5. **Neo4j** - Graph queries
6. **Gemini** (optional) - Alternative LLM

### File System
- `./data/pipeline_storage/` - Persistent state
- `./logs/` - Execution logs
- `./data/papers/` - Downloaded papers
- `./data/artifacts/` - Extracted content

### Configuration
- `backend/config.yaml` - System configuration
- Environment variables - Deployment settings

## Monitoring & Observability

### Current Logging
- Agent execution steps
- Error tracking
- State transitions
- LLM interactions

### Future Enhancements
- Metrics collection (Prometheus)
- Distributed tracing (Jaeger)
- Performance profiling
- Usage analytics
- Real-time dashboard

## Deployment Architecture

### Development
```
Laptop/Workstation
├── Ollama (local)
├── FastAPI Server
└── PostgreSQL/SQLite
```

### Production
```
├── Load Balancer (nginx)
├── API Instances (multiple FastAPI)
├── Worker Pool (agents)
├── Message Queue (RabbitMQ)
├── State Store (Redis/PostgreSQL)
├── Graph DB (Neo4j)
├── File Storage (S3/NAS)
└── Monitoring (Prometheus/Grafana)
```

## Next Steps for Enhancement

1. **Parallel Execution** - Process independent tasks concurrently
2. **Incremental Processing** - Resume from checkpoints
3. **Result Caching** - Avoid redundant computations
4. **Interactive Refinement** - User feedback integration
5. **Advanced Visualization** - Graph and relationship visualization
6. **API v2** - Enhanced query capabilities
7. **Web UI** - User-friendly interface
8. **MLOps Integration** - Model versioning and management
