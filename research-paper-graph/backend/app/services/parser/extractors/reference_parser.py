"""Reference parser — extracts and normalizes citation strings from paper text."""

import re
from typing import List, Optional, Tuple
from loguru import logger
from app.services.parser.models import ParsedReference
from app.services.crawler.models import PaperIdentifier


class ReferenceParser:
    """Parses the references/bibliography section of academic papers."""

    # Common reference patterns
    # [1] Author, A. & Author, B. (2020). Title. Journal, 1(2), 3-4.
    NUMBERED_REF = re.compile(r"^\[(\d+)\]\s*(.+)", re.MULTILINE)
    # Author, A. & Author, B. (2020). Title. Journal.
    AUTHOR_YEAR = re.compile(
        r"^([A-Z][a-zà-ö]+(?:,?\s+(?:[A-Z]\.?\s*)+)?(?:\s*(?:and|&|,)\s*[A-Z][a-zà-ö]+(?:,?\s+(?:[A-Z]\.?\s*)+)?)*)\s*[\(\.]\s*(\d{4})\s*[\)\.]\s*(.+)",
        re.MULTILINE,
    )

    def parse_references_section(self, references_text: str) -> List[ParsedReference]:
        """Parse the full references section text into structured references.

        Tries numbered references first, then falls back to author-year format.
        """
        if not references_text or len(references_text.strip()) < 20:
            return []

        # Try numbered refs first
        refs = self._parse_numbered(references_text)
        if not refs:
            refs = self._parse_author_year(references_text)

        # Fallback: split by blank lines or double newlines
        if not refs:
            refs = self._parse_by_splitting(references_text)

        logger.info(f"Parsed {len(refs)} references from text")
        return refs

    def _parse_numbered(self, text: str) -> List[ParsedReference]:
        """Parse [1] style numbered references."""
        matches = self.NUMBERED_REF.findall(text)
        refs = []
        for num, raw_text in matches:
            parsed = self._extract_fields(raw_text.strip())
            parsed.raw_text = f"[{num}] {raw_text.strip()}"
            refs.append(parsed)
        return refs

    def _parse_author_year(self, text: str) -> List[ParsedReference]:
        """Parse Author (Year) style references."""
        matches = self.AUTHOR_YEAR.findall(text)
        refs = []
        for authors_str, year_str, rest in matches:
            authors = self._split_authors(authors_str)
            title = self._extract_title_from_rest(rest)
            refs.append(
                ParsedReference(
                    raw_text=f"{authors_str} ({year_str}). {rest}".strip(),
                    normalized_form=f"{authors_str} ({year_str})",
                    authors=authors,
                    year=int(year_str),
                    title=title,
                    venue=self._extract_venue(rest),
                )
            )
        return refs

    def _parse_by_splitting(self, text: str) -> List[ParsedReference]:
        """Fallback: split references by blank lines or numbers."""
        # Split by double newline or by lines starting with numbers
        chunks = re.split(r"\n\s*\n|\n(?=\d+[\.\)])", text)
        refs = []
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) > 20:  # skip tiny fragments
                parsed = self._extract_fields(chunk)
                refs.append(parsed)
        return refs

    def _extract_fields(self, raw_text: str) -> ParsedReference:
        """Try to extract author, year, title from a raw citation string."""
        authors: List[str] = []
        year: Optional[int] = None
        title: Optional[str] = None
        venue: Optional[str] = None

        # Extract year
        year_match = re.search(r"\((\d{4})\)|\b((?:19|20)\d{2})\b", raw_text)
        if year_match:
            year = int(year_match.group(1) or year_match.group(2))

        # Extract title: typically the first sentence in quotes or after year
        title_match = re.search(r'"([^"]+)"', raw_text)
        if title_match:
            title = title_match.group(1)
        else:
            # Take text between first period and second period as title guess
            parts = raw_text.split(".")
            if len(parts) >= 2:
                title = parts[1].strip()[:200]

        # Extract authors: text before year or first period
        author_part = (
            raw_text.split("(")[0] if "(" in raw_text else raw_text.split(".")[0]
        )
        authors = self._split_authors(author_part)

        venue = self._extract_venue(raw_text)

        return ParsedReference(
            raw_text=raw_text[:500],
            normalized_form=f"{', '.join(authors[:3])} ({year})"
            if year
            else raw_text[:100],
            authors=authors,
            year=year,
            title=title,
            venue=venue,
        )

    def _split_authors(self, author_str: str) -> List[str]:
        """Split an author string into individual author names."""
        # Split by "and", "&", or ","
        parts = re.split(r"\s+and\s+|\s*&\s*|\s*,\s*", author_str.strip())
        authors = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
        return authors[:20]  # cap at 20 authors

    def _extract_title_from_rest(self, rest: str) -> Optional[str]:
        """Extract title from the rest of the citation after author/year."""
        # Title is typically the first sentence
        parts = rest.split(".")
        if parts:
            return parts[0].strip()[:200]
        return None

    def _extract_venue(self, text: str) -> Optional[str]:
        """Try to extract venue/journal name from citation text."""
        # Look for common patterns: "In ...", "Proceedings of ...", italicized journal
        venue_match = re.search(
            r"(?:In\s+|Proceedings\s+of\s+)([^\.]+)", text, re.IGNORECASE
        )
        if venue_match:
            return venue_match.group(1).strip()[:150]
        return None
