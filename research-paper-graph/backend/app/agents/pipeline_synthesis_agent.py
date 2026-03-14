"""Synthesis Agent (Pipeline Version) — Synthesizes knowledge across multiple papers."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from loguru import logger

from app.agents.orchestrator import BaseAgent, PipelineState
from app.agents.synthesis_agent import SynthesisAgent as LegacySynthesisAgent


class SimpleMetadata:
    """Simple wrapper for paper metadata."""
    
    def __init__(self, paper_dict: Dict[str, Any]):
        self.title = paper_dict.get('title', 'Unknown')
        self.abstract = paper_dict.get('abstract', '')
        
        # Handle publication_date parsing
        pub_date = paper_dict.get('publication_date') or paper_dict.get('year')
        if isinstance(pub_date, str):
            try:
                # Try simple year string first
                if len(pub_date) == 4 and pub_date.isdigit():
                    self.publication_date = datetime(int(pub_date), 1, 1)
                else:
                    self.publication_date = datetime.fromisoformat(pub_date)
            except (ValueError, TypeError):
                self.publication_date = datetime.now()
        elif isinstance(pub_date, int):
            self.publication_date = datetime(pub_date, 1, 1)
        elif hasattr(pub_date, 'year'):
            self.publication_date = pub_date
        else:
            self.publication_date = datetime.now()


class SimplePaper:
    """Simple wrapper for paper data to work with synthesis agent."""
    
    def __init__(self, paper_dict: Dict[str, Any], analysis: Dict[str, Any]):
        self.paper_id = paper_dict.get('id') or paper_dict.get('title', '').replace(' ', '_')[:50]
        
        # Create a simple metadata object
        self.metadata = SimpleMetadata(paper_dict)
        
        # Store analysis
        self.analysis = analysis if analysis and analysis.get('status') != 'error' else {}


class PipelineSynthesisAgent(BaseAgent):
    """Pipeline-integrated synthesis agent for cross-paper knowledge synthesis."""
    
    def __init__(self, llm_client=None):
        super().__init__("PipelineSynthesisAgent", llm_client)
        self.legacy_agent = LegacySynthesisAgent()
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Synthesize knowledge across all analyzed papers."""
        
        if not state.papers:
            return self._add_error(state, "No papers available for synthesis")
        
        if not state.analyses:
            return self._add_error(state, "No paper analyses available for synthesis")
        
        self._log_step(f"Synthesizing knowledge from {len(state.papers)} papers")
        
        try:
            # Convert papers to simple wrapper objects for synthesis agent
            simple_papers: List[SimplePaper] = []
            
            for paper in state.papers:
                paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
                analysis = state.analyses.get(paper_id, {})
                
                # Create a simple paper wrapper
                simple_paper = SimplePaper(paper, analysis)
                simple_papers.append(simple_paper)
            
            # Generate synthesis
            synthesis_result = await self.legacy_agent.generate_synthesis(
                query=state.raw_query,
                papers=simple_papers  # type: ignore
            )
            
            # Store synthesis in pipeline state
            state.synthesis = {
                "literature_summary": synthesis_result.get("literature_summary", ""),
                "contradictions": synthesis_result.get("contradictions", []),
                "research_gaps": synthesis_result.get("research_gaps", []),
                "generated_at": self._get_timestamp()
            }
            # Pipeline orchestrator will persist state after each agent; no need to call _update_state here.
            
            self._log_step(
                f"Synthesis complete: "
                f"{len(synthesis_result.get('contradictions', []))} contradictions, "
                f"{len(synthesis_result.get('research_gaps', []))} research gaps identified"
            )
            
        except Exception as e:
            logger.exception(f"PipelineSynthesisAgent failed: {e}")
            return self._add_error(state, f"Failed to synthesize knowledge: {str(e)}")
        
        return state
    
    def _get_timestamp(self) -> str:
        """Get ISO format timestamp."""
        return datetime.utcnow().isoformat()
