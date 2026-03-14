"""Synthesis Agent — Uses LLM to synthesize knowledge across multiple papers."""

import json
from typing import List, Dict, Any

from app.services.parser.extractors.llm_extractor import get_llm_client
from app.core.config import settings
from app.services.crawler.models import AnalyzedPaper
from loguru import logger

SYNTHESIS_SYSTEM_PROMPT = """\
You are an expert Research Synthesis Agent. Your job is to read the findings from multiple academic papers and synthesize them into three distinct deliverables:
1. Literature Summary: A concise overview of how the field is approaching this topic.
2. Contradiction Report: Identify specific points where papers disagree or use fundamentally different methodologies to approach the same problem.
3. Research Gap Brief: Identify what is missing from the current literature—what questions are circled but never directly answered?

You must output valid JSON matching this schema exactly.

{
  "literature_summary": "A 2-3 paragraph synthesis of the current state of the art based on these papers.",
  "contradictions": [
    {
      "topic": "The specific claim or methodology in dispute",
      "paper_a": "ID or title of first paper",
      "paper_b": "ID or title of second paper",
      "description": "How they differ or contradict"
    }
  ],
  "research_gaps": [
    {
      "gap": "The unanswered question or missing piece",
      "priority": "High/Medium/Low",
      "justification": "Why this gap is important based on the literature"
    }
  ]
}

DO NOT include any markdown formatting blocks like ```json around the output. Just return the raw JSON string. If there are no clear contradictions, return an empty list for that field. Do the same for gaps.
"""


class SynthesisAgent:
    def __init__(self):
        self.llm_client = get_llm_client(
            provider=settings.llm.provider,
            ollama_base_url=settings.llm.ollama.base_url,
            ollama_model=settings.llm.ollama.model,
            ollama_vision_model=settings.llm.ollama.vision_model,
        )

    async def generate_synthesis(
        self, query: str, papers: List[AnalyzedPaper]
    ) -> Dict[str, Any]:
        """Generate a synthesis report from a list of analyzed papers."""
        logger.info(
            f"SynthesisAgent: Generating report for {len(papers)} papers on '{query}'"
        )

        # Prepare context
        # We only want to send the most salient parts to the LLM to save tokens
        papers_context = []
        for p in papers:
            # Skip un-analyzed papers for synthesis if needed, but we'll include abstracts fallback
            try:
                pub_year = p.metadata.publication_date.year if hasattr(p.metadata.publication_date, 'year') else 2024
                context = {
                    "id": p.paper_id,
                    "title": p.metadata.title,
                    "year": pub_year,
                    "abstract": p.metadata.abstract,
                }
                if p.analysis:
                    context["key_findings"] = p.analysis.get("key_findings", [])
                    context["claims"] = p.analysis.get("claims", [])
                    context["methodology"] = p.analysis.get("methodology", "")

                papers_context.append(context)
            except Exception as e:
                logger.warning(f"Failed to process paper {p.paper_id}: {e}")
                continue

        prompt = f"""
        Research Query: {query}
        
        Papers Analyzed:
        {json.dumps(papers_context, indent=2)}
        
        Based on these papers, generate the requested JSON synthesis.
        """

        try:
            response = await self.llm_client.generate(
                prompt, system_prompt=SYNTHESIS_SYSTEM_PROMPT
            )
            response_text = response.text.strip()

            import re
            # Find JSON block
            json_match = re.search(r'(\{[\s\S]*\})', response_text)
            if json_match:
                response_text = json_match.group(1)

            # Parse JSON
            result = json.loads(response_text)
            logger.info("SynthesisAgent: Successfully generated synthesis.")
            return result

        except json.JSONDecodeError as e:
            logger.error(
                f"SynthesisAgent: LLM returned invalid JSON: {e}\nResponse: {response_text[:500] if 'response_text' in locals() else 'N/A'}..."
            )
            return {
                "literature_summary": "Failed to parse LLM response.",
                "contradictions": [],
                "research_gaps": [],
            }
        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"SynthesisAgent: Failed to generate synthesis: {error_msg}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {
                "literature_summary": "Error generating synthesis.",
                "contradictions": [],
                "research_gaps": [],
            }
