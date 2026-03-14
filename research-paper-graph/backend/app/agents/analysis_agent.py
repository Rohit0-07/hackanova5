"""Analysis Agent — uses LLM to extract structured findings from each research paper."""

from typing import Dict, Any, List, Optional
from loguru import logger

from app.services.parser.extractors.llm_extractor import (
    AbstractLLMClient,
    get_llm_client,
    FEATURE_EXTRACTION_SYSTEM_PROMPT,
)
from app.core.config import settings


PAPER_ANALYSIS_AGENT_PROMPT = """You are an expert research analyst agent. Given the full text (or available sections) of a research paper, extract a comprehensive structured analysis.

CRITICAL INSTRUCTIONS:
1. For every finding, claim, or contribution, you MUST provide:
   - "evidence": a direct verbatim quote from the text
   - "cited_from": {"section": "<section name e.g. Introduction/Methodology/Results>", "quote": "<verbatim text snippet>"}
2. Extract a "references" list — ALL papers cited by this paper, parsed from the reference/bibliography section.

Your output MUST be valid JSON with these keys:

- "research_question": string — the main question or hypothesis
- "methodology": {
    "approach": "string description",
    "evidence": "quote or specific detail from text supporting this",
    "cited_from": {"section": "Methodology", "quote": "verbatim snippet"}
  }
- "key_findings": [
    {
      "finding": "string",
      "evidence": "quote or data point from text",
      "cited_from": {"section": "Results", "quote": "verbatim snippet"}
    }
  ]
- "claims": [
    {
      "claim": "string",
      "evidence": "quote from text",
      "cited_from": {"section": "Introduction", "quote": "verbatim snippet"}
    }
  ]
- "datasets": list of strings
- "contributions": [
    {
      "contribution": "string",
      "evidence": "quote from text",
      "cited_from": {"section": "Introduction", "quote": "verbatim snippet"}
    }
  ]
- "limitations": list of strings
- "future_work": list of strings
- "keywords": list of strings
- "contribution_type": string
- "confidence_level": string
- "summary": string
- "reasoning_path": "Explain in 1-2 sentences how you derived these conclusions from the provided text."
- "references": [
    {
      "title": "cited paper title",
      "authors": ["Author A", "Author B"],
      "year": 2020,
      "venue": "NeurIPS 2020",
      "url": "https://arxiv.org/abs/... or DOI url if available, else null"
    }
  ]

Be precise. Populate references from the bibliography section. Output ONLY the JSON."""


class AnalysisAgent:
    """Analyzes each research paper and extracts structured findings using LLM."""

    def __init__(self, llm_client: Optional[AbstractLLMClient] = None):
        self._llm = llm_client

    def _get_llm(self) -> AbstractLLMClient:
        if self._llm is None:
            self._llm = get_llm_client(
                provider=settings.llm.provider,
                ollama_base_url=settings.llm.ollama.base_url,
                ollama_model=settings.llm.ollama.model,
                ollama_vision_model=settings.llm.ollama.vision_model,
            )
        return self._llm

    async def analyze_paper(
        self, paper_text: str, paper_title: str = "", paper_id: str = ""
    ) -> Dict[str, Any]:
        """Run LLM analysis on a paper's text and return structured findings.

        Args:
            paper_text: Full text of the paper (or concatenated sections).
            paper_title: Title of the paper for context.
            paper_id: ID for logging.

        Returns:
            Dict with structured findings (research_question, methodology, etc.)
        """
        logger.info(f"AnalysisAgent: analyzing paper '{paper_title[:60]}' ({paper_id})")

        # Truncate to fit LLM context window
        max_chars = 12000
        if len(paper_text) > max_chars:
            paper_text = (
                paper_text[:max_chars] + "\n\n[... text truncated for analysis ...]"
            )

        prompt = f"""Analyze this research paper and extract structured information.

Paper Title: {paper_title}

--- PAPER TEXT ---
{paper_text}
--- END OF PAPER TEXT ---

Extract the structured analysis as JSON."""

        try:
            llm = self._get_llm()
            response = await llm.generate(
                prompt=prompt,
                system_prompt=PAPER_ANALYSIS_AGENT_PROMPT,
                temperature=0.2,
                max_tokens=2048,
            )

            import json
            import re

            text = response.text.strip()
            
            # Find JSON block
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                text = json_match.group(1)

            result = self._safe_parse_json(text)
            result = self._normalize_analysis(result)
            result["_model"] = response.model
            result["_provider"] = response.provider
            result["_tokens_used"] = response.tokens_used
            return result

        except Exception as e:
            logger.warning(
                f"AnalysisAgent: LLM analysis failed ({e}), returning empty analysis"
            )
            return self._empty_analysis(paper_title, str(e))

    def _normalize_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure analysis output contains all expected sections."""
        if not isinstance(analysis, dict):
            return self._empty_analysis("unknown", "Invalid analysis output")

        # Core required fields with default values
        defaults = {
            "research_question": "unknown",
            "methodology": {"approach": "", "evidence": "", "cited_from": {}},
            "key_findings": [],
            "claims": [],
            "datasets": [],
            "contributions": [],
            "limitations": [],
            "future_work": [],
            "keywords": [],
            "contribution_type": "unknown",
            "confidence_level": "low",
            "summary": "",
            "reasoning_path": "",
            "references": [],
        }

        for k, v in defaults.items():
            if k not in analysis or analysis[k] is None:
                analysis[k] = v

        # Normalize methodology structure
        if not isinstance(analysis["methodology"], dict):
            analysis["methodology"] = {"approach": str(analysis.get("methodology", "")), "evidence": "", "cited_from": {}}
        else:
            analysis["methodology"].setdefault("approach", "")
            analysis["methodology"].setdefault("evidence", "")
            analysis["methodology"].setdefault("cited_from", {})

        # Normalize key_findings and claims to be list of dicts with cited_from
        def normalize_list_of_dicts(key: str, primary_field: str, extra_fields: List[str]):
            items = analysis.get(key)
            if not isinstance(items, list):
                analysis[key] = []
                return
            normalized = []
            for item in items:
                if isinstance(item, dict):
                    entry = {primary_field: item.get(primary_field, ""), "evidence": item.get("evidence", ""), "cited_from": item.get("cited_from", {})}
                    for f in extra_fields:
                        entry[f] = item.get(f, "")
                    normalized.append(entry)
                else:
                    normalized.append({primary_field: str(item), "evidence": "", "cited_from": {}})
            analysis[key] = normalized

        normalize_list_of_dicts("key_findings", "finding", [])
        normalize_list_of_dicts("claims", "claim", [])
        normalize_list_of_dicts("contributions", "contribution", [])

        # Normalize references list
        if not isinstance(analysis.get("references"), list):
            analysis["references"] = []
        normalized_refs = []
        for ref in analysis["references"]:
            if isinstance(ref, dict):
                normalized_refs.append({
                    "title": ref.get("title", ""),
                    "authors": ref.get("authors", []),
                    "year": ref.get("year"),
                    "venue": ref.get("venue", ""),
                    "url": ref.get("url"),
                })
            elif isinstance(ref, str):
                normalized_refs.append({"title": ref, "authors": [], "year": None, "venue": "", "url": None})
        analysis["references"] = normalized_refs

        return analysis

    def _safe_parse_json(self, text: str) -> Dict[str, Any]:
        """Try to parse LLM output as JSON, with fallbacks for common formatting issues."""
        import json
        import re
        import ast

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.debug(f"Initial JSON parsing failed: {e}. Attempting to clean invalid escapes.")
            # Fix common invalid escape sequences (e.g., \e) by escaping the backslash
            cleaned = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                # Last resort: try python literal eval (very permissive)
                try:
                    return ast.literal_eval(text)
                except Exception as e2:
                    logger.error(f"Failed to parse JSON after cleanup: {e2}")
                    raise e

    def _empty_analysis(self, title: str, error: str) -> Dict[str, Any]:
        return {
            "research_question": "unknown",
            "methodology": "unknown",
            "key_findings": [],
            "claims": [],
            "datasets": [],
            "contributions": [],
            "limitations": [],
            "future_work": [],
            "keywords": [],
            "contribution_type": "unknown",
            "confidence_level": "low",
            "summary": f"Analysis failed for '{title}': {error}",
            "_model": "N/A",
            "_provider": "N/A",
            "_tokens_used": 0,
        }

    async def compare_papers(
        self,
        paper_a_text: str,
        paper_b_text: str,
        paper_a_title: str,
        paper_b_title: str,
    ) -> Dict[str, Any]:
        """Compare two papers and identify agreements, contradictions, and gaps."""
        llm = self._get_llm()

        max_chars = 6000
        text_a = paper_a_text[:max_chars]
        text_b = paper_b_text[:max_chars]

        prompt = f"""Compare these two research papers:

PAPER A: {paper_a_title}
{text_a}

---

PAPER B: {paper_b_title}
{text_b}

---

Return JSON with:
- "agreements": list of points where both papers agree
- "contradictions": list of points where they disagree
- "unique_to_a": findings only in Paper A
- "unique_to_b": findings only in Paper B
- "methodology_comparison": how their approaches differ
- "recommendation": which paper to prioritize and why"""

        try:
            response = await llm.generate(
                prompt=prompt,
                system_prompt="You are an expert at comparing research papers. Return ONLY valid JSON.",
                temperature=0.2,
                max_tokens=2048,
            )
            import json
            import re

            text = response.text.strip()
            
            # Find JSON block
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                text = json_match.group(1)
            
            return json.loads(text)
        except Exception as e:
            return {"error": str(e), "agreements": [], "contradictions": []}
