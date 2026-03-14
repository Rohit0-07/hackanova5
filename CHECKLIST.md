## **MODULE IMPLEMENTATION CHECKLIST**

### **CRAWLER Module**
- [ ] Define `PaperIdentifier`, `PaperMetadata` models
- [ ] Create abstract `APISource` interface
- [ ] Implement `ArxivSource` with `get_papers_by_query()`, `get_paper_metadata()`, `get_citations()`
- [ ] Implement `SemanticScholarSource` similarly
- [ ] Create `PaperCrawler` orchestrator with depth-limited BFS
- [ ] Add duplicate detection using hash + DOI matching
- [ ] Add rate limiting and retry logic
- [ ] Implement progress tracking via `CrawlSession` state object
- [ ] Create endpoints: POST /start, GET /status, GET /frontier

### **PARSER Module**
- [ ] Define `SectionContent`, `ExtractedFigure`, `PaperContent` models
- [ ] Create `PaperParser` facade
- [ ] Implement `text_extractor.py` using pdfplumber + fitz
- [ ] Implement `image_extractor.py` using pdf2image
- [ ] Implement `reference_parser.py` for citation normalization
- [ ] Implement `ExtractionAudit` logging with timestamps & confidence
- [ ] Create endpoints: POST /parse-paper, GET /content, GET /audit

### **GRAPH Module**
- [ ] Define `GraphNode`, `GraphEdge`, `GraphStats` models
- [ ] Create abstract `DatabaseBackend` interface
- [ ] Implement Neo4j backend (or Postgres)
- [ ] Create `QueryBuilder` for flexible filtering
- [ ] Implement CRUD operations
- [ ] Add graph traversal functions (neighbors, depth-N)
- [ ] Create endpoints: GET /nodes, GET /edges, POST /advanced-query

### **ANALYSIS Module**
- [ ] Define `NodeFindings`, `FindingItem`, `ExtractionMethod` models
- [ ] Create `NodeInspector` facade
- [ ] Link to stored `PaperContent` and `ExtractionAudit`
- [ ] Create endpoints: GET /node/{id}, GET /audit, GET /raw

### **ROUTES & SERVER**
- [ ] Setup FastAPI app with all routers
- [ ] Add request/response validation
- [ ] Add error handling (404, 400, 500)
- [ ] Add CORS middleware
- [ ] Create /health endpoint
- [ ] Setup logging with loguru
- [ ] Test all endpoints with curl/Postman

### **DATABASE**
- [ ] Write schema/migrations
- [ ] Setup connection pooling
- [ ] Create indexes on frequently queried fields (authors, keywords, date)
- [ ] Test transactions and batch operations

### **TESTING**
- [ ] Write unit tests for each module
- [ ] Write integration tests for API endpoints
- [ ] Add fixtures for mock data
- [ ] Run coverage report
