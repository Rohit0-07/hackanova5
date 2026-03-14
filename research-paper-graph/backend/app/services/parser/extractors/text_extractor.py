"""Text extraction from PDFs using pdfplumber and PyMuPDF (fitz)."""

import fitz  # PyMuPDF
import pdfplumber
import asyncio
from typing import Dict, List, Optional
from loguru import logger


class TextExtractor:
    """Extracts full text from PDFs using dual methods for reliability."""

    async def extract_text_fitz(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF (fitz) — fast and reliable."""

        def _sync_extract():
            doc = fitz.open(pdf_path)
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text("text"))
            doc.close()
            return "\n\n".join(pages_text)

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _sync_extract)
        logger.info(f"fitz extracted {len(text)} chars from {pdf_path}")
        return text

    async def extract_text_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber — better table/layout awareness."""

        def _sync_extract():
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _sync_extract)
        logger.info(f"pdfplumber extracted {len(text)} chars from {pdf_path}")
        return text

    async def extract_text(self, pdf_path: str) -> Dict[str, str]:
        """Extract text using both methods and return both results.

        Returns:
            {"fitz": ..., "pdfplumber": ..., "best": ...}
        """
        fitz_text = ""
        plumber_text = ""

        try:
            fitz_text = await self.extract_text_fitz(pdf_path)
        except Exception as e:
            logger.warning(f"fitz extraction failed: {e}")

        try:
            plumber_text = await self.extract_text_pdfplumber(pdf_path)
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")

        # Prefer whichever got more text (usually fitz for academic papers)
        best = fitz_text if len(fitz_text) >= len(plumber_text) else plumber_text

        return {"fitz": fitz_text, "pdfplumber": plumber_text, "best": best}

    async def extract_tables(self, pdf_path: str) -> List[Dict]:
        """Extract tables from PDF using pdfplumber."""

        def _sync_extract():
            tables = []
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for j, table in enumerate(page_tables):
                        tables.append(
                            {
                                "table_id": f"table_p{i + 1}_{j + 1}",
                                "page_number": i + 1,
                                "rows": table,
                                "row_count": len(table),
                                "col_count": len(table[0]) if table else 0,
                            }
                        )
            return tables

        loop = asyncio.get_event_loop()
        tables = await loop.run_in_executor(None, _sync_extract)
        logger.info(f"Extracted {len(tables)} tables from {pdf_path}")
        return tables

    async def get_page_count(self, pdf_path: str) -> int:
        """Get the number of pages in the PDF."""

        def _sync_count():
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_count)
