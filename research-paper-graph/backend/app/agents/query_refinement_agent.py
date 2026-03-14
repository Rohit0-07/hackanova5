"""Query Refinement Agent — Part of the pipeline, refines user queries for the research pipeline."""

from typing import Dict, Any, Optional
from loguru import logger
import json

from app.agents.orchestrator import BaseAgent, PipelineState
from app.agents.query_agent import QueryAgent as LegacyQueryAgent


class QueryRefinementAgent(BaseAgent):
    """Pipeline-integrated query refinement agent."""
    
    def __init__(self, llm_client=None):
        super().__init__("QueryRefinementAgent", llm_client)
        self.legacy_agent = LegacyQueryAgent(llm_client)
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Refine the user's raw query into structured search parameters."""
        
        self._log_step(f"Refining query: '{state.raw_query}'")
        
        try:
            # Use legacy query agent for refinement
            refined = await self.legacy_agent.refine_query(state.raw_query)
            
            state.refined_query = refined
            self._log_step(f"Refined into {len(refined.get('refined_queries', []))} search queries")
            
        except Exception as e:
            logger.exception(f"QueryRefinementAgent failed: {e}")
            return self._add_error(state, f"Failed to refine query: {str(e)}")
        
        return state
