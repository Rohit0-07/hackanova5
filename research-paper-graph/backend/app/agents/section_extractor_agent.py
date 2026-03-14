"""Section Extractor Agent — Extracts relevant sections from papers for each research topic."""

from typing import Dict, Any, List, Optional
from loguru import logger
import json

from app.agents.orchestrator import BaseAgent, PipelineState


SECTION_EXTRACTION_PROMPT = """You are an expert research analyst. Given a research paper and a research topic, extract the most relevant sections for that topic.

Focus on:
1. Abstract and Introduction (context)
2. Methodology (implementation approach)
3. Results/Findings (key results)
4. Discussion (interpretation and implications)
5. Related Work (context with other research)
6. Conclusion (main takeaways)

Output valid JSON with structure:
{
  "abstract": "extracted abstract",
  "introduction": "key intro points relevant to topic",
  "methodology": "relevant methods",
  "results": "relevant results",
  "discussion": "relevant discussion",
  "related_work": "relevant citations and comparisons",
  "conclusion": "extracted conclusion",
  "key_quotes": ["quote1", "quote2"],
  "relevance_score": 0.95
}

Only include sections that exist. Be concise but comprehensive."""


class SectionExtractorAgent(BaseAgent):
    """Extracts and organizes relevant sections from papers."""
    
    def __init__(self, llm_client=None):
        super().__init__("SectionExtractorAgent", llm_client)
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """Extract relevant sections from papers based on their analyses."""
        
        if not state.papers or not state.analyses:
            return self._add_error(state, "No papers or analyses available for section extraction")
        
        self._log_step(f"Extracting sections from {len(state.papers)} papers")
        
        sectioned_content = {}
        
        try:
            for paper in state.papers:
                paper_id = paper.get('id') or paper.get('title', '').replace(' ', '_')[:50]
                
                # Get analysis for this paper
                analysis = state.analyses.get(paper_id, {})
                
                try:
                    sections = await self._extract_sections(
                        paper,
                        paper_id,
                        analysis,
                        state.raw_query
                    )
                    
                    sectioned_content[paper_id] = {
                        "title": paper.get('title'),
                        "source_url": paper.get('url'),
                        "sections": sections,
                        "key_findings_summary": analysis.get('key_findings', [])
                    }
                    
                    self._log_step(f"Extracted sections from: {paper.get('title', 'Unknown')[:50]}")
                
                except Exception as e:
                    logger.warning(f"Error extracting sections from paper {paper_id}: {e}")
                    state.errors.append(f"Section extraction error for {paper_id}: {str(e)}")
            
            state.sectioned_content = sectioned_content
            self._log_step(f"Sections extracted for {len(sectioned_content)} papers")
            
        except Exception as e:
            logger.exception(f"SectionExtractorAgent failed: {e}")
            return self._add_error(state, f"Failed to extract sections: {str(e)}")
        
        return state
    
    async def _extract_sections(
        self,
        paper: Dict[str, Any],
        paper_id: str,
        analysis: Dict[str, Any],
        topic: str
    ) -> Dict[str, Any]:
        """Extract relevant sections from a paper."""
        
        paper_text = paper.get('content') or paper.get('abstract', '')

        # If the paper text is very short or missing, augment it with analysis summaries
        if analysis and isinstance(analysis, dict):
            analysis_snippets = []
            for key in ["methodology", "summary", "key_findings", "claims", "contributions", "limitations"]:
                val = analysis.get(key)
                if isinstance(val, str) and val.strip():
                    analysis_snippets.append(val.strip())
                elif isinstance(val, list) and val:
                    analysis_snippets.extend([str(v) for v in val if isinstance(v, str) and v.strip()])
            if analysis_snippets and len(paper_text) < 500:
                paper_text = (paper_text + "\n\n" + "\n\n".join(analysis_snippets)).strip()

        if not paper_text:
            logger.warning(f"No content available for paper {paper_id}")
            return {}
        
        # Truncate for LLM context
        paper_text = paper_text[:6000]
        
        prompt = f"""Extract relevant sections from this research paper for the topic: "{topic}"

Paper Title: {paper.get('title')}
Paper Content:
{paper_text}

{SECTION_EXTRACTION_PROMPT}"""
        
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2048
            )
            
            # Parse JSON response
            text = response.text.strip()
            import re
            # Find JSON block
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                text = json_match.group(1)
            
            sections = json.loads(text)
            
        except Exception as e:
            logger.debug(f"Error using LLM for section extraction: {e}")
            # Fallback: extract basic sections manually
            sections = await self._extract_sections_fallback(paper, analysis)
        
        return sections
    
    async def _extract_sections_fallback(
        self,
        paper: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback section extraction without LLM."""
        
        content = paper.get('content', '')
        
        # Very simple fallback extraction
        sections = {
            "abstract": paper.get('abstract', '')[:500],
            "introduction": self._extract_by_keyword(content, ['introduction', 'background'], 1000),
            "methodology": self._extract_by_keyword(content, ['methodology', 'method', 'approach'], 1000),
            "results": self._extract_by_keyword(content, ['results', 'findings', 'evaluation'], 1000),
            "discussion": self._extract_by_keyword(content, ['discussion', 'conclusion'], 800),
            "key_findings": analysis.get('key_findings', []),
            "relevance_score": 0.5
        }
        
        return sections
    
    def _extract_by_keyword(self, text: str, keywords: List[str], max_chars: int = 1000) -> str:
        """Extract text near keywords."""
        
        text_lower = text.lower()
        
        for keyword in keywords:
            idx = text_lower.find(keyword.lower())
            if idx != -1:
                # Extract context around keyword
                start = max(0, idx - 200)
                end = min(len(text), idx + max_chars)
                return text[start:end]
        
        # If no keyword found, return first part
        return text[:max_chars]
