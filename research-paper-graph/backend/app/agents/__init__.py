"""Research Agent Module - Multi-agent pipeline for paper analysis."""

# Core orchestration
from app.agents.orchestrator import BaseAgent, AgentPipeline, PipelineState

# Query and discovery agents
from app.agents.query_agent import QueryAgent
from app.agents.query_refinement_agent import QueryRefinementAgent
from app.agents.paper_finder_agent import PaperFinderAgent

# Citation and relationship agents
from app.agents.citation_trail_agent import CitationTrailAgent
from app.agents.relationship_analysis_agent import RelationshipAnalysisAgent

# Analysis agents
from app.agents.analysis_agent import AnalysisAgent
from app.agents.pipeline_analysis_agent import PipelineAnalysisAgent
from app.agents.content_extractor_agent import ContentExtractorAgent
from app.agents.section_extractor_agent import SectionExtractorAgent

# Synthesis and graph agents
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.pipeline_synthesis_agent import PipelineSynthesisAgent
from app.agents.graph_builder_agent import GraphBuilderAgent

# Pipeline setup
from app.agents.pipeline_setup import (
    ResearchPipelineFactory,
    create_research_pipeline,
    create_pipeline_with_agents
)

__all__ = [
    # Core
    "BaseAgent",
    "AgentPipeline",
    "PipelineState",
    
    # Legacy agents
    "QueryAgent",
    "AnalysisAgent",
    "SynthesisAgent",
    
    # Pipeline agents
    "QueryRefinementAgent",
    "PaperFinderAgent",
    "CitationTrailAgent",
    "ContentExtractorAgent",
    "PipelineAnalysisAgent",
    "SectionExtractorAgent",
    "RelationshipAnalysisAgent",
    "GraphBuilderAgent",
    "PipelineSynthesisAgent",
    
    # Pipeline factory
    "ResearchPipelineFactory",
    "create_research_pipeline",
    "create_pipeline_with_agents",
]
