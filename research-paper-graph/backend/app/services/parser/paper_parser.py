"""Main PaperParser — orchestrates all extractors to produce PaperContent."""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from app.services.parser.models import (
    PaperContent,
    SectionContent,
    ExtractedFigure,
    ExtractedTable,
    ParsedReference,
    ExtractionAudit,
)
from app.services.parser.extractors.text_extractor import TextExtractor
from app.services.parser.extractors.image_extractor import ImageExtractor
from app.services.parser.extractors.section_detector import SectionDetector
from app.services.parser.extractors.reference_parser import ReferenceParser
from app.services.parser.extractors.llm_extractor import (
    AbstractLLMClient,
    get_llm_client,
    PAPER_ANALYSIS_SYSTEM_PROMPT,
    FEATURE_EXTRACTION_SYSTEM_PROMPT,
)
from app.services.crawler.models import PaperMetadata


class PaperParser:
    """Main parser orchestrator — extracts all structured content from a PDF."""

    PARSER_VERSION = "1.0.0"

    def __init__(
        self,
        figures_dir: str = "./data/figures",
        llm_provider: str = "ollama",
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        self.text_extractor = TextExtractor()
        self.image_extractor = ImageExtractor(output_dir=figures_dir)
        self.section_detector = SectionDetector()
        self.reference_parser = ReferenceParser()

        # LLM client (optional — used for deep analysis)
        self._llm_config = llm_config or {}
        self._llm_provider = llm_provider
        self._llm_client: Optional[AbstractLLMClient] = None

    def _get_llm(self) -> AbstractLLMClient:
        """Lazy-init the LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client(
                provider=self._llm_provider, **self._llm_config
            )
        return self._llm_client

    async def parse_paper(
        self,
        pdf_path: str,
        paper_id: str,
        metadata: Optional[PaperMetadata] = None,
        analyze_images: bool = False,
    ) -> PaperContent:
        """Full pipeline: text → sections → references → figures → audit.

        Args:
            pdf_path: Path to the PDF file.
            paper_id: Unique ID for this paper.
            metadata: Optional PaperMetadata from the crawler.
            analyze_images: If True, uses LLM to analyze extracted figures.
        """
        start_time = datetime.utcnow()
        methods_used: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []
        confidence_scores: Dict[str, float] = {}

        logger.info(f"Parsing paper {paper_id} from {pdf_path}")

        # 1. Extract text
        text_results = await self.text_extractor.extract_text(pdf_path)
        full_text = text_results["best"]
        methods_used.append("fitz")
        methods_used.append("pdfplumber")
        confidence_scores["text_extraction"] = 0.95 if len(full_text) > 500 else 0.6

        # 2. Detect sections
        sections_raw = self.section_detector.detect_sections(full_text)
        section_confidences = self.section_detector.compute_confidence(sections_raw)
        methods_used.append("section_detector")
        confidence_scores["section_identification"] = sum(
            section_confidences.values()
        ) / max(len(section_confidences), 1)

        sections: Dict[str, SectionContent] = {}
        for name, content in sections_raw.items():
            sections[name] = SectionContent(
                section_name=name.title(),
                content=content,
                subsections={},
                confidence=section_confidences.get(name, 0.5),
            )

        # 3. Extract references
        refs_text = sections_raw.get("references", "")
        parsed_refs = self.reference_parser.parse_references_section(refs_text)
        methods_used.append("reference_parser")
        confidence_scores["reference_parsing"] = 0.9 if parsed_refs else 0.3

        # 4. Extract images
        images_raw = await self.image_extractor.extract_images(pdf_path)
        methods_used.append("fitz_image_extractor")

        figures: List[ExtractedFigure] = []
        for i, img in enumerate(images_raw):
            figures.append(
                ExtractedFigure(
                    figure_id=img.image_id,
                    figure_number=i + 1,
                    caption="",  # Captions require more sophisticated extraction
                    image_path=img.saved_path,
                    page_number=img.page_number,
                    dimensions=(img.width, img.height),
                    format=img.image_format,
                )
            )

        # 5. (Optional) LLM image analysis
        image_analyses = []
        if analyze_images and images_raw:
            try:
                llm = self._get_llm()
                image_analyses = await self.image_extractor.analyze_all_images(
                    llm, images_raw
                )
                methods_used.append(f"llm_vision_{llm.provider_name}")
            except Exception as e:
                logger.warning(f"LLM image analysis skipped: {e}")
                warnings.append(f"LLM image analysis failed: {str(e)}")

        # 6. Extract tables
        tables_raw = await self.text_extractor.extract_tables(pdf_path)
        methods_used.append("pdfplumber_tables")
        tables: List[ExtractedTable] = []
        for t in tables_raw:
            rows_str = "\n".join(
                ["\t".join([str(c) if c else "" for c in row]) for row in t["rows"]]
            )
            tables.append(
                ExtractedTable(
                    table_id=t["table_id"],
                    table_number=len(tables) + 1,
                    caption="",
                    content=rows_str,
                    page_number=t["page_number"],
                )
            )

        # Build audit log
        end_time = datetime.utcnow()
        audit = ExtractionAudit(
            extraction_time=end_time,
            parser_version=self.PARSER_VERSION,
            methods_used=methods_used,
            confidence_scores=confidence_scores,
            errors=errors,
            warnings=warnings,
        )

        # Construct dummy metadata if none provided
        if metadata is None:
            from app.services.crawler.models import PaperIdentifier
            import hashlib

            metadata = PaperMetadata(
                identifier=PaperIdentifier(
                    title=paper_id,
                    authors=[],
                    hash=hashlib.sha256(paper_id.encode()).hexdigest(),
                ),
                title=paper_id,
                authors=[],
                publication_date=datetime.utcnow(),
                venue="",
                abstract=sections_raw.get("abstract", ""),
                reference_list=[],
                url="",
                source_api="local_pdf",
            )

        return PaperContent(
            paper_id=paper_id,
            metadata=metadata,
            sections=sections,
            abstract=sections_raw.get("abstract", ""),
            introduction=sections_raw.get("introduction", ""),
            methodology=sections_raw.get("methodology", ""),
            results=sections_raw.get("results", ""),
            conclusion=sections_raw.get("conclusion", ""),
            references=parsed_refs,
            figures=figures,
            tables=tables,
            extraction_audit=audit,
        )

    async def extract_features_with_llm(
        self, full_text: str, paper_id: str
    ) -> Dict[str, Any]:
        """Use an LLM to extract structured features from the paper text.

        Returns a dict with: research_question, methodology, datasets,
        key_results, contributions, limitations, future_work, keywords.
        """
        llm = self._get_llm()
        # Truncate if very long (LLM context limits)
        text_for_llm = full_text[:15000] if len(full_text) > 15000 else full_text

        prompt = (
            f"Extract structured features from this research paper.\n\n"
            f"--- PAPER TEXT ---\n{text_for_llm}\n--- END ---\n\n"
            f"Return valid JSON with keys: research_question, methodology, datasets, "
            f"key_results, contributions, limitations, future_work, keywords"
        )

        response = await llm.generate(
            prompt=prompt,
            system_prompt=FEATURE_EXTRACTION_SYSTEM_PROMPT,
            temperature=0.2,
        )

        return {
            "paper_id": paper_id,
            "llm_response": response.text,
            "model": response.model,
            "provider": response.provider,
            "tokens_used": response.tokens_used,
        }

    async def analyze_paper_with_llm(
        self, full_text: str, paper_id: str
    ) -> Dict[str, Any]:
        """Use an LLM for a comprehensive analysis of the paper."""
        llm = self._get_llm()
        text_for_llm = full_text[:15000] if len(full_text) > 15000 else full_text

        prompt = (
            f"Provide a comprehensive analysis of this research paper:\n\n"
            f"--- PAPER TEXT ---\n{text_for_llm}\n--- END ---"
        )

        response = await llm.generate(
            prompt=prompt,
            system_prompt=PAPER_ANALYSIS_SYSTEM_PROMPT,
            temperature=0.3,
        )

        return {
            "paper_id": paper_id,
            "analysis": response.text,
            "model": response.model,
            "provider": response.provider,
            "tokens_used": response.tokens_used,
        }
