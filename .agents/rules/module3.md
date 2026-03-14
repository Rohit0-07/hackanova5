---
trigger: always_on
---

### **Module 3: Graph Builder (`graph/`)**

**Purpose:** Store papers and citations in queryable graph structure. Support flexible filtering on any attribute.

**Responsibilities:**

- Model papers as nodes, citations as edges
- Store rich metadata per node and edge
- Provide queryable graph with multiple filtering options
- Support graph statistics and traversal
- Enable bidirectional citation relationships

**Key Classes:**

```python
class GraphNode:
    """Paper node in citation graph"""
    node_id: str  # Unique ID (e.g., "paper_arxiv_2106.03762")
    paper_identifier: PaperIdentifier

    # Metadata
    title: str
    authors: List[str]
    publication_date: datetime
    venue: str
    abstract: str
    keywords: List[str]

    # Content references
    parsed_content_id: str  # Link to PaperContent storage

    # Relationships
    outgoing_edges: List[str]  # IDs of papers this cites
    incoming_edges: List[str]  # IDs of papers citing this

    # Extracted analysis (for later phases)
    analysis_metadata: Dict[str, Any]  # Extensible for future use

    # Audit
    created_at: datetime
    last_updated: datetime

class GraphEdge:
    """Citation relationship"""
    edge_id: str
    source_node_id: str  # Paper A
    target_node_id: str  # Paper B (cited by A)

    relationship_type: str  # "cites", "extends", "contradicts", etc.
    citation_context: str  # Quote showing how it was cited

    # Metadata
    is_bidirectional: bool  # If B also cites A
    strength: float  # 0-1 confidence in relationship

class GraphQuery:
    """Flexible query builder"""
    filters: Dict[str, Any]  # {"author": "LeCun", "year_min": 2015}
    search_text: Optional[str]
    sort_by: str  # "date", "citations", "relevance"
    limit: int

class PaperGraphManager:
    """Main graph manager"""
    async def add_node(node: GraphNode) -> str
    async def add_edge(edge: GraphEdge) -> str
    async def query_nodes(query: GraphQuery) -> List[GraphNode]
    async def query_edges(query: GraphQuery) -> List[GraphEdge]
    async def get_node(node_id: str) -> GraphNode
    async def get_node_neighbors(node_id: str, depth: int) -> List[GraphNode]
    async def get_graph_stats() -> GraphStats
```

**Database Technology Choice (pick one for MVP):**

**Option A: Neo4j (recommended for graphs)**

- Native graph DB, excellent for citation networks
- Cypher query language (declarative)
- Good for complex traversals
- Library: `neo4j-driver`

**Option B: PostgreSQL + pgvector (if you prefer relational)**

- Use JSONB columns for flexible metadata
- Use array columns for lists (authors, keywords)
- Build query builder for filtering
- Library: `sqlalchemy`, `psycopg2`

**Option C: MongoDB (if you prefer document DB)**

- Flexible schema for nodes
- Good for rapid iteration
- Needs manual implementation of graph logic
- Library: `pymongo`, `motor` (async)

**For MVP, recommend PostgreSQL with SQLAlchemy or Neo4j.**

**API Endpoints:**

```
GET    /api/v1/graph/nodes
       Query params: ?authors=LeCun&year_min=2015&keywords=attention&limit=50
       Returns: List of GraphNodes

GET    /api/v1/graph/nodes/{node_id}
       Returns: Detailed GraphNode with all metadata

GET    /api/v1/graph/nodes/{node_id}/neighbors
       Query params: ?depth=2
       Returns: Neighboring nodes up to depth

GET    /api/v1/graph/edges
       Query params: ?source={id}&relationship_type=cites
       Returns: List of edges matching filter

GET    /api/v1/graph/search
       Query params: ?q=attention%20mechanism&fields=title,abstract
       Returns: Full-text search results

GET    /api/v1/graph/stats
       Returns: {total_nodes, total_edges, avg_citations_per_paper}

POST   /api/v1/graph/advanced-query
       Body: {filters: {...}, search_text: "...", sort_by: "date"}
       Returns: Custom query results
```

**Example Query Response:**

```json
{
  "query": {
    "filters": { "keywords": ["attention", "transformer"], "year_min": 2015 },
    "limit": 50
  },
  "results": [
    {
      "node_id": "paper_arxiv_2106.03762",
      "title": "Attention Is All You Need",
      "authors": ["Vaswani, A.", "Shazeer, N."],
      "publication_date": "2017-06-12",
      "venue": "NeurIPS 2017",
      "abstract": "...",
      "keywords": ["attention", "transformer", "sequence"],
      "citation_count": {
        "outgoing": 127, // Papers this cites
        "incoming": 89420 // Papers citing this
      },
      "neighbors": {
        "depth_1_outgoing": 127,
        "depth_1_incoming": 100
      }
    }
  ],
  "total_results": 1247,
  "query_time_ms": 234
}
```
