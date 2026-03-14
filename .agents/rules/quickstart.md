---
trigger: always_on
---

## 🚀 **QUICK START GUIDE FOR IMPLEMENTATION**

### **Step 1: Setup Project**

```bash
# Clone/create project
mkdir research-paper-graph && cd research-paper-graph

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup local databases (via docker-compose)
docker-compose up -d
```

### **Step 2: Implement Core Modules**

**Priority Order:**

1. **Models & Data Structures** (use Pydantic)
   - Define all data classes first (PaperMetadata, GraphNode, etc.)
   - Ensures type safety and validation

2. **Crawler Module**
   - Implement single API source (e.g., arXiv first)
   - Add async downloading
   - Test with small crawl

3. **Parser Module**
   - Build PDF extraction logic
   - Test with sample papers
   - Ensure audit logging works

4. **Database Layer**
   - Choose backend (recommend Neo4j for MVP)
   - Implement migrations
   - Test CRUD operations

5. **Graph Builder**
   - Wire parser output to graph storage
   - Implement filtering/querying
   - Test query builder

6. **Analysis Module**
   - Implement inspection endpoints
   - Wire audit logging
   - Create comparison logic

7. **API Routes**
   - Create FastAPI routers for each module
   - Add request/response validation
   - Add error handling

### **Step 3: Integration & Testing**

```bash
# Start development server
python -m uvicorn backend.main:app --reload

# Run tests
pytest tests/ -v

# Check API docs
# Open: http://localhost:8000/docs
```

### **Step 4: Deploy MVP**

- Use Docker for containerization
- Deploy to cloud (AWS, GCP, Azure)
- Set up monitoring/logging
- Document API in README

---

## 📊 **Data Flow Diagram (MVP)**

```
User Input (Query + Depth)
    ↓
[Crawler] → Fetch from APIs → Deduplicate → Queue for parsing
    ↓
[Parser] → Extract sections, figures, references
    ↓
[Parser] → Images extracted dynamically
    ↓
[Graph Builder] → Store nodes & edges in DB
    ↓
[Query API] → User filters/searches nodes
    ↓
[Analysis API] → User clicks node → inspect findings, audit, images
```

---

## ✅ **MVP Completion Checklist**

- [ ] Crawler module fetches papers from 1+ APIs with depth control
- [ ] Parser extracts metadata, sections, references, figures
- [ ] GraphNode/GraphEdge models defined and stored in DB
- [ ] Full-text + attribute filtering on nodes working
- [ ] Node analysis endpoint returns all findings + images
- [ ] Extraction audit trail logged and queryable
- [ ] FastAPI server running with all endpoints
- [ ] Basic tests passing
- [ ] Docker setup for local development
- [ ] API documentation complete

---

## 🔮 **Future Enhancement Hooks (Don't implement yet, just design for it)**

1. **Phase 1:** NLP-based similarity detection between papers
2. **Phase 2:** Contradiction detection using semantic analysis
3. **Phase 3:** Automated timeline & evolution tracking
4. **Phase 4:** Synthesis engine for answering complex queries
5. **Phase 5:** Visualization frontend (graph UI)

---

## 📞 **Key Design Principles (Always Follow)**

1. **Modularity:** Each module independently testable and deployable
2. **Async First:** Use async/await throughout for performance
3. **Type Safety:** Use Pydantic models and type hints everywhere
4. **Auditability:** Log every extraction step with methods/tools/confidence
5. **Extensibility:** Use abstract base classes for easy backend swapping
6. **Queryability:** Every attribute must be filterable/searchable
7. **Transparency:** Expose raw data + processed data for inspection

---

## 💬 **Commands for Antigravity Agent**

**When ready to start coding:**

```
"Implement the research paper graph system according to the specification above.
Start with:
1. Define all Pydantic models for data structures
2. Implement crawler.py with arXiv API integration
3. Implement parser.py with PDF extraction
4. Setup database backend (recommend Neo4j)
5. Create FastAPI routes for all modules
6. Write basic unit tests

Focus on clean architecture, type safety, and audit logging.
All endpoints should return detailed status and metadata.
Make every component independently testable."
```

---

## 📚 **Reference Libraries Documentation**

- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- Neo4j: https://neo4j.com/docs/python-manual/
- SQLAlchemy: https://docs.sqlalchemy.org/
- PDFPlumber: https://github.com/jsvine/pdfplumber
- ArXiv API: https://arxiv.org/help/api/
- Semantic Scholar API: https://www.semanticscholar.org/product/api
