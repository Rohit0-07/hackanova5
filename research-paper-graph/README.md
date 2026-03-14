# Research Paper Citation Graph & Multi-Agent Analysis Platform

An autonomous research analysis platform that crawls academic databases, builds citation networks, and constructs knowledge graphs using a sophisticated multi-agent system powered by local LLMs (Ollama).

## 🎯 Key Features

### Multi-Agent Pipeline
- **Query Refinement Agent** - Transforms user queries into structured search parameters
- **Paper Finder Agent** - Discovers papers from multiple academic sources (arXiv, Google Scholar, Semantic Scholar)
- **Citation Trail Agent** - Builds complete citation graphs with parent-child relationships
- **Content Extractor Agent** - Extracts images, tables, diagrams, and equations from papers
- **Analysis Agent** - Extracts structured findings, methodology, and contributions
- **Section Extractor Agent** - Organizes relevant sections by research topic
- **Relationship Analyzer Agent** - Identifies feature connections and methodological relationships
- **Graph Builder Agent** - Constructs knowledge graph with Neo4j export

### Advanced Capabilities
- 🔄 Citation trail following (configurable depth)
- 📊 Knowledge graph construction with Neo4j
- 🎨 Artifact extraction (figures, tables, equations)
- 🔍 Feature relationship analysis
- 📈 Research progression tracking
- 💾 Persistent state storage with markdown reports
- 🌐 RESTful API with FastAPI
- 📱 Async pipeline execution

### Local LLM Integration
- Powered by **Ollama** for privacy and offline capability
- Configurable model selection (default: Qwen, alternative: Llava for vision)
- No external API dependencies required

## 📋 Prerequisites

- Python 3.10+
- Ollama running locally (http://localhost:11434)
- Neo4j (optional, for advanced graph features)
- 8GB+ RAM recommended

## 🚀 Quick Start

### 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh

# Or download from https://ollama.ai
```

### 2. Pull Required Models

```bash
# Main LLM (for text analysis)
ollama pull gemma3:latest

# Or use other models
ollama pull mistral:latest
ollama pull llama2:latest

# Vision model (optional, for image extraction)
ollama pull llava:latest
```

### 3. Start Ollama

```bash
ollama serve
# Runs on http://localhost:11434
```

### 4. Install & Run Project

```bash
# Clone repository
git clone <repo-url>
cd research-paper-graph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy configuration
cp backend/config.example.yaml backend/config.yaml

# Edit config if needed
nano backend/config.yaml

# Run API server
python -m uvicorn backend.main:app --reload

# Access API docs
open http://localhost:8000/docs
```

## 📚 API Documentation

### Starting a Research Analysis

```bash
# POST /api/v1/pipeline/analyze
curl -X POST http://localhost:8000/api/v1/pipeline/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "recent advances in attention mechanisms",
    "user_id": "researcher_123",
    "max_papers": 20,
    "max_citation_depth": 3
  }'

# Response
{
  "session_id": "abc-123-def",
  "status": "queued",
  "message": "Pipeline analysis has been queued..."
}
```

### Checking Pipeline Status

```bash
# GET /api/v1/pipeline/status/{session_id}
curl http://localhost:8000/api/v1/pipeline/status/abc-123-def

# Response
{
  "session_id": "abc-123-def",
  "status": "completed",
  "query": "recent advances in attention mechanisms",
  "papers_found": 18,
  "analyses_complete": 18,
  "graph_nodes": 250,
  "graph_edges": 650,
  "errors": []
}
```

### Retrieving Results

```bash
# Get complete results
curl http://localhost:8000/api/v1/pipeline/results/abc-123-def

# Get markdown report
curl http://localhost:8000/api/v1/pipeline/report/abc-123-def?format=markdown

# Get JSON report
curl http://localhost:8000/api/v1/pipeline/report/abc-123-def?format=json
```

### Managing Sessions

```bash
# List all sessions
curl http://localhost:8000/api/v1/pipeline/sessions

# Get storage statistics
curl http://localhost:8000/api/v1/pipeline/storage/stats

# Cleanup old states (> 30 days)
curl -X POST http://localhost:8000/api/v1/pipeline/storage/cleanup?days=30
```

## 🏗️ Pipeline Architecture

```
User Query
    ↓
[1. Query Refinement] → Structured search parameters
    ↓
[2. Paper Finding] → Academic papers from multiple sources
    ↓
[3. Citation Trails] → Complete citation graph (parent-child)
    ↓
[4. Content Extraction] → Images, tables, diagrams, equations
    ↓
[5. Paper Analysis] → Key findings, methodology, contributions
    ↓
[6. Section Extraction] → Organized sections per topic
    ↓
[7. Relationship Analysis] → Feature connections & patterns
    ↓
[8. Graph Building] → Knowledge graph (nodes & edges)
    ↓
Knowledge Graph + Reports + Storage
```

## 📁 Project Structure

```
research-paper-graph/
├── backend/
│   ├── agents/              # Multi-agent pipeline system
│   │   ├── orchestrator.py              # Base classes & state management
│   │   ├── query_refinement_agent.py
│   │   ├── paper_finder_agent.py
│   │   ├── citation_trail_agent.py
│   │   ├── content_extractor_agent.py
│   │   ├── pipeline_analysis_agent.py
│   │   ├── section_extractor_agent.py
│   │   ├── relationship_analysis_agent.py
│   │   ├── graph_builder_agent.py
│   │   ├── pipeline_setup.py            # Pipeline factory & configuration
│   │   └── storage_manager.py           # Persistent state storage
│   │
│   ├── routes/
│   │   ├── pipeline.py      # Multi-agent pipeline endpoints
│   │   ├── crawler.py       # Paper crawling endpoints
│   │   ├── parser.py        # Document parsing endpoints
│   │   └── chat.py          # Chat/query endpoints
│   │
│   ├── crawler/             # Paper collection system
│   ├── parser/              # Document parsing
│   ├── graph/               # Knowledge graph
│   ├── utils/               # Utilities
│   ├── config.yaml          # Configuration
│   ├── requirements.txt     # Dependencies
│   └── main.py              # FastAPI application
│
├── data/
│   ├── pipeline_storage/    # Persistent state
│   ├── papers/              # Downloaded papers
│   ├── artifacts/           # Extracted content
│   └── graphs/              # Graph exports
│
├── docs/
│   ├── PIPELINE.md          # Complete pipeline documentation
│   ├── AGENT_GUIDE.md       # Individual agent details
│   └── API.md               # API reference
│
└── tests/                   # Test suite
```

## 🔧 Configuration

Edit `backend/config.yaml`:

```yaml
# LLM Configuration
llm:
  provider: "ollama"          # or "gemini" for Google Gemini
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma3:latest"         # Main analysis model
    vision_model: "llava:latest"  # For image extraction

# Crawler Configuration
crawler:
  download_dir: "./data/papers"
  max_concurrent_downloads: 3
  default_depth: 2
  default_max_papers: 20

# Rate Limits (requests per second)
rate_limits:
  semantic_scholar: 1.2
  arxiv: 3.0
  google_scholar: 5.0

# API Configuration
api:
  host: "0.0.0.0"
  port: 8000

# Database Configuration
database:
  backend: "neo4j"  # or "postgres"

neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "password"
```

## 📖 Documentation

- **[PIPELINE.md](docs/PIPELINE.md)** - Complete pipeline architecture and usage guide
- **[AGENT_GUIDE.md](docs/AGENT_GUIDE.md)** - Individual agent details and customization
- **[API.md](docs/API.md)** - Detailed API reference
- **[Setup Guide](docs/GUIDES/setup.md)** - Detailed installation instructions
- **[Deployment Guide](docs/GUIDES/deployment.md)** - Production deployment

## 💻 Python Client Usage

```python
import asyncio
from backend.agents.pipeline_setup import create_research_pipeline
from backend.agents.storage_manager import PipelineStorageManager

async def analyze():
    # Create pipeline
    pipeline = create_research_pipeline(llm_provider="ollama")
    storage = PipelineStorageManager()
    
    # Execute analysis
    state = await pipeline.execute(
        query="transformer architectures 2024",
        user_id="researcher_1",
        session_id="session_001"
    )
    
    # Access results
    print(f"Papers found: {len(state.papers)}")
    print(f"Graph nodes: {state.graph_nodes['total_nodes']}")
    print(f"Errors: {state.errors}")
    
    # Export report
    report = storage.export_findings_report("session_001", format="markdown")
    print(report)

asyncio.run(analyze())
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=backend tests/

# Run specific test file
pytest tests/test_analysis.py -v
```

## 📊 Performance

Typical execution times per step (for ~20 papers):
- Query Refinement: ~2-5 seconds
- Paper Finding: ~10-30 seconds
- Citation Trails: ~15-60 seconds
- Content Extraction: ~20-120 seconds
- Analysis: ~10-30 seconds per paper
- Section Extraction: ~10-25 seconds per paper
- Relationship Analysis: ~20-60 seconds
- Graph Building: ~5-15 seconds

**Total: ~5-15 minutes** (depending on paper complexity and model size)

## 🔄 Advanced Features

### Custom Agent Pipelines

```python
from backend.agents.pipeline_setup import create_pipeline_with_agents

# Create custom pipeline with selected agents
pipeline = create_pipeline_with_agents([
    "QueryRefinementAgent",
    "PaperFinderAgent",
    "PipelineAnalysisAgent",
    "GraphBuilderAgent"  # Skip citation trails
])

state = await pipeline.execute(query, user_id, session_id)
```

### Creating Custom Agents

```python
from backend.agents.orchestrator import BaseAgent, PipelineState

class MyCustomAgent(BaseAgent):
    async def execute(self, state: PipelineState) -> PipelineState:
        # Your custom logic
        self._log_step("Processing...")
        return state
```

### Storage Management

```python
from backend.agents.storage_manager import PipelineStorageManager

storage = PipelineStorageManager()

# List all sessions
sessions = storage.list_states()

# Get session results
state = storage.get_state_by_session("session_id")

# Export report
report = storage.export_findings_report("session_id", format="markdown")

# Cleanup old data
storage.cleanup_old_states(days=30)
```

## 🚨 Troubleshooting

### Ollama Not Responding
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### Model Not Found
```bash
# List available models
ollama list

# Pull required model
ollama pull gemma3:latest
```

### Low Paper Results
- Try reformulating queries
- Increase `max_papers` parameter
- Reduce citation depth
- Check academic source availability

### Memory Issues
- Reduce paper batch size
- Use smaller LLM model
- Limit citation tree depth
- Run cleanup utilities

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📜 License

MIT License - See LICENSE file for details

## 📧 Contact & Support

- Issues: GitHub Issues
- Documentation: See `/docs` directory
- API Playground: http://localhost:8000/docs

## 🗺️ Roadmap

- [ ] Parallel agent execution
- [ ] Interactive result refinement UI
- [ ] Real-time progress dashboard
- [ ] Advanced visualization
- [ ] Multi-agent consensus voting
- [ ] Incremental pipeline execution
- [ ] Web UI for query management
- [ ] Export to academic formats (BibTeX, RIS)

## 🙏 Acknowledgments

- Powered by [Ollama](https://ollama.ai) for local LLMs
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Graph database support via [Neo4j](https://neo4j.com/)
- Paper sources: arXiv, Google Scholar, Semantic Scholar
