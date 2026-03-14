"""Section detection — identifies standard academic paper sections from extracted text."""

import re
from typing import Dict, List, Tuple
from loguru import logger


# Common section headers in academic papers (case-insensitive)
STANDARD_SECTIONS = [
    "abstract",
    "introduction",
    "related work",
    "background",
    "methodology",
    "methods",
    "method",
    "approach",
    "proposed method",
    "model",
    "architecture",
    "experiments",
    "experimental setup",
    "experimental results",
    "results",
    "evaluation",
    "discussion",
    "analysis",
    "ablation study",
    "ablation",
    "conclusion",
    "conclusions",
    "future work",
    "limitations",
    "acknowledgments",
    "acknowledgements",
    "references",
    "bibliography",
    "appendix",
]

# Regex pattern: matches numbered or unnumbered section headers
# e.g., "1. Introduction", "2 Methods", "III. Results", "ABSTRACT", "## Background"
SECTION_PATTERN = re.compile(
    r"^(?:"
    r"(?:\d+\.?\s+)"  # "1. " or "1 "
    r"|(?:[IVXivx]+\.?\s+)"  # "III. " Roman numerals
    r"|(?:#{1,3}\s+)"  # Markdown-style "## "
    r")?"
    r"(" + "|".join(re.escape(s) for s in STANDARD_SECTIONS) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class SectionDetector:
    """Detects and extracts sections from academic paper text."""

    def detect_sections(self, full_text: str) -> Dict[str, str]:
        """Split full paper text into named sections.

        Returns:
            Dict mapping section_name (lowercase) -> section_content
        """
        lines = full_text.split("\n")
        sections: Dict[str, str] = {}
        current_section: str = "preamble"
        current_content: List[str] = []

        for line in lines:
            stripped = line.strip()
            match = SECTION_PATTERN.match(stripped)

            if match:
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()

                current_section = match.group(1).lower()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        # Normalize aliases
        sections = self._normalize_section_names(sections)
        logger.info(f"Detected {len(sections)} sections: {list(sections.keys())}")
        return sections

    def _normalize_section_names(self, sections: Dict[str, str]) -> Dict[str, str]:
        """Merge alias section names into canonical names."""
        aliases = {
            "methods": "methodology",
            "method": "methodology",
            "approach": "methodology",
            "proposed method": "methodology",
            "conclusions": "conclusion",
            "experiments": "results",
            "experimental results": "results",
            "evaluation": "results",
            "acknowledgments": "acknowledgements",
            "bibliography": "references",
        }
        normalized: Dict[str, str] = {}
        for name, content in sections.items():
            canonical = aliases.get(name, name)
            if canonical in normalized:
                normalized[canonical] += "\n\n" + content
            else:
                normalized[canonical] = content
        return normalized

    def compute_confidence(self, sections: Dict[str, str]) -> Dict[str, float]:
        """Compute confidence score for each detected section.

        Confidence is based on content length and presence of expected keywords.
        """
        confidences: Dict[str, float] = {}
        for name, content in sections.items():
            score = 0.5  # base confidence

            # Longer sections generally more reliable
            if len(content) > 500:
                score += 0.2
            elif len(content) > 200:
                score += 0.1

            # Penalize very short sections
            if len(content) < 50:
                score -= 0.2

            # Bonus for expected section names
            if name in [
                "abstract",
                "introduction",
                "methodology",
                "results",
                "conclusion",
                "references",
            ]:
                score += 0.15

            confidences[name] = min(1.0, max(0.0, round(score, 2)))

        return confidences
