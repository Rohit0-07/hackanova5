"""Relationship Analysis Agent — Analyzes relationships between papers and features based on citation tree."""

from typing import Dict, Any, List, Optional
from loguru import logger
import json

from app.agents.orchestrator import BaseAgent, PipelineState


RELATIONSHIP_ANALYSIS_PROMPT = """You are an expert research relationship analyst. Given multiple papers and their citation relationships, analyze:

1. **Feature Relationships**: How are key concepts related across papers?
2. **Methodological Connections**: How do different approaches relate?
3. **Building Blocks**: Which papers are foundational vs derivative?
4. **Contradictions**: Where do papers disagree?
5. **Complementary Work**: Which papers complement each other?
6. **Citation Patterns**: What citation patterns indicate influence?

Output valid JSON:
{
  "feature_relationships": [
    {
      "feature1": "feature name",
      "feature2": "feature name",
      "relationship_type": "builds_on|extends|contradicts|complements",
      "strength": 0.9,
      "papers_involved": ["paper_id1", "paper_id2"],
      "description": "how they relate"
    }
  ],
  "citation_hierarchy": {
    "foundational_papers": ["id1", "id2"],
    "derivative_papers": ["id3", "id4"],
    "cluster_analysis": {"cluster_name": ["papers"]}
  },
  "research_progression": "narrative of how field evolved",
  "key_connections": ["connection1", "connection2"]
}

Analyze deeply and provide actionable insights."""


class RelationshipAnalysisAgent(BaseAgent):
    """Analyzes relationships between papers, their findings, and citation patterns."""
    
    def __init__(self, llm_client=None):
        super().__init__("RelationshipAnalysisAgent", llm_client)
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Analyze relationships within the citation tree."""
        
        if not state.papers or not state.citation_tree or not state.analyses:
            return self._add_error(state, "Missing required data for relationship analysis")
        
        self._log_step(f"Analyzing relationships for {len(state.papers)} papers")
        
        try:
            # Extract key information from papers and analyses
            paper_context = self._prepare_paper_context(state)
            
            # Analyze relationships using LLM
            relationships = await self._analyze_relationships_with_llm(
                paper_context,
                state.citation_tree,
                state.raw_query
            )
            
            # Enhance with citation-based analysis
            relationships = self._enhance_with_citations(
                relationships,
                state.citation_tree
            )
            
            # Add parent-child relationships from citation tree
            relationships["parent_child_relationships"] = self._extract_hierarchy(
                state.citation_tree
            )
            
            state.relationships = relationships
            self._log_step(f"Identified {len(relationships.get('feature_relationships', []))} key relationships")
            
        except Exception as e:
            logger.exception(f"RelationshipAnalysisAgent failed: {e}")
            return self._add_error(state, f"Failed to analyze relationships: {str(e)}")
        
        return state
    
    def _prepare_paper_context(self, state: PipelineState) -> str:
        """Prepare context string with paper information."""
        
        context = []
        
        for paper in state.papers:
            paper_id = paper.get('id') or paper.get('title', '')[:50]
            analysis = state.analyses.get(paper_id, {})
            
            context.append({
                "id": paper_id,
                "title": paper.get('title'),
                "year": paper.get('year'),
                "key_findings": analysis.get('key_findings', []),
                "methodology": analysis.get('methodology', ''),
                "contributions": analysis.get('contributions', []),
                "claims": analysis.get('claims', [])
            })
        
        return json.dumps(context, indent=2)
    
    async def _analyze_relationships_with_llm(
        self,
        paper_context: str,
        citation_tree: Dict[str, Any],
        topic: str
    ) -> Dict[str, Any]:
        """Use LLM to analyze relationships."""
        
        prompt = f"""Analyze research relationships for topic: "{topic}"

Papers:
{paper_context}

Citation Tree Summary:
- Total unique papers: {citation_tree.get('total_unique_papers', 0)}
- Root papers: {len(citation_tree.get('root_papers', []))}

{RELATIONSHIP_ANALYSIS_PROMPT}"""
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2048
            )
            
            text = response.text.strip()
            import re
            # Find JSON block
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                text = json_match.group(1)
            
            relationships = json.loads(text)
            
        except Exception as e:
            logger.debug(f"LLM analysis failed: {e}, using template")
            relationships = self._create_default_relationships()
        
        return relationships
    
    def _enhance_with_citations(
        self,
        relationships: Dict[str, Any],
        citation_tree: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance relationships with citation-based analysis."""
        
        # Add citation strength analysis
        citation_graph = citation_tree.get('citation_graph', {})
        
        relationships["citation_analysis"] = {
            "most_cited": sorted(
                [(id, len(info.get('cited_by', []))) for id, info in citation_graph.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "most_citing": sorted(
                [(id, len(info.get('cites', []))) for id, info in citation_graph.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "network_density": len(citation_graph)
        }
        
        return relationships
    
    def _extract_hierarchy(self, citation_tree: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parent-child relationships from citation tree."""
        
        hierarchy = {
            "root_to_children": {},
            "parent_to_children": {},
            "depth_distribution": {}
        }
        
        citation_graph = citation_tree.get('citation_graph', {})
        
        # Build parent-child relationships
        for paper_id, info in citation_graph.items():
            depth = info.get('depth', 0)
            
            # Track depth distribution
            if depth not in hierarchy["depth_distribution"]:
                hierarchy["depth_distribution"][depth] = 0
            hierarchy["depth_distribution"][depth] += 1
            
            # Track parent-child
            parent = info.get('parent')
            if parent:
                if parent not in hierarchy["parent_to_children"]:
                    hierarchy["parent_to_children"][parent] = []
                hierarchy["parent_to_children"][parent].append(paper_id)
        
        return hierarchy
    
    def _create_default_relationships(self) -> Dict[str, Any]:
        """Create template relationships when LLM is unavailable."""
        
        return {
            "feature_relationships": [],
            "citation_hierarchy": {
                "foundational_papers": [],
                "derivative_papers": [],
                "cluster_analysis": {}
            },
            "research_progression": "Relationships analysis pending",
            "key_connections": [],
            "analysis_status": "incomplete"
        }
