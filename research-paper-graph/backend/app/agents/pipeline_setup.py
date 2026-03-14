"""
Pipeline Setup and Initialization
Configures the complete agent pipeline with proper sequencing.
"""

from typing import List, Optional
from pathlib import Path
from loguru import logger

from app.agents.orchestrator import BaseAgent, AgentPipeline
from app.agents.query_refinement_agent import QueryRefinementAgent
from app.agents.paper_finder_agent import PaperFinderAgent
from app.agents.citation_trail_agent import CitationTrailAgent
from app.agents.content_extractor_agent import ContentExtractorAgent
from app.agents.pipeline_analysis_agent import PipelineAnalysisAgent
from app.agents.section_extractor_agent import SectionExtractorAgent
from app.agents.relationship_analysis_agent import RelationshipAnalysisAgent
from app.agents.graph_builder_agent import GraphBuilderAgent
from app.agents.pipeline_synthesis_agent import PipelineSynthesisAgent
from app.services.parser.extractors.llm_extractor import get_llm_client
from app.core.config import settings


class ResearchPipelineFactory:
    """Factory for creating configured research analysis pipelines."""
    
    @staticmethod
    def create_default_pipeline(
        llm_provider: str = "ollama",
        storage_dir: Optional[Path] = None
    ) -> AgentPipeline:
        """
        Create the default research analysis pipeline with all agents in sequence.
        
        Pipeline Flow:
        1. QueryRefinementAgent - Refine user query into structured search params
        2. PaperFinderAgent - Find papers from multiple academic sources
        3. CitationTrailAgent - Build citation graph and tree
        4. ContentExtractorAgent - Extract images, tables, diagrams from papers
        5. PipelineAnalysisAgent - Analyze findings from each paper
        6. SectionExtractorAgent - Extract relevant sections for the topic
        7. RelationshipAnalysisAgent - Analyze relationships and feature connections
        8. GraphBuilderAgent - Construct knowledge graph with all findings
        9. PipelineSynthesisAgent - Synthesize findings: literature summary, contradictions, research gaps
        """
        
        if storage_dir is None:
            storage_dir = Path("./data/pipeline_storage/states")
        
        logger.info("Creating default research pipeline")
        
        # Initialize LLM client
        llm_client = get_llm_client(
            provider=settings.llm.provider,
            ollama_base_url=settings.llm.ollama.base_url,
            ollama_model=settings.llm.ollama.model,
            ollama_vision_model=settings.llm.ollama.vision_model,
        )
        
        # Create agents in publication order
        agents: List[BaseAgent] = [
            # Step 1: Refine the query
            QueryRefinementAgent(llm_client=llm_client),
            
            # Step 2: Find papers
            PaperFinderAgent(llm_client=llm_client),
            
            # Step 3: Build citation tree
            CitationTrailAgent(max_depth=3, llm_client=llm_client),
            
            # Step 4: Extract content (images, tables, diagrams)
            ContentExtractorAgent(llm_client=llm_client),
            
            # Step 5: Analyze papers
            PipelineAnalysisAgent(llm_client=llm_client),
            
            # Step 6: Extract relevant sections
            SectionExtractorAgent(llm_client=llm_client),
            
            # Step 7: Analyze relationships
            RelationshipAnalysisAgent(llm_client=llm_client),
            
            # Step 8: Build knowledge graph
            GraphBuilderAgent(llm_client=llm_client),
            
            # Step 9: Synthesize knowledge (literature summary, contradictions, gaps)
            PipelineSynthesisAgent(llm_client=llm_client),
        ]
        
        logger.info(f"Pipeline configured with {len(agents)} agents")
        
        return AgentPipeline(agents=agents, storage_dir=storage_dir)
    
    @staticmethod
    def create_custom_pipeline(
        agent_types: List[str],
        llm_provider: str = "ollama",
        storage_dir: Optional[Path] = None
    ) -> AgentPipeline:
        """
        Create a custom pipeline with selected agents.
        
        Args:
            agent_types: List of agent class names to include
                e.g., ["QueryRefinementAgent", "PaperFinderAgent", "PipelineAnalysisAgent"]
            llm_provider: LLM provider to use
            storage_dir: Directory for storing pipeline state
        
        Returns:
            Configured AgentPipeline
        """
        
        if storage_dir is None:
            storage_dir = Path("./data/pipeline_storage/states")
        
        logger.info(f"Creating custom pipeline with agents: {agent_types}")
        
        llm_client = get_llm_client(provider=llm_provider)
        
        agent_map = {
            "QueryRefinementAgent": QueryRefinementAgent,
            "PaperFinderAgent": PaperFinderAgent,
            "CitationTrailAgent": CitationTrailAgent,
            "ContentExtractorAgent": ContentExtractorAgent,
            "PipelineAnalysisAgent": PipelineAnalysisAgent,
            "SectionExtractorAgent": SectionExtractorAgent,
            "RelationshipAnalysisAgent": RelationshipAnalysisAgent,
            "GraphBuilderAgent": GraphBuilderAgent,
            "PipelineSynthesisAgent": PipelineSynthesisAgent,
        }
        
        agents = []
        for agent_name in agent_types:
            if agent_name in agent_map:
                agents.append(agent_map[agent_name](llm_client=llm_client))
            else:
                logger.warning(f"Unknown agent type: {agent_name}")
        
        if not agents:
            raise ValueError(f"No valid agents specified: {agent_types}")
        
        logger.info(f"Custom pipeline configured with {len(agents)} agents")
        
        return AgentPipeline(agents=agents, storage_dir=storage_dir)


# Convenience functions for quick pipeline creation
def create_research_pipeline(llm_provider: str = "ollama") -> AgentPipeline:
    """Create a default research analysis pipeline."""
    return ResearchPipelineFactory.create_default_pipeline(llm_provider)


def create_pipeline_with_agents(
    agent_types: List[str],
    llm_provider: str = "ollama"
) -> AgentPipeline:
    """Create a custom pipeline with specified agents."""
    return ResearchPipelineFactory.create_custom_pipeline(agent_types, llm_provider)
