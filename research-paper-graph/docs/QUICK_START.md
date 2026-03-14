# Quick Start Guide - Multi-Agent Research Pipeline

## 5-Minute Setup

### Step 1: Install Ollama (2 minutes)

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai

### Step 2: Get Models (1 minute)

```bash
# Start Ollama
ollama serve

# In another terminal, pull models
ollama pull qwen2:7b      # Main model
ollama pull llava:latest  # Optional: for vision
```

### Step 3: Setup Project (2 minutes)

```bash
# Clone
git clone <repo-url>
cd research-paper-graph

# Virtual environment
python -m venv venv
source venv/bin/activate

# Install
pip install -r backend/requirements.txt

# Run
python -m uvicorn backend.main:app --reload
```

**Done!** API available at http://localhost:8000

## 🚀 First Analysis

### Using cURL

```bash
# 1. Start analysis
curl -X POST http://localhost:8000/api/v1/pipeline/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer models 2024",
    "max_papers": 10
  }'

# Response contains: session_id (save this!)
# {"session_id": "abc-123-def", "status": "queued"}

# 2. Check status (repeat until completed)
curl http://localhost:8000/api/v1/pipeline/status/abc-123-def

# 3. Get results
curl http://localhost:8000/api/v1/pipeline/results/abc-123-def

# 4. Get markdown report
curl http://localhost:8000/api/v1/pipeline/report/abc-123-def?format=markdown
```

### Using Python

```python
import asyncio
from backend.agents.pipeline_setup import create_research_pipeline
from backend.agents.storage_manager import PipelineStorageManager
import json

async def main():
    # Create pipeline
    pipeline = create_research_pipeline(llm_provider="ollama")
    storage = PipelineStorageManager()
    
    # Run analysis
    print("Starting analysis...")
    state = await pipeline.execute(
        query="attention mechanisms in transformers",
        user_id="demo_user",
        session_id="demo_001"
    )
    
    # Display results
    print(f"\n✅ Analysis Complete!")
    print(f"Papers found: {len(state.papers)}")
    print(f"Graph nodes: {state.graph_nodes['total_nodes'] if state.graph_nodes else 0}")
    print(f"Errors: {len(state.errors)}")
    
    # Export report
    report = storage.export_findings_report("demo_001", format="markdown")
    print("\n" + "="*50)
    print(report)

asyncio.run(main())
```

Save as `test_pipeline.py` and run:
```bash
python test_pipeline.py
```

## 📊 Understanding Results

### Full Results Structure
```python
{
  "papers": [
    {
      "title": "Paper Title",
      "authors": ["Author 1"],
      "year": 2024,
      "url": "...",
      "abstract": "..."
    }
  ],
  "analyses": {
    "paper_id": {
      "research_question": "...",
      "methodology": "...",
      "key_findings": ["Finding 1", "Finding 2"],
      "contributions": [...]
    }
  },
  "citation_tree": {
    "total_unique_papers": 45,
    "depth_levels": {...}
  },
  "relationships": {
    "feature_relationships": [...],
    "citation_hierarchy": {...}
  },
  "graph_nodes": {
    "nodes": [...],
    "edges": [...],
    "total_nodes": 250,
    "total_edges": 650
  }
}
```

## 🔧 Common Tasks

### Query Different Topics

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your research question here",
    "max_papers": 15,
    "max_citation_depth": 2
  }'
```

### View Storage

```python
from backend.agents.storage_manager import PipelineStorageManager

storage = PipelineStorageManager()

# List all sessions
sessions = storage.list_states()
for session in sessions:
    print(f"{session['session_id']}: {session['papers_found']} papers")

# Get statistics
stats = storage.get_storage_stats()
print(f"Total storage: {stats['total_sessions']} sessions, {stats['storage_size_mb']:.1f} MB")

# Cleanup old data
storage.cleanup_old_states(days=7)
```

### Custom Pipeline

```python
from backend.agents.pipeline_setup import create_pipeline_with_agents

# Run only specific agents
pipeline = create_pipeline_with_agents([
    "QueryRefinementAgent",
    "PaperFinderAgent",
    "PipelineAnalysisAgent"
])

state = await pipeline.execute(query, user_id, session_id)
```

## ⚙️ Configuration

Edit `backend/config.yaml` to customize:

```yaml
# Change main LLM model
llm:
  ollama:
    model: "mistral:latest"  # Faster
    # or
    model: "neural-chat:7b"  # More specific
    # or
    model: "llama2:13b"      # Larger

# Limit papers searched
crawler:
  default_max_papers: 10

# Speed up by reducing depth
# (in your query: "max_citation_depth": 1)
```

## 📈 Expected Performance

For **10 papers**:
- Total time: ~3-5 minutes
- Storage used: ~50-100 MB

For **20 papers**:
- Total time: ~8-12 minutes
- Storage used: ~150-250 MB

Time varies by:
- Model size (7B vs 13B)
- Query complexity
- Paper length
- System resources

## 🆘 Help & Debugging

### Check System Status

```bash
# API health
curl http://localhost:8000/api/v1/pipeline/health

# Ollama status
curl http://localhost:11434/api/tags

# View logs
tail -f ./logs/*.log
```

### Common Issues

**Issue: "Connection refused" on http://localhost:8000**
```bash
# Make sure API is running
python -m uvicorn backend.main:app --reload
```

**Issue: "Ollama not responding"**
```bash
# Start Ollama
ollama serve
```

**Issue: "Model not found"**
```bash
# Pull the model
ollama pull qwen2:7b
```

**Issue: Out of memory**
```bash
# Use smaller model
ollama pull mistral:latest  # Smaller than qwen2
# Update config.yaml with new model name
```

## 📚 Next Steps

1. **Read Full Docs**: Check [PIPELINE.md](/docs/PIPELINE.md)
2. **Explore API**: Visit http://localhost:8000/docs
3. **Create Custom Agents**: See [AGENT_GUIDE.md](/docs/AGENT_GUIDE.md)
4. **Deploy**: See [Deployment Guide](/docs/GUIDES/deployment.md)

## 💡 Tips

- **Start Small**: Begin with 5-10 papers to test
- **Good Queries**: Be specific ("attention mechanisms in vision transformers 2024" vs "AI")
- **Monitor Resources**: Check CPU/RAM during runs
- **Save Results**: Export to markdown for sharing
- **Parallel Development**: Use different session IDs for parallel research

## 🎯 Example Queries to Try

```
"recent advances in reinforcement learning"
"protein structure prediction with machine learning 2024"
"efficient transformers for edge devices"
"graph neural networks for molecular property prediction"
"federated learning in healthcare"
"large language model alignment and safety 2024"
```

## 🚀 Performance Tuning

### For Speed
```yaml
llm:
  ollama:
    model: "mistral:7b"  # Faster inference
crawler:
  default_max_papers: 5  # Fewer papers
```

### For Quality
```yaml
llm:
  ollama:
    model: "neural-chat:13b"  # Better analysis
crawler:
  default_max_papers: 30  # More papers
```

## 📞 Support

- **Stuck?** Check the troubleshooting section above
- **Questions?** Read the full documentation in `/docs`
- **Issues?** Open an issue on GitHub
- **Want to contribute?** See CONTRIBUTING.md

---

**Happy researching! 🔬🤖**
