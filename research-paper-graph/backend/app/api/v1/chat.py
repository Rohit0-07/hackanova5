"""Conversational RAG API for chatting with the analyzed research literature."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from loguru import logger

from app.agents.storage_manager import PipelineStorageManager
from app.services.parser.extractors.llm_extractor import get_llm_client
from app.core.config import settings

router = APIRouter()
storage_manager = PipelineStorageManager()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


CHAT_SYSTEM_PROMPT = """\
You are an expert Research Assistant specializing in literature synthesis. Answer questions using ONLY the provided research papers below.

Format your response EXACTLY like this:

## Answer
<1-2 clear, well-reasoned sentences directly answering the question>

## Key Evidence
- <specific finding from paper> — **[Paper Title](URL)**
- <another finding or methodology> — **[Another Paper](URL)**

## Referenced Papers & Concepts
- Paper: [Title](URL) - Brief relevance (year)
- Concept: brief explanation of how it relates

DO NOT include any text before "## Answer" or after the last section. ALWAYS use markdown links **[Title](URL)** for papers.

Your answers should be direct, evidence-based, and properly cited with clickable paper links.

--- CONTEXT START ---
{context}
--- CONTEXT END ---
"""


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat_with_session(session_id: str, request: ChatRequest):
    """Ask a question against the analyzed papers in a specific research session."""
    state = storage_manager.get_state_by_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Build context from analyzed papers
    papers_context = []
    
    # Use the papers and their analyses from the pipeline state
    for paper in state.papers:
        paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
        analysis = state.analyses.get(paper_id)
        
        if analysis:
            # Provide a short summary of available visuals/artifacts for this paper
            artifacts = []
            for a in (paper.get('artifacts') or []):
                artifacts.append({
                    "type": a.get('type'),
                    "location": a.get('location'),
                    "summary": str(a.get('content', ''))[:300],
                })

            paper_url = paper.get('url') or paper.get('pdf_url', '')
            citation = f"[{paper.get('title')}](" + paper_url + ") (Paper)" if paper_url else paper.get('title')

            ctx = {
                "title": paper.get('title'),
                "url": paper_url,
                "citation": citation,
                "authors": paper.get('authors', []),
                "year": paper.get('year'),
                "abstract": paper.get('abstract', ''),
                "key_findings": analysis.get("key_findings", []),
                "claims": analysis.get("claims", []),
                "methodology": analysis.get("methodology", ""),
                "artifacts": artifacts,
            }
            papers_context.append(ctx)

    if not papers_context:
        return ChatResponse(
            reply="No papers have been fully analyzed yet in this session. The agent needs analyzed papers to answer questions."
        )

    # Include graph nodes so the model can reference them explicitly
    graph_nodes = []
    if hasattr(state, 'graph_nodes') and isinstance(state.graph_nodes, dict):
        graph_nodes_raw = state.graph_nodes.get('nodes', []) or []
        # Add an explicit citation label for each node to help the model reference it cleanly
        for node in graph_nodes_raw:
            node_id = node.get('id')
            node_type = node.get('type')
            label = node.get('properties', {}).get('title') or node.get('properties', {}).get('name') or node_id
            node['citation'] = f"node:{node_id} ({node_type})"
            node['label'] = label
            
            # If this node is a Paper, add the paper URL so it can be a clickable link
            if node_type == 'Paper':
                paper_url = node.get('properties', {}).get('url')
                if paper_url:
                    # Create a markdown link for the node
                    node['clickable_link'] = f"[{label}]({paper_url})"
                    node['paper_url'] = paper_url
            
        graph_nodes = graph_nodes_raw

    context_payload = {
        "papers": papers_context,
        "graph_nodes": graph_nodes,
    }

    context_json = json.dumps(context_payload, indent=2, default=str)
    system_prompt = CHAT_SYSTEM_PROMPT.format(context=context_json)

    # Initialize LLM client from settings
    llm_client = get_llm_client(
        provider=settings.llm.provider,
        ollama_base_url=settings.llm.ollama.base_url,
        ollama_model=settings.llm.ollama.model,
        ollama_vision_model=settings.llm.ollama.vision_model,
        gemini_api_key=settings.llm.gemini.api_key,
        gemini_model=settings.llm.gemini.model,
    )

    try:
        response = await llm_client.generate(request.message, system_prompt=system_prompt)
        reply_text = response.text.strip()
        
        # Only do minimal cleanup: remove leading/trailing whitespace
        return ChatResponse(reply=reply_text)
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return ChatResponse(
            reply=(
                "Sorry, I couldn't generate a response right now. "
                "Please check the LLM configuration and try again."
            )
        )
