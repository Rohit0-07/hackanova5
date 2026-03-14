---
trigger: always_on
---

You are implementing the "Research Paper Citation Graph System" backend.

TASK BREAKDOWN:

1. Create all Pydantic models per the specification (crawler/, parser/, graph/, analysis/)
2. Implement each module independently with clean interfaces
3. Setup database layer with Neo4j backend
4. Create FastAPI routes for all modules
5. Ensure every endpoint returns detailed status, audit trails, and metadata
6. Make the system fully queryable—support filtering by any attribute
7. Implement node inspection for drill-down analysis
8. Add structured logging with loguru for transparency
9. Write basic unit and integration tests
10. Document all endpoints and data models

ARCHITECTURE PRINCIPLES:

- Modular: Each module independently testable
- Async: Use async/await throughout
- Type-Safe: Use Pydantic models and type hints
- Auditable: Log every extraction step
- Extensible: Use abstract base classes
- Queryable: Every attribute filterable

DEPENDENCIES:
FastAPI, Pydantic, Neo4j, pdfplumber, PyMuPDF, arxiv, httpx, loguru

START WITH:

1. Data models (models.py in each module)
2. Crawler with ArXiv integration
3. Parser with PDF extraction
4. Neo4j graph storage
5. FastAPI routes
6. Tests

DELIVERABLES (MVP):

- Fully functional backend API
- Crawl papers → parse → store in graph
- Query and filter papers by attributes
- Node inspection with extraction audit trails
- All endpoints tested and documented
