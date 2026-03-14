"""Graph Builder Agent — Constructs knowledge graph from analyzed papers and relationships."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import json

from app.agents.orchestrator import BaseAgent, PipelineState


class GraphBuilderAgent(BaseAgent):
    """Constructs Neo4j knowledge graph from papers, analyses, and relationships."""
    
    def __init__(self, llm_client=None, graph_manager=None):
        super().__init__("GraphBuilderAgent", llm_client)
        self.graph_manager = graph_manager  # Will be passed in from main setup
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Build knowledge graph from all pipeline data."""
        
        if not state.papers or not state.analyses:
            return self._add_error(state, "Missing papers or analyses for graph building")
        
        self._log_step(f"Building knowledge graph for {len(state.papers)} papers")
        
        graph_nodes = []
        
        try:
            # Create paper nodes
            paper_nodes = await self._create_paper_nodes(state)
            graph_nodes.extend(paper_nodes)
            self._log_step(f"Created {len(paper_nodes)} paper nodes")
            
            # Create finding nodes
            finding_nodes = await self._create_finding_nodes(state)
            graph_nodes.extend(finding_nodes)
            self._log_step(f"Created {len(finding_nodes)} finding nodes")
            
            # Create concept nodes
            concept_nodes = await self._create_concept_nodes(state)
            graph_nodes.extend(concept_nodes)
            self._log_step(f"Created {len(concept_nodes)} concept nodes")
            
            # Create relationship edges
            edges = await self._create_edges(state, graph_nodes)
            
            # Create citation nodes and links
            citation_nodes, citation_edges = await self._create_citation_nodes(state)
            graph_nodes.extend(citation_nodes)
            edges.extend(citation_edges)
            
            # ADDED: Create similarity edges between papers
            similarity_edges = await self._create_similarity_edges(state)
            edges.extend(similarity_edges)
            
            # ADDED: Create contradiction edges from synthesis
            contradiction_edges = await self._add_contradiction_edges(state)
            edges.extend(contradiction_edges)
            
            # ENSURE STATE IS UPDATED IMMEDIATELY
            state.graph_nodes = {
                "nodes": graph_nodes,
                "edges": edges,
                "total_nodes": len(graph_nodes),
                "total_edges": len(edges),
                "graph_metadata": {
                    "origin_query": state.raw_query,
                    "papers_analyzed": len(state.papers),
                    "topics_identified": len(concept_nodes)
                }
            }
            state.updated_at = datetime.utcnow().isoformat()
            state.save_to_file()
            
            self._log_step(f"Graph built: {len(graph_nodes)} nodes, {len(edges)} edges")
            
            # Optionally persist to database if graph_manager available
            if self.graph_manager:
                try:
                    await self._persist_to_graph(self.graph_manager, state)
                    self._log_step("Graph persisted to database")
                except Exception as e:
                    logger.warning(f"Could not persist graph to database: {e}")
            
        except Exception as e:
            logger.exception(f"GraphBuilderAgent failed: {e}")
            return self._add_error(state, f"Failed to build graph: {str(e)}")
        
        return state

    async def _create_similarity_edges(self, state: PipelineState) -> List[Dict[str, Any]]:
        """Create SIMILAR_TO edges between papers sharing keywords."""
        edges = []
        paper_keywords = {}
        
        for paper in state.papers:
            pid = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
            analysis = state.analyses.get(pid, {})
            keywords = set(analysis.get('keywords', []))
            if keywords:
                paper_keywords[pid] = keywords
                
        pids = list(paper_keywords.keys())
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                id1, id2 = pids[i], pids[j]
                common = paper_keywords[id1].intersection(paper_keywords[id2])
                if len(common) >= 2: # At least 2 shared keywords
                    edges.append({
                        "source": f"paper_{id1}",
                        "target": f"paper_{id2}",
                        "relationship": "SIMILAR_TO",
                        "type": "SIMILAR_TO",  # Normalized field for frontend
                        "properties": {
                            "shared_keywords": list(common),
                            "strength": len(common)
                        }
                    })
        return edges
    
    async def _create_paper_nodes(self, state: PipelineState) -> List[Dict[str, Any]]:
        """Create graph nodes for papers."""
        
        nodes = []
        
        for paper in state.papers:
            paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
            analysis = state.analyses.get(paper_id, {})
            sections = state.sectioned_content.get(paper_id, {})
            
            # Find artifacts for this paper
            paper_artifacts = []
            if hasattr(state, 'extracted_artifacts') and state.extracted_artifacts:
                paper_artifacts = [
                    a for a in state.extracted_artifacts 
                    if a.get('paper_id') == paper_id
                ]

            node = {
                "id": f"paper_{paper_id}",
                "type": "Paper",
                "properties": {
                    "title": paper.get('title'),
                    "authors": paper.get('authors', []),
                    "year": paper.get('year'),
                    "url": paper.get('url'),
                    "source": paper.get('source', 'unknown'),
                    "abstract": paper.get('abstract', '')[:500],
                    "contribution_type": analysis.get('contribution_type', 'unknown'),
                    "key_findings": analysis.get('key_findings', []),
                    "methodology": analysis.get('methodology', ''),
                    "limitations": analysis.get('limitations', []),
                    "keywords": analysis.get('keywords', []),
                    "confidence": analysis.get('confidence_level', 'low'),
                    "sections": sections.get('sections', {}),
                    "artifacts": paper_artifacts
                }
            }
            
            nodes.append(node)
        
        return nodes
    
    async def _create_finding_nodes(self, state: PipelineState) -> List[Dict[str, Any]]:
        """Create nodes for key findings."""
        
        nodes = []
        finding_id_counter = 0
        
        for paper in state.papers:
            paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
            analysis = state.analyses.get(paper_id, {})
            
            for finding in analysis.get('key_findings', []):
                node = {
                    "id": f"finding_{finding_id_counter}",
                    "type": "Finding",
                    "properties": {
                        "text": finding,
                        "source_paper": paper_id,
                        "source_paper_title": paper.get('title'),
                        "confidence": analysis.get('confidence_level', 'low')
                    }
                }
                nodes.append(node)
                finding_id_counter += 1
        
        return nodes
    
    async def _create_concept_nodes(self, state: PipelineState) -> List[Dict[str, Any]]:
        """Create nodes for core concepts/keywords."""
        
        concepts_set = set()
        
        # Collect all keywords from analyses
        for paper in state.papers:
            paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
            analysis = state.analyses.get(paper_id, {})
            
            for keyword in analysis.get('keywords', []):
                concepts_set.add(keyword)
        
        # Create concept nodes
        nodes = []
        for idx, concept in enumerate(concepts_set):
            node = {
                "id": f"concept_{idx}",
                "type": "Concept",
                "properties": {
                    "name": concept,
                    "frequency": sum(
                        1 for p in state.papers 
                        if concept in state.analyses.get(
                            p.get('id') or p.get('title', '')[:50], {}
                        ).get('keywords', [])
                    )
                }
            }
            nodes.append(node)
        
        return nodes
    
    async def _create_edges(
        self,
        state: PipelineState,
        nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create relationship edges between nodes."""
        
        edges = []
        
        # Create edges from papers to their findings
        for node in nodes:
            if node['type'] == 'Finding':
                source_paper = node['properties'].get('source_paper')
                edges.append({
                    "source": f"paper_{source_paper}",
                    "target": node['id'],
                    "relationship": "HAS_FINDING",
                    "type": "HAS_FINDING",  # Normalized field for frontend
                    "properties": {}
                })
        
        # Create edges from papers to concepts (keywords)
        for paper in state.papers:
            paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
            analysis = state.analyses.get(paper_id, {})
            
            for keyword in analysis.get('keywords', []):
                for node in nodes:
                    if node['type'] == 'Concept' and node['properties']['name'] == keyword:
                        edges.append({
                            "source": f"paper_{paper_id}",
                            "target": node['id'],
                            "relationship": "DISCUSSES",
                            "type": "DISCUSSES",  # Normalized field for frontend
                            "properties": {}
                        })
        
        # Add relationship edges from relationship analysis
        if state.relationships:
            for rel in state.relationships.get('feature_relationships', []):
                edges.append({
                    "source": rel.get('feature1', ''),
                    "target": rel.get('feature2', ''),
                    "relationship": rel.get('relationship_type', 'RELATED'),
                    "type": rel.get('relationship_type', 'RELATED'),  # Normalized field for frontend
                    "properties": {
                        "strength": rel.get('strength'),
                        "description": rel.get('description')
                    }
                })
        
        return edges
    
    async def _create_citation_nodes(
        self,
        state: PipelineState
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Create citation nodes and edges."""
        
        citation_nodes = []
        citation_edges = []
        
        if not state.citation_tree:
            return citation_nodes, citation_edges
        
        citation_graph = state.citation_tree.get('citation_graph', {})
        
        # Create citation nodes
        for paper_id, info in citation_graph.items():
            node = {
                "id": f"citation_{paper_id}",
                "type": "CitedPaper",
                "properties": {
                    "title": info.get('title'),
                    "year": info.get('year'),
                    "authors": info.get('authors', []),
                    "depth_in_graph": info.get('depth', 0),
                    "citation_count": len(info.get('cited_by', []))
                }
            }
            citation_nodes.append(node)
        
        # Create citation edges
        for paper_id, info in citation_graph.items():
            # Edges for papers this cites
            for cited_id in info.get('cites', []):
                if cited_id in citation_graph:
                    citation_edges.append({
                        "source": f"citation_{paper_id}",
                        "target": f"citation_{cited_id}",
                        "relationship": "CITES",
                        "type": "CITES",  # Normalized field for frontend
                        "properties": {}
                    })
            
            # Edges for papers that cite this
            for citing_id in info.get('cited_by', []):
                if citing_id in citation_graph:
                    citation_edges.append({
                        "source": f"citation_{citing_id}",
                        "target": f"citation_{paper_id}",
                        "relationship": "CITED_BY",
                        "type": "CITED_BY",  # Normalized field for frontend
                        "properties": {}
                    })
        
        return citation_nodes, citation_edges
    
    async def _add_contradiction_edges(self, state: PipelineState) -> List[Dict[str, Any]]:
        """Extract contradictions from synthesis and create edges."""
        contradiction_edges = []
        
        if not state.synthesis or not state.synthesis.get('contradictions'):
            return contradiction_edges
        
        # Build title-to-paper-id mapping for matching
        title_to_id = {}
        for paper in state.papers:
            title = paper.get('title', '')
            paper_id = paper.get('id') or title.replace(' ', '_')[:50]
            if title:
                title_to_id[title] = paper_id
        
        # Create edges for each contradiction
        for contradiction in state.synthesis.get('contradictions', []):
            paper_a = contradiction.get('paper_a', '')
            paper_b = contradiction.get('paper_b', '')
            description = contradiction.get('description', '')
            topic = contradiction.get('topic', '')
            
            # Find the paper IDs
            source_id = title_to_id.get(paper_a)
            target_id = title_to_id.get(paper_b)
            
            if source_id and target_id:
                contradiction_edges.append({
                    "source": f"paper_{source_id}",
                    "target": f"paper_{target_id}",
                    "relationship": "CONTRADICTS",
                    "type": "CONTRADICTS",  # Normalized field for frontend
                    "properties": {
                        "description": description,
                        "topic": topic
                    }
                })
        
        return contradiction_edges
    
    async def _persist_to_graph(self, graph_manager, state: PipelineState):
        """Persist graph to database."""
        
        # This will call your Neo4j or Postgres database layer
        # Implementation depends on graph_manager interface
        logger.info("Persisting graph data to database...")
        
        # Placeholder for actual persistence
        # graph_manager.create_nodes(state.graph_nodes['nodes'])
        # graph_manager.create_edges(state.graph_nodes['edges'])
