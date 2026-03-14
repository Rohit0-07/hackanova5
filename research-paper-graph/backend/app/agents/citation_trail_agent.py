"""Citation Trail Agent — Builds the complete citation tree from root papers."""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from loguru import logger
import asyncio

from app.agents.orchestrator import BaseAgent, PipelineState


class CitationTrailAgent(BaseAgent):
    """Follows citation chains to build a complete citation tree from root papers."""
    
    def __init__(self, max_depth: int = 3, llm_client=None):
        super().__init__("CitationTrailAgent", llm_client)
        self.max_depth = max_depth
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Build citation tree from papers."""
        
        if not state.papers:
            return self._add_error(state, "No papers available to build citation trail")
        
        # Use max_depth from state if available
        max_depth = getattr(state, 'max_depth', self.max_depth)
        
        self._log_step(f"Building citation tree for {len(state.papers)} root papers, max depth: {max_depth}")
        
        try:
            from app.services import research_crawler
            
            citation_tree = {
                "root_papers": [],
                "citation_graph": {},
                "depth_levels": {},
                "total_unique_papers": 0
            }
            
            # For each root paper, build citation trail
            for paper in state.papers:
                paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
                
                # Fetch full data from Semantic Scholar to get actual citations/references
                try:
                    # Semantic Scholar lookup using ArXiv ID if available
                    external_id = None
                    if paper.get('identifier', {}).get('arxiv_id'):
                        external_id = f"ArXiv:{paper['identifier']['arxiv_id']}"
                    elif paper.get('identifier', {}).get('doi'):
                        external_id = f"DOI:{paper['identifier']['doi']}"
                    
                    if external_id:
                        s2_paper = await research_crawler.semantic_scholar.fetch_paper(external_id)
                        # Add references and citations to the paper dict
                        paper['references'] = await research_crawler.semantic_scholar.fetch_references(external_id, limit=10)
                        paper['cited_by'] = await research_crawler.semantic_scholar.fetch_citations(external_id, limit=10)
                except Exception as e:
                    logger.debug(f"Failed to fetch citation data for {paper_id} from S2: {e}")

                self._log_step(f"Tracing citations for: {paper.get('title', 'Unknown')[:60]}")
                
                try:
                    # Build tree for this paper
                    tree = await self._build_citation_tree(
                        paper,
                        depth=0,
                        visited=set(),
                        crawler=research_crawler,
                        max_depth=max_depth
                    )
                    
                    citation_tree["root_papers"].append({
                        "id": paper_id,
                        "title": paper.get('title'),
                        "url": paper.get('url'),
                        "citation_tree": tree
                    })
                    
                    # Update graph structure
                    await self._update_graph(citation_tree["citation_graph"], tree)
                    
                    # Update state incrementally
                    state.citation_tree = citation_tree
                    
                    # Also build graph nodes incrementally
                    try:
                        from app.agents.graph_builder_agent import GraphBuilderAgent
                        graph_agent = GraphBuilderAgent(llm_client=self.llm_client)
                        await graph_agent.execute(state)
                    except Exception as ge:
                        logger.warning(f"Incremental graph update (citation) failed: {ge}")

                    self._update_state(state) # Push partial results
                    
                except Exception as e:
                    logger.warning(f"Error building tree for paper: {e}")
                    state.errors.append(f"Citation tree error: {str(e)}")
            
            # Analyze depth levels
            citation_tree["depth_levels"] = self._analyze_depths(citation_tree["citation_graph"])
            citation_tree["total_unique_papers"] = len(citation_tree["citation_graph"])
            
            state.citation_tree = citation_tree
            self._log_step(f"Citation tree complete: {citation_tree['total_unique_papers']} unique papers found")
            
        except Exception as e:
            logger.exception(f"CitationTrailAgent failed: {e}")
            return self._add_error(state, f"Failed to build citation trail: {str(e)}")
        
        return state
    
    async def _build_citation_tree(
        self,
        paper: Dict[str, Any],
        depth: int,
        visited: Set[str],
        crawler: Any = None,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """Recursively build citation tree for a paper."""
        
        paper_id = paper.get('id') or paper.get('title', '')[:50]
        
        if depth > max_depth or paper_id in visited:
            return {"id": paper_id, "title": paper.get('title'), "depth": depth}
        
        visited.add(paper_id)
        
        # If we have crawler and this is a deeper level, try to fetch more data
        if crawler and depth > 0 and not paper.get('references'):
            try:
                external_id = None
                if paper.get('identifier', {}).get('arxiv_id'):
                    external_id = f"ArXiv:{paper['identifier']['arxiv_id']}"
                elif paper.get('identifier', {}).get('doi'):
                    external_id = f"DOI:{paper['identifier']['doi']}"
                
                if external_id:
                    paper['references'] = await crawler.semantic_scholar.fetch_references(external_id, limit=5)
                    paper['cited_by'] = await crawler.semantic_scholar.fetch_citations(external_id, limit=5)
            except Exception:
                pass

        tree = {
            "id": paper_id,
            "title": paper.get('title'),
            "url": paper.get('url'),
            "authors": paper.get('authors', []),
            "year": paper.get('year'),
            "depth": depth,
            "citations": [],
            "cited_by": []
        }
        
        try:
            # Get references this paper cites
            references = paper.get('references', [])
            for ref in references[: 5]:  # Limit to avoid explosion
                ref_data = ref
                if not isinstance(ref, dict):
                    # Handle if it's a PaperMetadata object from S2
                    ref_data = {
                        "id": ref.identifier.arxiv_id or ref.identifier.doi or ref.identifier.hash,
                        "title": ref.title,
                        "authors": ref.authors,
                        "year": ref.publication_date.year if ref.publication_date else None,
                        "url": ref.url,
                        "identifier": {
                            "arxiv_id": ref.identifier.arxiv_id,
                            "doi": ref.identifier.doi,
                            "hash": ref.identifier.hash
                        }
                    }
                
                ref_tree = await self._build_citation_tree(ref_data, depth + 1, visited, crawler, max_depth)
                tree["citations"].append(ref_tree)
            
            # Get papers that cite this paper (cited_by)
            cited_by = paper.get('cited_by', [])
            for citing_paper in cited_by[: 5]:
                citing_data = citing_paper
                if not isinstance(citing_paper, dict):
                    citing_data = {
                        "id": citing_paper.identifier.arxiv_id or citing_paper.identifier.doi or citing_paper.identifier.hash,
                        "title": citing_paper.title,
                        "authors": citing_paper.authors,
                        "year": citing_paper.publication_date.year if citing_paper.publication_date else None,
                        "url": citing_paper.url,
                        "identifier": {
                            "arxiv_id": citing_paper.identifier.arxiv_id,
                            "doi": citing_paper.identifier.doi,
                            "hash": citing_paper.identifier.hash
                        }
                    }
                
                citing_tree = await self._build_citation_tree(citing_data, depth + 1, visited, crawler, max_depth)
                tree["cited_by"].append(citing_tree)
        
        except Exception as e:
            logger.debug(f"Error building subtree for {paper_id}: {e}")
        
        return tree
    
    async def _update_graph(self, graph: Dict[str, Any], tree: Dict[str, Any]):
        """Update citation graph with tree information."""
        
        stack = [tree]
        visited = set()
        
        while stack:
            node = stack.pop()
            node_id = node.get('id')
            
            if not node_id or node_id in visited:
                continue
            
            visited.add(node_id)
            
            if node_id not in graph:
                graph[node_id] = {
                    "title": node.get('title'),
                    "url": node.get('url'),
                    "year": node.get('year'),
                    "authors": node.get('authors', []),
                    "depth": node.get('depth', 0),
                    "cites": [],
                    "cited_by": []
                }
            
            # Add citations
            for citation in node.get('citations', []):
                cite_id = citation.get('id')
                if cite_id:
                    if cite_id not in graph[node_id]["cites"]:
                        graph[node_id]["cites"].append(cite_id)
                    stack.append(citation)
            
            # Add cited_by
            for citing in node.get('cited_by', []):
                citing_id = citing.get('id')
                if citing_id:
                    if citing_id not in graph[node_id]["cited_by"]:
                        graph[node_id]["cited_by"].append(citing_id)
                    stack.append(citing)
    
    def _analyze_depths(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze papers by depth in citation tree."""
        
        depths = {}
        
        for paper_id, info in graph.items():
            depth = info.get('depth', 0)
            if depth not in depths:
                depths[depth] = []
            depths[depth].append(paper_id)
        
        return {
            "by_level": depths,
            "counts": {str(d): len(papers) for d, papers in depths.items()}
        }
