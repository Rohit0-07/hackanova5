import os
import fitz
import pdfplumber
import asyncio
from typing import List, Optional
from app.services.crawler.models import Figure, Table, FigureMetadata
from loguru import logger


class ImageExtractor:
    """Dynamic image extraction from PDFs"""

    def __init__(self, output_dir: str = "./data/figures"):
        self.output_dir = output_dir

    async def extract_figures(
        self, pdf_path: str, min_width: int = 100, min_height: int = 100
    ) -> List[Figure]:
        logger.info(f"Extracting figures from {pdf_path}")
        os.makedirs(self.output_dir, exist_ok=True)

        def _sync_extract():
            doc = fitz.open(pdf_path)
            figures = []
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

                        # Filter out small images
                        if width < min_width or height < min_height:
                            continue

                        img_bytes = base_image["image"]
                        img_ext = base_image["ext"]
                        figure_id = f"fig_p{page_idx + 1}_{img_idx + 1}"

                        # Save to disk
                        filename_base = os.path.splitext(os.path.basename(pdf_path))[0]
                        save_path = os.path.join(
                            self.output_dir, f"{filename_base}_{figure_id}.{img_ext}"
                        )
                        with open(save_path, "wb") as f:
                            f.write(img_bytes)

                        figures.append(
                            Figure(
                                figure_id=figure_id,
                                image_path=save_path,
                                metadata=FigureMetadata(
                                    figure_id=figure_id,
                                    dimensions=(width, height),
                                    format=img_ext,
                                ),
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract image {xref} from page {page_idx + 1}: {e}"
                        )

            doc.close()
            return figures

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_extract)

    async def extract_tables(self, pdf_path: str) -> List[Table]:
        logger.info(f"Extracting tables from {pdf_path}")

        def _sync_extract():
            tables = []
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for j, table in enumerate(page_tables):
                        table_id = f"table_p{i + 1}_{j + 1}"
                        rows_str = "\\n".join(
                            [
                                "\\t".join([str(c) if c else "" for c in row])
                                for row in table
                            ]
                        )
                        tables.append(Table(table_id=table_id, content=rows_str))
            return tables

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_extract)

    async def get_figure_metadata(self, figure_id: str) -> Optional[FigureMetadata]:
        return None
