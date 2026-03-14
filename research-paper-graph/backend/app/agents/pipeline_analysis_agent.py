"""Analysis Agent (Pipeline Version) — Analyzes each paper in the pipeline."""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.agents.orchestrator import BaseAgent, PipelineState
from app.agents.analysis_agent import AnalysisAgent as LegacyAnalysisAgent


class PipelineAnalysisAgent(BaseAgent):
    """Pipeline-integrated analysis agent for extracting findings from papers."""
    
    def __init__(self, llm_client=None):
        super().__init__("PipelineAnalysisAgent", llm_client)
        self.legacy_agent = LegacyAnalysisAgent(llm_client)
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Analyze all papers in the pipeline."""
        
        if not state.papers:
            return self._add_error(state, "No papers available for analysis")
        
        self._log_step(f"Analyzing {len(state.papers)} papers")
        
        analyses = {}
        
        try:
            from app.services import research_crawler
            from app.services.parser.paper_parser import PaperParser
            
            parser = PaperParser(llm_provider=self.llm_client.provider_name)
            
            for paper in state.papers:
                paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
                
                try:
                    # Get paper content
                    paper_text = paper.get('content') or paper.get('abstract', '')
                    paper_title = paper.get('title', '')
                    
                    # If content is missing, try to download and parse PDF
                    if (not paper_text or len(paper_text) < 500) and paper.get('pdf_url'):
                        self._log_step(f"Content missing for {paper_id}, attempting to download PDF...")
                        try:
                            pdf_path = await research_crawler.arxiv.download_pdf(
                                paper['pdf_url'], 
                                paper_id, 
                                "./data/papers"
                            )
                            parsed_content = await parser.parse_paper(pdf_path, paper_id)

                            # Build a richer content string from parsed sections to improve downstream analysis
                            sections = [
                                parsed_content.abstract,
                                parsed_content.introduction,
                                parsed_content.methodology,
                                parsed_content.results,
                                parsed_content.conclusion,
                            ]

                            # Include any other detected sections (e.g., Discussion, Related Work)
                            if hasattr(parsed_content, 'sections') and isinstance(parsed_content.sections, dict):
                                for sec in parsed_content.sections.values():
                                    sec_text = getattr(sec, 'content', sec) if sec is not None else None
                                    if isinstance(sec_text, str) and sec_text.strip():
                                        sections.append(sec_text)

                            paper_text = "\n\n".join([s for s in sections if s])

                            # Persist enriched content for use by later agents (section extractor, chat, etc.)
                            paper['content'] = paper_text
                        except Exception as e:
                            logger.warning(f"Failed to download/parse PDF for {paper_id}: {e}")
                    
                    if not paper_text:
                        self._log_step(f"Skipping paper {paper_id}: no content available")
                        analyses[paper_id] = {"status": "no_content"}
                        continue
                    
                    # Attach artifacts to paper for frontend display
                    if state.extracted_artifacts:
                        paper['artifacts'] = [
                            a for a in state.extracted_artifacts 
                            if a.get('paper_id') == paper_id
                        ]
                    
                    # Analyze the paper
                    analysis = await self.legacy_agent.analyze_paper(
                        paper_text=paper_text,
                        paper_title=paper_title,
                        paper_id=paper_id
                    )
                    
                    analyses[paper_id] = analysis
                    state.analyses = analyses  # Update state immediately
                    
                    # Update graph incrementally
                    try:
                        from app.agents.graph_builder_agent import GraphBuilderAgent
                        graph_agent = GraphBuilderAgent(llm_client=self.llm_client)
                        await graph_agent.execute(state)
                    except Exception as ge:
                        logger.warning(f"Incremental graph update (analysis) failed: {ge}")

                    self._update_state(state) # Push results after each analysis
                    
                    self._log_step(f"Analyzed: {paper_title[:50]}")
                
                except Exception as e:
                    logger.warning(f"Error analyzing paper {paper_id}: {e}")
                    state.errors.append(f"Analysis error for {paper_id}: {str(e)}")
                    analyses[paper_id] = {"status": "error", "error": str(e)}
            
            state.analyses = analyses
            self._log_step(f"Completed analysis for {len([a for a in analyses.values() if 'status' not in a or a['status'] == 'complete'])} papers")
            
        except Exception as e:
            logger.exception(f"PipelineAnalysisAgent failed: {e}")
            return self._add_error(state, f"Failed to analyze papers: {str(e)}")
        
        return state
