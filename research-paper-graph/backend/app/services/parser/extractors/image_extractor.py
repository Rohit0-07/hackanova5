"""Image extraction from PDFs using PyMuPDF + LLM-powered analysis."""

import os
import fitz  # PyMuPDF
import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger
from app.services.parser.extractors.llm_extractor import (
    AbstractLLMClient,
    IMAGE_ANALYSIS_SYSTEM_PROMPT,
)


class ImageInfo:
    """Info about an extracted image."""

    def __init__(
        self,
        image_id: str,
        image_bytes: bytes,
        page_number: int,
        width: int,
        height: int,
        image_format: str,
        saved_path: str = "",
    ):
        self.image_id = image_id
        self.image_bytes = image_bytes
        self.page_number = page_number
        self.width = width
        self.height = height
        self.image_format = image_format
        self.saved_path = saved_path


class ImageExtractor:
    """Extracts images from PDFs and optionally analyzes them with an LLM."""

    def __init__(self, output_dir: str = "./data/figures"):
        self.output_dir = output_dir

    async def extract_images(
        self, pdf_path: str, min_width: int = 100, min_height: int = 100
    ) -> List[ImageInfo]:
        """Extract all images from a PDF that meet minimum size requirements.

        Filters out tiny icons/logos by enforcing min dimensions.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        def _sync_extract():
            doc = fitz.open(pdf_path)
            images = []
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                image_list = page.get_images(full=True)

                for img_idx, img_info in enumerate(image_list):
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue

                        width = base_image["width"]
                        height = base_image["height"]

                        # Filter out small images (icons, logos)
                        if width < min_width or height < min_height:
                            continue

                        img_bytes = base_image["image"]
                        img_ext = base_image["ext"]
                        image_id = f"fig_p{page_idx + 1}_{img_idx + 1}"

                        # Save to disk
                        save_path = os.path.join(
                            self.output_dir, f"{image_id}.{img_ext}"
                        )
                        with open(save_path, "wb") as f:
                            f.write(img_bytes)

                        images.append(
                            ImageInfo(
                                image_id=image_id,
                                image_bytes=img_bytes,
                                page_number=page_idx + 1,
                                width=width,
                                height=height,
                                image_format=img_ext,
                                saved_path=save_path,
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract image {xref} from page {page_idx + 1}: {e}"
                        )

            doc.close()
            return images

        loop = asyncio.get_event_loop()
        images = await loop.run_in_executor(None, _sync_extract)
        logger.info(
            f"Extracted {len(images)} images (>={min_width}x{min_height}) from {pdf_path}"
        )
        return images

    async def render_page_as_image(
        self, pdf_path: str, page_number: int, zoom: float = 2.0
    ) -> bytes:
        """Render a specific PDF page as a PNG image for LLM analysis."""

        def _sync_render():
            doc = fitz.open(pdf_path)
            page = doc[page_number - 1]
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_render)

    async def analyze_image_with_llm(
        self,
        llm_client: AbstractLLMClient,
        image: ImageInfo,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a single extracted image using the LLM vision model.

        Returns structured analysis including figure type, description,
        key findings, and significance.
        """
        prompt = custom_prompt or (
            f"This is Figure from page {image.page_number} of a research paper. "
            f"Image dimensions: {image.width}x{image.height}. "
            "Analyze this figure in detail. What does it show? "
            "What are the key data points, trends, or architectural components?"
        )

        try:
            response = await llm_client.analyze_image(
                image_bytes=image.image_bytes,
                prompt=prompt,
                system_prompt=IMAGE_ANALYSIS_SYSTEM_PROMPT,
            )
            return {
                "image_id": image.image_id,
                "page_number": image.page_number,
                "dimensions": (image.width, image.height),
                "format": image.image_format,
                "saved_path": image.saved_path,
                "llm_analysis": response.text,
                "llm_model": response.model,
                "llm_provider": response.provider,
                "tokens_used": response.tokens_used,
            }
        except Exception as e:
            logger.error(f"LLM image analysis failed for {image.image_id}: {e}")
            return {
                "image_id": image.image_id,
                "page_number": image.page_number,
                "dimensions": (image.width, image.height),
                "format": image.image_format,
                "saved_path": image.saved_path,
                "llm_analysis": f"Analysis failed: {str(e)}",
                "llm_model": "N/A",
                "llm_provider": "N/A",
                "tokens_used": 0,
            }

    async def analyze_all_images(
        self, llm_client: AbstractLLMClient, images: List[ImageInfo]
    ) -> List[Dict[str, Any]]:
        """Analyze all extracted images with the LLM."""
        results = []
        for img in images:
            result = await self.analyze_image_with_llm(llm_client, img)
            results.append(result)
        return results
