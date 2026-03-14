# Agent Implementation Guide

## Overview

Each agent in the pipeline implements the `BaseAgent` interface and can be used independently or as part of the pipeline. This guide covers the architecture, implementation details, and customization options for each agent.

## Base Agent Architecture

All agents inherit from `BaseAgent`:

```python
class BaseAgent:
    def __init__(self, agent_name: str, llm_client=None)
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Main execution method - must be implemented by subclass."""
        raise NotImplementedError()
    
    def _log_step(self, message: str):
        """Log agent steps for debugging."""
    
    def _add_error(self, state: PipelineState, error: str) -> PipelineState:
        """Add error to pipeline state and log it."""
```

## Individual Agents

### QueryRefinementAgent

**Purpose:** Transform vague user queries into structured search parameters

**Input:**
- `state.raw_query`: User's natural language query

**Output:**
- `state.refined_query`: Dictionary with:
  - `refined_queries`: List of 3-5 specific search queries
  - `key_concepts`: Core technical terms
  - `date_range`: {start_year, end_year} or null
  - `target_venues`: Relevant conferences/journals
  - `exclusions`: Terms to exclude
  - `search_strategy`: Brief explanation

**Example:**
```
Input: "recent deep learning advances in medical imaging"

Output: {
  "refined_queries": [
    "deep learning medical imaging 2024",
    "CNN radiology analysis",
    "transformer vision medical applications",
    "foundation models healthcare imaging"
  ],
  "key_concepts": ["deep learning", "medical imaging", "CNN", "transformer"],
  "date_range": {"start_year": 2023, "end_year": null},
  "target_venues": ["MICCAI", "ISBI", "NeurIPS", "ICML"],
  "search_strategy": "Focus on recent deep learning methods for medical image analysis"
}
```

**Implementation Notes:**
- Uses LLM for intelligent query expansion
- Falls back to heuristic if LLM unavailable
- Structured JSON output for reliable parsing

---

### PaperFinderAgent

**Purpose:** Find papers from multiple academic sources

**Input:**
- `state.refined_query.refined_queries`: List of search queries

**Output:**
- `state.papers`: List of paper dictionaries with:
  - `id`: Unique identifier
  - `title`: Paper title
  - `authors`: List of authors
  - `year`: Publication year
  - `url`: Link to paper
  - `abstract`: Paper abstract
  - `source`: Source (arxiv, scholar, semantic_scholar)

**Example Paper:**
```python
{
  "id": "arxiv_2401.01234",
  "title": "Efficient Vision Transformers for Medical Imaging",
  "authors": ["John Doe", "Jane Smith"],
  "year": 2024,
  "url": "https://arxiv.org/abs/2401.01234",
  "abstract": "...",
  "source": "arxiv"
}
```

**Implementation Notes:**
- Searches multiple sources in parallel
- Deduplicates by title and year
- Respects rate limits per source
- Handles source-specific response formats

**Extensibility:**
Add new sources by implementing the source interface:
```python
class CustomSource(AbstractSource):
    async def search(self, query: str) -> List[Dict]:
        # Implementation
        pass
```

---

### CitationTrailAgent

**Purpose:** Build citation graph and follow citation trails

**Input:**
- `state.papers`: Root papers

**Output:**
- `state.citation_tree`: Dictionary with:
  - `root_papers`: Root paper data with citation trees
  - `citation_graph`: Complete graph structure
  - `depth_levels`: Papers organized by depth
  - `total_unique_papers`: Total count

**Citation Graph Structure:**
```python
{
  "paper_id": {
    "title": "Paper Title",
    "year": 2024,
    "authors": [...],
    "depth": 0,
    "cites": ["ref_paper_1", "ref_paper_2"],  # Papers this cites
    "cited_by": ["cite_paper_1", "cite_paper_2"]  # Papers citing this
  }
}
```

**Citation Tree Structure:**
```python
{
  "id": "paper_id",
  "title": "Paper Title",
  "depth": 0,
  "citations": [
    {
      "id": "ref_paper_1",
      "depth": 1,
      "citations": [...]  # Recursive
    }
  ],
  "cited_by": [...]
}
```

**Implementation Notes:**
- Recursive tree building with depth limit
- Avoids cycles (visited set)
- Configurable max depth (default: 3)
- Graph structure for relationship analysis

---

### ContentExtractorAgent

**Purpose:** Extract images, tables, diagrams from papers

**Input:**
- `state.papers`: Papers with full content

**Output:**
- `state.extracted_artifacts`: List of artifacts (images, tables, diagrams, equations)

**Artifact Structure:**
```python
{
  "type": "table|figure|diagram|equation",
  "paper_id": "paper_id",
  "paper_title": "Paper Title",
  "content": {...},  # Type-specific content
  "location": "page 5, section 3.2"
}
```

**Types of Extraction:**

**Tables:**
```python
{
  "type": "table",
  "title": "Results Comparison",
  "columns": ["Model", "Accuracy", "Speed"],
  "rows": [[...], [...]],
  "caption": "..."
}
```

**Figures:**
```python
{
  "type": "figure",
  "number": "Fig. 1",
  "caption": "Architecture diagram",
  "location": "page 3",
  "image_url": "..."  # if available
}
```

**Diagrams:**
```python
{
  "type": "diagram",
  "description": "Flowchart of process",
  "components": ["input", "process", "output"],
  "connections": [...]
}
```

**Equations:**
```python
{
  "type": "equation",
  "equation": "y = mx + b",
  "latex": "y = mx + b",
  "description": "Linear regression formula",
  "location": "page 2"
}
```

**Implementation Notes:**
- Uses vision LLM for image analysis
- Text pattern matching for structured data
- Falls back to LLM for complex extraction
- Stores artifacts in local directory

---

### PipelineAnalysisAgent

**Purpose:** Extract structured findings from papers

**Input:**
- `state.papers`: Papers with full content

**Output:**
- `state.analyses`: Dict mapping paper_id to analysis

**Analysis Structure:**
```python
{
  "research_question": "Main question the paper addresses",
  "methodology": "Approach/method used",
  "key_findings": [
    "Finding 1 with quantitative results",
    "Finding 2 with implications"
  ],
  "claims": [
    "Specific claim 1",
    "Specific claim 2"
  ],
  "datasets": ["Dataset 1", "Dataset 2"],
  "contributions": ["Novel contribution 1", "..."],
  "limitations": ["Limitation 1", "..."],
  "future_work": ["Suggested direction 1", "..."],
  "keywords": ["term1", "term2"],
  "contribution_type": "empirical|theoretical|survey|system|benchmark|dataset",
  "confidence_level": "high|medium|low",
  "summary": "2-3 sentence summary"
}
```

**Implementation Notes:**
- Truncates content to fit LLM context window
- Structured JSON output for downstream processing
- Confidence scores help filter low-quality extractions
- Can work offline with fallback heuristics

---

### SectionExtractorAgent

**Purpose:** Extract relevant sections for research topic

**Input:**
- `state.papers`: Original papers
- `state.analyses`: Paper analyses
- `state.raw_query`: Original research query

**Output:**
- `state.sectioned_content`: Dict mapping paper_id to sections

**Section Structure:**
```python
{
  "paper_id": {
    "title": "Paper Title",
    "source_url": "...",
    "sections": {
      "abstract": "...",
      "introduction": "...",
      "methodology": "...",
      "results": "...",
      "discussion": "...",
      "related_work": "...",
      "conclusion": "...",
      "key_quotes": ["quote1", "quote2"],
      "relevance_score": 0.85
    },
    "key_findings_summary": [...]
  }
}
```

**Implementation Notes:**
- LLM-guided section extraction
- Fallback keyword-based extraction
- Topic-aware relevance scoring
- Respects original paper structure

---

### RelationshipAnalysisAgent

**Purpose:** Analyze relationships between papers and features

**Input:**
- `state.papers`: All analyzed papers
- `state.citation_tree`: Citation relationships
- `state.analyses`: Paper findings

**Output:**
- `state.relationships`: Relationship analysis

**Relationship Analysis Structure:**
```python
{
  "feature_relationships": [
    {
      "feature1": "attention mechanisms",
      "feature2": "transformer efficiency",
      "relationship_type": "extends|builds_on|contradicts|complements",
      "strength": 0.85,
      "papers_involved": ["paper_1", "paper_2"],
      "description": "How feature2 extends feature1"
    }
  ],
  "citation_hierarchy": {
    "foundational_papers": ["paper_1", "paper_2"],
    "derivative_papers": ["paper_3", "paper_4"],
    "cluster_analysis": {
      "cluster_name": ["papers"]
    }
  },
  "research_progression": "Narrative of field evolution",
  "key_connections": ["connection1", "connection2"],
  "parent_child_relationships": {
    # From citation tree
  }
}
```

**Implementation Notes:**
- Multi-dimensional relationship analysis
- Citation strength computed from cite counts
- Cluster detection for paper grouping
- Research progression narrative generation

---

### GraphBuilderAgent

**Purpose:** Construct knowledge graph

**Input:**
- All previous pipeline outputs (papers, analyses, relationships, etc.)

**Output:**
- `state.graph_nodes`: Graph nodes and edges

**Graph Structure:**
```python
{
  "nodes": [
    {
      "id": "paper_123",
      "type": "Paper",
      "properties": {
        "title": "...",
        "authors": [...],
        "year": 2024,
        "key_findings": [...]
      }
    },
    {
      "id": "finding_456",
      "type": "Finding",
      "properties": {
        "text": "Key finding text",
        "source_paper": "paper_123"
      }
    },
    # ... more nodes
  ],
  "edges": [
    {
      "source": "paper_123",
      "target": "finding_456",
      "relationship": "HAS_FINDING",
      "properties": {}
    },
    # ... more edges
  ],
  "total_nodes": 250,
  "total_edges": 650
}
```

**Node Types:**
- **Paper**: Full paper metadata
- **Finding**: Key research findings
- **Concept**: Technical concepts/topics
- **CitedPaper**: External citations

**Edge Types:**
- **HAS_FINDING**: Paper → Finding
- **DISCUSSES**: Paper → Concept
- **CITES**: Paper → Paper
- **CITED_BY**: Paper → Paper
- **RELATED**: Concept → Concept

**Implementation Notes:**
- Creates comprehensive knowledge graph
- Can persist to Neo4j or Postgres
- Edge weights represent relationship strength
- Supports complex queries on graph

---

## Agent Lifecycle

Each agent follows this execution pattern:

1. **Initialization**
   - Create agent instance
   - Initialize LLM client
   - Set up logging

2. **Execution Context**
   - Receive PipelineState
   - Log agent start
   - Perform main task
   - Handle errors gracefully
   - Update state
   - Log completion

3. **State Management**
   - Read required fields from state
   - Validate input data
   - Compute/process
   - Update output fields
   - Maintain backward compatibility

4. **Error Handling**
   - Catch specific exceptions
   - Log with context
   - Add to state.errors
   - Continue or fail gracefully
   - Return updated state

## Creating Custom Agents

### Template

```python
from backend.agents.orchestrator import BaseAgent, PipelineState
from loguru import logger

class CustomAgent(BaseAgent):
    """Description of what agent does."""
    
    def __init__(self, llm_client=None, config=None):
        super().__init__("CustomAgent", llm_client)
        self.config = config or {}
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Execute custom logic."""
        
        self._log_step("Starting custom processing")
        
        try:
            # Your logic here
            result = await self._process_data(state)
            
            # Update state
            state.custom_field = result
            
            self._log_step("Custom processing complete")
            
        except Exception as e:
            logger.exception(f"Error in CustomAgent: {e}")
            return self._add_error(state, f"Custom processing failed: {str(e)}")
        
        return state
    
    async def _process_data(self, state: PipelineState):
        """Helper method for processing."""
        # Implementation
        pass
```

### Integration into Pipeline

```python
from backend.agents.pipeline_setup import create_pipeline_with_agents

# Add custom agent to your pipeline
agents = [
    "QueryRefinementAgent",
    "PaperFinderAgent",
    "CustomAgent",  # Your custom agent
    "PipelineAnalysisAgent"
]

pipeline = create_pipeline_with_agents(agents)
state = await pipeline.execute(query, user_id, session_id)
```

## Agent Configuration

Agents can accept configuration dictionaries:

```python
agent_config = {
    "max_depth": 5,
    "min_confidence": 0.7,
    "timeout": 30
}

agent = CustomAgent(config=agent_config)
```

## Debugging Agents

### Enable Verbose Logging

Agents automatically log detailed execution steps:
```
[QueryRefinementAgent] Refining query: 'attention mechanisms'
[QueryRefinementAgent] Refined into 4 search queries
[PaperFinderAgent] Searching: 'attention mechanisms 2024'
[PaperFinderAgent] Found 42 papers
```

### Inspect State

Access pipeline state for debugging:
```python
state = storage_manager.get_state_by_session(session_id)
print(json.dumps(state.to_dict(), indent=2))
```

### Test Individual Agents

```python
import asyncio
from backend.agents import QueryRefinementAgent
from backend.agents.orchestrator import PipelineState

async def test():
    state = PipelineState(
        raw_query="test query",
        user_id="test",
        session_id="test-session"
    )
    
    agent = QueryRefinementAgent()
    result = await agent.execute(state)
    print(result.refined_query)

asyncio.run(test())
```

## Performance Tips

1. **LLM Selection**
   - Smaller models: Faster, lower accuracy
   - Larger models: Slower, higher accuracy
   - Use appropriate model for each agent

2. **Parallel Processing**
   - Some agents can be parallelized (future enhancement)
   - Content extraction from multiple papers
   - Analysis on different papers simultaneously

3. **Caching**
   - Cache LLM responses for identical inputs
   - Store intermediate results locally
   - Reuse parsed papers

4. **Resource Management**
   - Monitor memory usage during execution
   - Limit citation tree depth
   - Batch process large paper collections

## Best Practices

1. **Error Handling**
   - Always return updated state
   - Add meaningful error messages
   - Continue processing when possible

2. **Logging**
   - Log key decision points
   - Use _log_step for major steps
   - Include context in error logs

3. **Data Validation**
   - Validate input state fields
   - Check for required data
   - Use sensible defaults

4. **Testing**
   - Test with mock data
   - Verify output structure
   - Check error handling

5. **Documentation**
   - Document expected inputs/outputs
   - Explain configuration options
   - Provide usage examples
