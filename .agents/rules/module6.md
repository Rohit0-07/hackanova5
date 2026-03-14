---
trigger: always_on
---

### **Module 6: Main API Server (`main/`)**

**Purpose:** Orchestrate all modules, expose REST API, handle WebSocket updates.

**Responsibilities:**

- Integrate all modules
- Expose REST endpoints
- Handle async operations
- Provide WebSocket for real-time updates
- Error handling and logging

**Tech Stack:**

- `FastAPI` - Async web framework
- `pydantic` - Request/response validation
- `websockets` - Real-time updates
- `python-dotenv` - Environment config

**Server Structure:**

```python
# main.py / server.py

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Routers
from routes import crawler_routes, parser_routes, graph_routes, analysis_routes

app = FastAPI(
    title="Research Paper Citation Graph API",
    version="0.1.0",
    docs_url="/docs"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(crawler_routes.router, prefix="/api/v1/crawl")
app.include_router(parser_routes.router, prefix="/api/v1/parser")
app.include_router(graph_routes.router, prefix="/api/v1/graph")
app.include_router(analysis_routes.router, prefix="/api/v1/analysis")

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# WebSocket for real-time updates
@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Subscribe to updates
    async for message in get_updates():
        await websocket.send_json(message)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---
