"""
Pipeline Research API Routes
Endpoints for running the complete multi-agent research analysis pipeline.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, AsyncGenerator
import uuid
import json
import asyncio
from loguru import logger

from app.agents.pipeline_setup import create_research_pipeline
from app.agents.storage_manager import PipelineStorageManager
from app.agents.orchestrator import PipelineState


router = APIRouter()
storage_manager = PipelineStorageManager()


# ==================== Request/Response Models ====================

class ResearchQueryRequest(BaseModel):
    """Request to start a research analysis pipeline."""
    query: str = Field(..., description="The research question or topic to analyze")
    session_name: Optional[str] = Field(default="", description="Friendly name for this research session")
    user_id: str = Field(default="anonymous", description="User identifier")
    max_papers: Optional[int] = Field(default=20, description="Maximum papers to find")
    max_citation_depth: Optional[int] = Field(default=3, description="Max depth for citation tree")
    llm_provider: Optional[str] = Field(default="ollama", description="Provider (ollama or gemini)")
    focus_areas: Optional[List[str]] = Field(default=["findings", "claims", "methodology"], description="Specific focus areas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are recent advancements in attention mechanisms for transformers?",
                "user_id": "researcher_123",
                "max_papers": 20,
                "max_citation_depth": 3
            }
        }


class PipelineResponse(BaseModel):
    """Response from pipeline execution."""
    session_id: str
    status: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "status": "completed",
                "message": "Analysis complete. 15 papers analyzed."
            }
        }


class PipelineStatusResponse(BaseModel):
    """Response with pipeline state and results."""
    session_id: str
    session_name: Optional[str]
    status: str
    query: str
    user_id: Optional[str]
    max_papers: Optional[int]
    max_citation_depth: Optional[int]
    papers_found: int
    analyses_complete: int
    graph_nodes: Optional[int]
    graph_edges: Optional[int]
    errors: List[str]
    synthesis: Optional[Dict[str, Any]]  # includes literature_summary, contradictions, research_gaps
    results: Optional[Dict[str, Any]]


class StorageStatsResponse(BaseModel):
    """Response with storage statistics."""
    total_sessions: int
    total_findings: int
    total_graphs: int
    storage_size_mb: float


# ==================== Pipeline Endpoints ====================

@router.post(
    "/analyze",
    response_model=PipelineResponse,
    tags=["Research Pipeline"],
    summary="Start multi-agent research analysis"
)
async def start_pipeline_analysis(
    request: ResearchQueryRequest,
    background_tasks: BackgroundTasks
) -> PipelineResponse:
    """
    Start a complete research analysis pipeline.
    
    This endpoint initiates the multi-agent pipeline that:
    1. Refines the research query
    2. Finds papers from multiple academic sources
    3. Builds citation trails
    4. Extracts content (images, tables, diagrams)
    5. Analyzes papers for key findings
    6. Extracts relevant sections
    7. Analyzes feature relationships
    8. Constructs knowledge graph
    
    Results are stored for querying and will be saved to disk.
    """
    
    logger.info(f"Starting pipeline analysis for: {request.query[:100]}")
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Run pipeline in background
    background_tasks.add_task(
        run_pipeline,
        query=request.query,
        session_id=session_id,
        session_name=request.session_name,
        user_id=request.user_id,
        max_papers=request.max_papers,
        max_depth=request.max_citation_depth,
        llm_provider=request.llm_provider,
    )
    
    return PipelineResponse(
        session_id=session_id,
        status="queued",
        message="Pipeline analysis queued. Results will be available shortly."
    )


async def run_pipeline(
    query: str,
    session_id: str,
    session_name: str,
    user_id: str,
    max_papers: int = 20,
    max_depth: int = 3,
    llm_provider: str = "ollama"
):
    """Execute the research pipeline (runs in background)."""
    
    try:
        logger.info(f"[{session_id}] Executing pipeline for query: {query}")
        
        # Create pipeline
        pipeline = create_research_pipeline(llm_provider=llm_provider)
        
        # Execute pipeline
        final_state = await pipeline.execute(
            query=query,
            session_id=session_id,
            session_name=session_name,
            user_id=user_id,
            max_papers=max_papers,
            max_depth=max_depth
        )
        
        # Save state
        storage_manager.save_state(final_state)
        
        # Save graph if available
        if final_state.graph_nodes:
            storage_manager.save_graph(session_id, final_state.graph_nodes)
        
        logger.info(f"[{session_id}] Pipeline completed successfully")

        # Send email notification if someone subscribed
        try:
            from app.services.email_service import send_completion_email
            papers_count = len(final_state.papers or [])
            send_completion_email(
                session_id=session_id,
                query=query,
                papers_count=papers_count,
                status=final_state.status,
            )
        except Exception as email_err:
            logger.warning(f"[{session_id}] Email notification skipped: {email_err}")
        
    except Exception as e:
        logger.exception(f"[{session_id}] Pipeline execution failed: {e}")


@router.get(
    "/status/{session_id}",
    response_model=PipelineStatusResponse,
    tags=["Research Pipeline"],
    summary="Get pipeline execution status"
)
async def get_pipeline_status(session_id: str) -> PipelineStatusResponse:
    """
    Get the status and results of a pipeline execution.
    
    Returns:
    - Current execution status
    - Number of papers analyzed
    - Knowledge graph statistics
    - Any errors encountered
    """
    
    try:
        state = storage_manager.get_state_by_session(session_id)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )
        
        # Handle None values safely
        analyses = state.analyses or {}
        papers = state.papers or []
        relationships = state.relationships or {}
        citation_tree = state.citation_tree or {}
        
        return PipelineStatusResponse(
            session_id=session_id,
            session_name=state.session_name if hasattr(state, 'session_name') else None,
            status=state.status,
            query=state.raw_query,
            user_id=getattr(state, 'user_id', None),
            max_papers=getattr(state, 'max_papers', None),
            max_citation_depth=getattr(state, 'max_depth', None),
            papers_found=len(papers),
            analyses_complete=len([a for a in analyses.values() if isinstance(a, dict) and 'status' not in a]),
            graph_nodes=state.graph_nodes.get('total_nodes') if isinstance(state.graph_nodes, dict) else None,
            graph_edges=state.graph_nodes.get('total_edges') if isinstance(state.graph_nodes, dict) else None,
            errors=state.errors or [],
            synthesis=state.synthesis,  # Include synthesis results
            results={
                "papers": papers,
                "analyses": analyses,
                "relationships": relationships,
                "citation_tree_summary": {
                    "total_unique": citation_tree.get('total_unique_papers', 0)
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Error retrieving status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/results/{session_id}",
    tags=["Research Pipeline"],
    summary="Get complete pipeline results"
)
async def get_pipeline_results(session_id: str) -> Dict[str, Any]:
    """
    Get the complete results from a pipeline execution.
    
    Returns full state including:
    - All papers found
    - Analyses and findings
    - Citation graph
    - Knowledge graph
    - Extracted content and relationships
    """
    
    try:
        state = storage_manager.get_state_by_session(session_id)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )
        
        return state.to_dict()
    
    except Exception as e:
        logger.error(f"Error retrieving results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/report/{session_id}",
    tags=["Research Pipeline"],
    summary="Get markdown report of analysis"
)
async def get_pipeline_report(
    session_id: str,
    format: str = Query("markdown", pattern="^(markdown|json)$")
) -> str:
    """
    Get a formatted report of the pipeline analysis.
    
    Supported formats:
    - markdown: Human-readable markdown report
    - json: Structured JSON data
    """
    
    try:
        report = storage_manager.export_findings_report(session_id, format=format)
        return report
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sessions",
    tags=["Research Pipeline"],
    summary="List all pipeline sessions"
)
async def list_sessions() -> Dict[str, Any]:
    """List all available analysis sessions and their status."""
    
    try:
        states = storage_manager.list_states()
        return {
            "total_sessions": len(states),
            "sessions": states
        }
    
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/storage/stats",
    response_model=StorageStatsResponse,
    tags=["Storage"],
    summary="Get storage statistics"
)
async def get_storage_stats() -> StorageStatsResponse:
    """Get statistics about pipeline storage usage."""
    
    try:
        stats = storage_manager.get_storage_stats()
        return StorageStatsResponse(
            total_sessions=stats["states"],
            total_findings=stats["findings"],
            total_graphs=stats["graphs"],
            storage_size_mb=stats["states_dir_size_mb"] + stats["findings_dir_size_mb"] + stats["graphs_dir_size_mb"]
        )
    
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/storage/cleanup",
    tags=["Storage"],
    summary="Cleanup old stored states"
)
async def cleanup_storage(days: int = Query(30, ge=1)):
    """
    Remove state files older than specified number of days.
    
    Args:
        days: Number of days to retain (default: 30)
    """
    
    try:
        storage_manager.cleanup_old_states(days=days)
        return {
            "message": f"Cleaned up states older than {days} days",
            "status": "success"
        }
    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stream/{session_id}",
    tags=["Research Pipeline"],
    summary="Stream pipeline progress updates (SSE)"
)
async def stream_pipeline_progress(session_id: str) -> StreamingResponse:
    """
    Stream real-time progress updates for a pipeline session using SSE.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        last_status = None
        last_updated = None
        
        # Keep track of which steps we've already sent to avoid duplicates
        sent_errors_count = 0
        sent_papers_count = 0
        sent_analyses_count = 0
        
        while True:
            try:
                state = storage_manager.get_state_by_session(session_id)
                if not state:
                    yield f"data: {json.dumps({'error': 'Session not found', 'session_id': session_id})}\n\n"
                    break
                
                # Check if state has changed
                current_updated = state.updated_at
                current_status = state.status
                
                # Always send the first update or if status/updated_at changed
                if last_updated != current_updated or last_status != current_status:
                    # Basic progress info
                    papers = state.papers or []
                    analyses = state.analyses or {}
                    errors = state.errors or []
                    
                    data = {
                        "session_id": session_id,
                        "status": state.status,
                        "progress": {
                            "papers_found": len(papers),
                            "analyses_complete": len([a for a in analyses.values() if isinstance(a, dict) and 'status' not in a]),
                            "errors_count": len(errors)
                        },
                        "updated_at": current_updated,
                        "graph_nodes": state.graph_nodes,
                        "analyses": state.analyses,
                        "papers": papers,
                        "synthesis": state.synthesis
                    }
                    
                    # Add new findings if available
                    if len(papers) > sent_papers_count:
                        data["new_papers"] = papers[sent_papers_count:]
                        sent_papers_count = len(papers)
                        
                    if len(errors) > sent_errors_count:
                        data["new_errors"] = errors[sent_errors_count:]
                        sent_errors_count = len(errors)
                        
                    if state.synthesis and last_status != "completed" and current_status == "completed":
                        data["synthesis"] = state.synthesis
                        
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    last_updated = current_updated
                    last_status = current_status
                
                # If completed or failed, stop streaming after one last check
                if current_status in ["completed", "failed"]:
                    break
                    
                await asyncio.sleep(1.0) # Poll every second
                
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get(
    "/health",
    tags=["Health"],
    summary="Pipeline health check"
)
async def pipeline_health() -> Dict[str, str]:
    """Check if the pipeline system is operational."""
    
    try:
        stats = storage_manager.get_storage_stats()
        return {
            "status": "healthy",
            "pipeline": "operational",
            "storage_accessible": "yes",
            "sessions_tracked": str(stats["states"])
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
