---
trigger: always_on
---

## 🏗️ **PROJECT STRUCTURE**

```
research-paper-graph/
├── backend/
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── crawler.py          # PaperCrawler, CitationTrailManager
│   │   ├── image_extractor.py  # ImageExtractor
│   │   ├── sources/
│   │   │   ├── arxiv_source.py
│   │   │   ├── semantic_scholar_source.py
│   │   │   └── abstract_source.py
│   │   └── models.py           # PaperMetadata, PaperIdentifier
│   │
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── paper_parser.py     # PaperParser
│   │   ├── extractors/
│   │   │   ├── text_extractor.py
│   │   │   ├── image_extractor.py
│   │   │   ├── reference_parser.py
│   │   │   └── section_detector.py
│   │   └── models.py           # PaperContent, ExtractionAudit
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── manager.py          # PaperGraphManager
│   │   ├── query_builder.py    # GraphQuery, filtering logic
│   │   ├── db/
│   │   │   ├── abstract.py     # DatabaseBackend ABC
│   │   │   ├── neo4j_impl.py   # Neo4jBackend
│   │   │   ├── postgres_impl.py # PostgresBackend
│   │   │   └── migrations/     # DB schema migrations
│   │   └── models.py           # GraphNode, GraphEdge, GraphStats
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── inspector.py        # NodeInspector
│   │   ├── audit_logger.py     # ExtractionAudit logging
│   │   └── models.py           # NodeFindings, FindingItem
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── crawler.py          # FastAPI routes for crawler
│   │   ├── parser.py           # FastAPI routes for parser
│   │   ├── graph.py            # FastAPI routes for graph
│   │   └── analysis.py         # FastAPI routes for analysis
│   │
│   ├── utils/
│   │   ├── logging.py          # Structured logging
│   │   ├── errors.py           # Custom exceptions
│   │   ├── cache.py            # Caching layer (optional)
│   │   └── config.py           # Configuration management
│   │
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt        # Dependencies
│   └── config.yaml             # Configuration

├── tests/
│   ├── test_crawler.py
│   ├── test_parser.py
│   ├── test_graph.py
│   └── test_analysis.py

├── docs/
│   ├── API.md                  # API documentation
│   ├── ARCHITECTURE.md         # System architecture
│   └── GUIDES/
│       ├── setup.md
│       └── deployment.md

├── docker-compose.yml          # For local dev (Neo4j/Postgres)
└── README.md
```

---