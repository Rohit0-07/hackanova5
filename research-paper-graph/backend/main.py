"""Research Paper Citation Graph API - Main Entry Point"""

import os
import sys

# Ensure the current directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.core.logging import setup_logging
from app.api.v1 import chat as chat_routes
from app.api.v1 import pipeline as pipeline_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    setup_logging()
    logger.info("Autonomous Research Literature Agent API starting up")
    yield
    logger.info("Autonomous Research Literature Agent API shutting down")


app = FastAPI(
    title="Autonomous Research Literature Agent API",
    description="An autonomous agent that crawls academic databases, follows citation trails, extracts findings from papers, and builds a cross-paper knowledge graph.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 routers
app.include_router(
    chat_routes.router, prefix="/api/v1/chat", tags=["Conversational Chat"]
)
app.include_router(
    pipeline_routes.router, prefix="/api/v1/pipeline", tags=["Multi-Agent Pipeline"]
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
