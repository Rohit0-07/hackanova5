"""Content Extractor Agent — Extracts images, tables, diagrams from papers."""

from typing import Dict, Any, List, Optional
from loguru import logger
from pathlib import Path

from app.agents.orchestrator import BaseAgent, PipelineState


class ContentExtractorAgent(BaseAgent):
    """Extracts structured content (images, tables, diagrams) from research papers."""
    
    def __init__(self, llm_client=None, artifacts_dir: Optional[Path] = None):
        super().__init__("ContentExtractorAgent", llm_client)
        self.artifacts_dir = artifacts_dir or Path("./data/artifacts")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Extract artifacts from papers."""
        
        if not state.papers:
            return self._add_error(state, "No papers available for content extraction")
        
        self._log_step(f"Extracting content from {len(state.papers)} papers")
        
        extracted_artifacts = []
        
        try:
            for paper in state.papers:
                paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
                
                try:
                    # Extract different types of content
                    artifacts = await self._extract_paper_content(paper, paper_id)
                    extracted_artifacts.extend(artifacts)
                    
                    self._log_step(f"Extracted {len(artifacts)} artifacts from {paper.get('title', 'Unknown')[:50]}")
                
                except Exception as e:
                    logger.warning(f"Error extracting content from paper {paper_id}: {e}")
                    state.errors.append(f"Content extraction error for {paper_id}: {str(e)}")
            
            state.extracted_artifacts = extracted_artifacts
            self._log_step(f"Total artifacts extracted: {len(extracted_artifacts)}")
            
        except Exception as e:
            logger.exception(f"ContentExtractorAgent failed: {e}")
            return self._add_error(state, f"Failed to extract content: {str(e)}")
        
        return state
    
    async def _extract_paper_content(
        self,
        paper: Dict[str, Any],
        paper_id: str
    ) -> List[Dict[str, Any]]:
        """Extract all content types from a paper."""
        
        artifacts = []
        
        # Extract tables
        tables = await self._extract_tables(paper)
        for table in tables:
            artifacts.append({
                "type": "table",
                "paper_id": paper_id,
                "paper_title": paper.get('title'),
                "content": table,
                "location": table.get("location")
            })
        
        # Extract figures/images
        figures = await self._extract_figures(paper)
        for figure in figures:
            artifacts.append({
                "type": "figure",
                "paper_id": paper_id,
                "paper_title": paper.get('title'),
                "content": figure,
                "location": figure.get("location")
            })
        
        # Extract diagrams
        diagrams = await self._extract_diagrams(paper)
        for diagram in diagrams:
            artifacts.append({
                "type": "diagram",
                "paper_id": paper_id,
                "paper_title": paper.get('title'),
                "content": diagram,
                "location": diagram.get("location")
            })
        
        # Extract key equations/formulas
        equations = await self._extract_equations(paper)
        for equation in equations:
            artifacts.append({
                "type": "equation",
                "paper_id": paper_id,
                "paper_title": paper.get('title'),
                "content": equation,
                "location": equation.get("location")
            })
        
        return artifacts
    
    async def _extract_tables(self, paper: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tables from paper."""
        
        tables = []
        paper_content = paper.get('content', '')
        
        # Use LLM to identify and extract tables from text
        if paper_content:
            try:
                prompt = f"""Extract all tables from this paper content. Format each table as structured JSON with columns and rows.

Paper excerpt:
{paper_content[:4000]}

Output a JSON list of table objects with: title, columns, rows, caption, location"""
                
                # This would call LLM if integrated
                # For now, return mock structure
                
            except Exception as e:
                logger.debug(f"Error extracting tables: {e}")
        
        # Check if paper has attached table data
        if 'tables' in paper:
            tables.extend(paper['tables'])
        
        return tables
    
    async def _extract_figures(self, paper: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract figures/images from paper."""
        
        figures = []
        
        # Check if paper has figure URLs or embedded images
        if 'figures' in paper:
            figures.extend(paper['figures'])
        
        if 'images' in paper:
            figures.extend(paper['images'])
        
        # Try to extract figure references from text
        paper_content = paper.get('content', '')
        if paper_content:
            try:
                # Use LLM to identify figure references
                prompt = f"""Identify all figure references in this paper. Return locations and descriptions.

Paper excerpt:
{paper_content[:4000]}

Format: JSON list with {{"number": "Fig X", "caption": "...", "location": "page X"}}"""
                
                # This would call LLM if integrated
                
            except Exception as e:
                logger.debug(f"Error extracting figure references: {e}")
        
        return figures
    
    async def _extract_diagrams(self, paper: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract diagrams/visual structures from paper."""
        
        diagrams = []
        paper_content = paper.get('content', '')
        
        if paper_content:
            try:
                prompt = f"""Identify and extract diagrams, flowcharts, architecture diagrams from this paper.

Paper excerpt:
{paper_content[:4000]}

Output: JSON list with diagram descriptions, type, and key components"""
                
                # This would call LLM if integrated
                
            except Exception as e:
                logger.debug(f"Error extracting diagrams: {e}")
        
        return diagrams
    
    async def _extract_equations(self, paper: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract mathematical equations from paper."""
        
        equations = []
        paper_content = paper.get('content', '')
        
        if paper_content:
            try:
                prompt = f"""Extract all mathematical equations, formulas, and their LaTeX representations.

Paper excerpt:
{paper_content[:4000]}

Output: JSON list with {{"equation": "...", "latex": "...", "description": "...", "location": "..."}}"""
                
                # This would call LLM if integrated
                
            except Exception as e:
                logger.debug(f"Error extracting equations: {e}")
        
        return equations
