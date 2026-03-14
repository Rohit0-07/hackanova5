"""Query Agent — uses LLM to refine vague user queries into structured search parameters."""

from typing import Dict, Any, Optional
from loguru import logger

from app.services.parser.extractors.llm_extractor import AbstractLLMClient, get_llm_client
from app.core.config import settings


QUERY_REFINEMENT_PROMPT = """You are a research query refinement specialist. Given a user's research question or topic, transform it into structured search parameters optimized for academic database searches.

Your output MUST be valid JSON with these keys:
- "refined_queries": list of 3-5 specific search query strings optimized for arXiv/Google Scholar
- "key_concepts": list of core technical concepts to search for
- "date_range": {"start_year": int or null, "end_year": int or null} — infer from context if mentioned
- "target_venues": list of likely relevant venues/conferences/journals (can be empty)
- "exclusions": list of terms to exclude if the query implies narrowing scope
- "search_strategy": a brief 1-2 sentence explanation of your reasoning

EXAMPLES:

Input: "What do 2023 papers say about attention mechanisms?"
Output:
{
  "refined_queries": ["attention mechanism survey 2023", "self-attention transformer improvements 2023", "efficient attention architectures", "attention mechanism alternatives 2023", "linear attention models"],
  "key_concepts": ["attention mechanism", "self-attention", "transformer", "multi-head attention"],
  "date_range": {"start_year": 2023, "end_year": 2024},
  "target_venues": ["NeurIPS", "ICML", "ICLR", "ACL", "EMNLP"],
  "exclusions": [],
  "search_strategy": "Focus on 2023+ papers covering attention mechanism improvements, alternatives, and efficiency."
}

Input: "latest research on protein folding using deep learning"
Output:
{
  "refined_queries": ["protein structure prediction deep learning 2024", "AlphaFold improvements", "protein folding neural network", "de novo protein design machine learning", "protein language models"],
  "key_concepts": ["protein folding", "AlphaFold", "protein structure prediction", "protein language model"],
  "date_range": {"start_year": 2022, "end_year": null},
  "target_venues": ["Nature", "Science", "PNAS", "NeurIPS", "ICML"],
  "exclusions": [],
  "search_strategy": "Target recent protein folding papers with emphasis on deep learning methods and AlphaFold-related work."
}

ONLY output the JSON. No markdown, no explanation outside the JSON."""


class QueryAgent:
    """Transforms vague user queries into structured search parameters."""

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

    async def refine_query(self, raw_query: str) -> Dict[str, Any]:
        """Take a user's raw query and return structured search parameters.

        If LLM is unavailable, falls back to a simple heuristic.
        """
        logger.info(f"QueryAgent: refining query — '{raw_query}'")

        try:
            llm = self._get_llm()
            response = await llm.generate(
                prompt=f"Refine this research query:\n\n{raw_query}",
                system_prompt=QUERY_REFINEMENT_PROMPT,
                temperature=0.2,
                max_tokens=1024,
            )

            # Parse LLM response as JSON
            import json
            import re

            text = response.text.strip()
            # Find JSON block
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                text = json_match.group(1)
            
            result = json.loads(text)
            result["_source"] = "llm"
            result["_model"] = response.model
            logger.info(
                f"QueryAgent: LLM refined into {len(result.get('refined_queries', []))} queries"
            )
            return result

        except Exception as e:
            logger.warning(
                f"QueryAgent: LLM unavailable ({e}), using heuristic fallback"
            )
            return self._heuristic_refine(raw_query)

    def _heuristic_refine(self, raw_query: str) -> Dict[str, Any]:
        """Simple heuristic fallback when LLM is not available."""
        words = raw_query.strip().split()
        return {
            "refined_queries": [
                raw_query,
                " ".join(words[:5]) + " survey",
                " ".join(words[:5]) + " recent advances",
            ],
            "key_concepts": words[:8],
            "date_range": {"start_year": None, "end_year": None},
            "target_venues": [],
            "exclusions": [],
            "search_strategy": "Heuristic fallback: using raw query and variants.",
            "_source": "heuristic",
        }
