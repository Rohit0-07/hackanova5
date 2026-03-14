"""Paper Finder Agent — Finds research papers from multiple sources based on refined query."""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from loguru import logger
import asyncio

from app.agents.orchestrator import BaseAgent, PipelineState
from app.services.crawler.models import PaperMetadata

if TYPE_CHECKING:
    from app.services.crawler.crawler import ResearchCrawler


class PaperFinderAgent(BaseAgent):
    """Searches multiple academic sources for papers matching the refined query."""
    
    def __init__(self, crawler: Optional['ResearchCrawler'] = None, llm_client=None):
        super().__init__("PaperFinderAgent", llm_client)
        # Import here to avoid circular imports
        if crawler is None:
            from app.services.crawler.crawler import ResearchCrawler
            self.crawler = ResearchCrawler()
        else:
            self.crawler = crawler
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Find papers based on refined query."""
        
        if state.refined_query is None:
            return self._add_error(state, "No refined query available")
        
        self._log_step(f"Finding papers for {len(state.refined_query.get('refined_queries', []))} queries")
        
        papers: List[Dict[str, Any]] = []
        
        try:
            queries = state.refined_query.get('refined_queries', [state.raw_query])
            
            # Search each query across sources
            for query in queries:
                if len(papers) >= state.max_papers:
                    self._log_step(f"Reached max_papers limit ({state.max_papers}), stopping search")
                    break
                    
                self._log_step(f"Searching: '{query}'")
                
                try:
                    # Crawl from different sources
                    # Distribute remaining budget among sources
                    remaining_budget = state.max_papers - len(papers)
                    source_papers = await self._search_query(query, limit=max(1, remaining_budget))
                    
                    # Deduplicate before adding
                    for p in source_papers:
                        if len(papers) >= state.max_papers:
                            break
                        if not any(existing['title'].lower() == p['title'].lower() for existing in papers):
                            papers.append(p)
                            
                    state.papers = papers
                    # Orchestrator will persist state; no need to call _update_state here
                    
                    self._log_step(f"Found {len(source_papers)} papers for query: '{query[:50]}'")
                
                except Exception as e:
                    logger.warning(f"Error searching query '{query}': {e}")
                    state.errors.append(f"Error searching '{query}': {str(e)}")
            
            # Deduplicate papers
            papers = self._deduplicate_papers(papers)
            
            state.papers = papers
            self._log_step(f"Total unique papers found: {len(papers)}")
            
        except Exception as e:
            logger.exception(f"PaperFinderAgent failed: {e}")
            state.status = "failed"
            return self._add_error(state, f"Failed to find papers: {str(e)}")
        
        return state
    
    async def _search_query(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search a single query across available sources."""
        
        papers = []
        try:
            logger.info(f"Searching for: {query}")
            if not getattr(self, "crawler", None):
                from app.services.crawler.crawler import ResearchCrawler
                self.crawler = ResearchCrawler()
            
            # Search ArXiv
            try:
                arxiv_limit = max(1, limit // 2)
                arxiv_papers = await self.crawler.arxiv.search(query, max_results=arxiv_limit)
                for p in arxiv_papers:
                    pid = p.identifier.arxiv_id or p.identifier.doi or p.identifier.hash
                    papers.append({
                        "id": pid,
                        "title": p.title,
                        "authors": p.authors,
                        "year": p.publication_date.year if p.publication_date else None,
                        "abstract": p.abstract,
                        "url": p.url,
                        "pdf_url": p.pdf_url,
                        "source": "arxiv",
                        "identifier": {
                            "arxiv_id": p.identifier.arxiv_id,
                            "doi": p.identifier.doi,
                            "hash": p.identifier.hash
                        }
                    })
            except Exception as e:
                logger.warning(f"ArXiv search failed: {e}")

            # Search Semantic Scholar
            try:
                s2_limit = max(1, limit - len(papers))
                if s2_limit > 0:
                    s2_papers = await self.crawler.s2.search(query, max_results=s2_limit)
                    for p in s2_papers:
                        pid = p.identifier.arxiv_id or p.identifier.doi or p.identifier.hash
                        papers.append({
                            "id": pid,
                            "title": p.title,
                            "authors": p.authors,
                            "year": p.publication_date.year if p.publication_date else None,
                            "abstract": p.abstract,
                            "url": p.url,
                            "pdf_url": p.pdf_url,
                            "source": "semantic_scholar",
                            "identifier": {
                                "arxiv_id": p.identifier.arxiv_id,
                                "doi": p.identifier.doi,
                                "hash": p.identifier.hash
                            }
                        })
            except Exception as e:
                logger.warning(f"Semantic Scholar search failed: {e}")

        except Exception as e:
            logger.error(f"Error during search: {e}")
        
        return papers
    
    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers using title and year."""
        
        seen = set()
        unique_papers = []
        
        for paper in papers:
            key = (paper.get('title', '').lower(), paper.get('year', ''))
            if key not in seen:
                seen.add(key)
                unique_papers.append(paper)
        
        logger.info(f"Deduplicated {len(papers)} papers to {len(unique_papers)}")
        return unique_papers
