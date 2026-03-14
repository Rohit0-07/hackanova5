"""
Agent Orchestrator — Manages the multi-agent pipeline for research paper analysis.

Flow:
  1. Query Agent: Refines user query → SearchParams
  2. Paper Finder Agent: Finds papers from sources → PaperList  
  3. Citation Trail Agent: Builds citation graph → CitationTree
  4. Content Extractor Agent: Extracts images/tables/diagrams → Artifacts
  5. Analysis Agent: Analyzes each paper → Findings
  6. Section Extractor Agent: Makes relevant sections → SectionedContent
  7. Relationship Agent: Analyzes feature relationships → RelationshipMap
  8. Graph Builder Agent: Constructs knowledge graph → GraphNodes
  9. Query Agent: Answers user queries from graph & stored data
"""

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from loguru import logger

from app.services.parser.extractors.llm_extractor import get_llm_client
from app.core.config import settings


@dataclass
class PipelineState:
    """Tracks the state as it flows through the agent pipeline."""
    
    # User input
    raw_query: str
    user_id: str
    session_id: str
    session_name: Optional[str] = None
    
    # Refined query (from Query Agent)
    refined_query: Optional[Dict[str, Any]] = None
    
    # Found papers (from Paper Finder Agent)
    papers: List[Dict[str, Any]] = None
    
    # Citation trail (from Citation Trail Agent)
    citation_tree: Optional[Dict[str, Any]] = None
    
    # Extracted content (from Content Extractor Agent)
    extracted_artifacts: Optional[List[Dict[str, Any]]] = None
    
    # Paper analyses (from Analysis Agent)
    analyses: Optional[Dict[str, Dict[str, Any]]] = None  # paper_id -> analysis
    
    # Sectioned content (from Section Extractor Agent)
    sectioned_content: Optional[Dict[str, Dict[str, Any]]] = None  # paper_id -> sections
    
    # Relationship analysis (from Relationship Agent)
    relationships: Optional[Dict[str, Any]] = None
    
    # Graph nodes (from Graph Builder Agent)
    graph_nodes: Optional[List[Dict[str, Any]]] = None
    
    # Synthesis results (from Synthesis Agent)
    synthesis: Optional[Dict[str, Any]] = None  # includes literature_summary, contradictions, research_gaps
    
    # Constraints
    max_papers: int = 20
    max_depth: int = 3
    
    # Metadata
    created_at: str = None
    updated_at: str = None
    status: str = "initialized"  # initialized, in_progress, completed, failed
    errors: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()
        if self.errors is None:
            self.errors = []
        if self.papers is None:
            self.papers = []
        if self.extracted_artifacts is None:
            self.extracted_artifacts = []
        if self.analyses is None:
            self.analyses = {}
        if self.sectioned_content is None:
            self.sectioned_content = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return asdict(self)
    
    def save_to_file(self, storage_dir: Path = None) -> Path:
        """Save pipeline state to persistent storage."""
        if storage_dir is None:
            storage_dir = Path("./data/pipeline_storage/states")
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a stable filename for the session
        filename = f"{self.session_id}.json"
        filepath = storage_dir / filename
        
        # Also save a backup with timestamp for history
        timestamp = self.updated_at.replace(':', '-') if self.updated_at else self.created_at.replace(':', '-')
        history_dir = storage_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / f"{self.session_id}_{timestamp}.json"
        
        data = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        # Optional: limited history backup
        try:
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass
        
        logger.debug(f"Pipeline state saved to {filepath}")
        return filepath
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> "PipelineState":
        """Load pipeline state from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)


class BaseAgent:
    """Base class for all agents in the pipeline."""
    
    def __init__(self, agent_name: str, llm_client=None):
        self.agent_name = agent_name
        self.llm_client = llm_client or get_llm_client(
            provider=settings.llm.provider,
            ollama_base_url=settings.llm.ollama.base_url,
            ollama_model=settings.llm.ollama.model,
            ollama_vision_model=settings.llm.ollama.vision_model,
        )
        logger.info(f"Initialized {agent_name}")
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Execute the agent's task on the current pipeline state."""
        raise NotImplementedError(f"{self.agent_name} must implement execute()")
    
    def _log_step(self, message: str):
        """Log a step in agent execution."""
        logger.info(f"[{self.agent_name}] {message}")
    
    def _update_state(self, state: PipelineState):
        """Update state and persist for real-time updates."""
        state.updated_at = datetime.utcnow().isoformat()
        state.save_to_file() # Uses default directory ./data/pipeline_storage/states
    
    def _add_error(self, state: PipelineState, error: str) -> PipelineState:
        """Add error to pipeline state."""
        state.errors.append(f"[{self.agent_name}] {error}")
        logger.error(f"[{self.agent_name}] {error}")
        return state


class AgentPipeline:
    """Orchestrates sequential execution of agent pipeline."""
    
    def __init__(self, agents: List[BaseAgent], storage_dir: Optional[Path] = None):
        self.agents = agents
        self.storage_dir = storage_dir or Path("./data/pipeline_storage/states")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized pipeline with {len(agents)} agents")
    
    async def execute(
        self,
        query: str,
        session_id: str,
        session_name: str,
        user_id: str,
        max_papers: int = 20,
        max_depth: int = 3,
    ) -> PipelineState:
        """Execute the full agent pipeline."""
        
        # Initialize state
        state = PipelineState(
            raw_query=query,
            session_name=session_name,
            user_id=user_id,
            session_id=session_id,
            max_papers=max_papers,
            max_depth=max_depth,
            status="in_progress"
        )
        
        logger.info(f"Starting pipeline for session {session_id}, query: '{query[:100]}'")
        
        # Persist initial state immediately so status checks can find it
        state.save_to_file(self.storage_dir)
        
        try:
            # Execute each agent sequentially
            for agent in self.agents:
                self._log_agent_start(agent.agent_name)
                
                try:
                    state = await agent.execute(state)
                    state.updated_at = datetime.utcnow().isoformat()
                    state.save_to_file(self.storage_dir)
                    self._log_agent_complete(agent.agent_name)
                    
                    # Stop if we have a critical failure in an early stage
                    if state.status == "failed":
                        logger.error(f"Pipeline execution halted due to failure in {agent.agent_name}")
                        break
                        
                except Exception as e:
                    logger.exception(f"Agent {agent.agent_name} failed: {e}")
                    state.errors.append(f"{agent.agent_name} failed: {str(e)}")
                    state.status = "failed"
                    state.save_to_file(self.storage_dir)
                    # Continue to next agent (optional: change for fail-fast)
            
            if state.status != "failed":
                state.status = "completed"
            logger.info(f"Pipeline completed for session {session_id} (status={state.status})")
            
        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            state.status = "failed"
            state.errors.append(f"Pipeline failed: {str(e)}")
            state.save_to_file(self.storage_dir)
        
        # Save final state (ensures any last updates are persisted)
        state.save_to_file(self.storage_dir)
        
        return state
    
    def _log_agent_start(self, agent_name: str):
        logger.info(f"► Starting agent: {agent_name}")
    
    def _update_state(self, state: PipelineState):
        """Update state and persist for real-time updates."""
        state.updated_at = datetime.utcnow().isoformat()
        state.save_to_file(self.storage_dir)

    def _log_agent_complete(self, agent_name: str):
        logger.info(f"✓ Completed agent: {agent_name}")
