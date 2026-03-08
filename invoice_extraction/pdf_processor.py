"""
pdf_processor.py
Handles PDF → image conversion using PyMuPDF (no external binaries needed).
"""

from dataclasses import dataclass, field

import fitz  # PyMuPDF

from .config import PDFConfig
from .logging_config import get_logger

logger = get_logger("pdf")


@dataclass
class PageImage:
    """A single rendered page from a PDF."""

    page_number: int  # 1-indexed
    image_bytes: bytes
    width: int
    height: int
    source_filename: str


@dataclass
class PDFDocument:
    """Result of processing a PDF file."""

    filename: str
    total_pages: int
    pages: list[PageImage] = field(default_factory=list)
    error: str = ""

    @property
    def success(self) -> bool:
        return not self.error and len(self.pages) > 0


class PDFProcessor:
    """
    Converts PDF files into a list of page images.

    Each page is rendered at a configurable DPI and returned as PNG bytes.
    Higher DPI = better OCR quality but more memory and slower processing.
    """

    def __init__(self, dpi: int = PDFConfig.DPI):
        self.dpi = dpi
        self._scale = dpi / PDFConfig.BASE_DPI

    def process(self, file_bytes: bytes, filename: str) -> PDFDocument:
        """
        Convert all pages of a PDF into rendered PageImage objects.

        Args:
            file_bytes: Raw PDF bytes
            filename:   Original filename (for display/tracking)

        Returns:
            PDFDocument with rendered pages or error message
        """
        doc = PDFDocument(filename=filename, total_pages=0)

        try:
            pdf = fitz.open(stream=file_bytes, filetype="pdf")
            doc.total_pages = len(pdf)
            logger.info(f"[{filename}] Opened PDF with {doc.total_pages} page(s)")

            for page_index in range(len(pdf)):
                page = pdf[page_index]
                image_bytes = self._render_page(page)

                doc.pages.append(
                    PageImage(
                        page_number=page_index + 1,
                        image_bytes=image_bytes,
                        width=int(page.rect.width * self._scale),
                        height=int(page.rect.height * self._scale),
                        source_filename=filename,
                    )
                )

            pdf.close()
            logger.debug(f"[{filename}] Rendered all {doc.total_pages} pages at {self.dpi} DPI")

        except fitz.FileDataError as e:
            doc.error = f"Invalid PDF format: {e}"
            logger.error(f"[{filename}] Invalid PDF format: {e}")
        except Exception as e:
            doc.error = f"Unexpected error: {e}"
            logger.exception(f"[{filename}] Unexpected PDF processing error")

        return doc

    def _render_page(self, page: fitz.Page) -> bytes:
        """Render a single PDF page to PNG bytes."""
        matrix = fitz.Matrix(self._scale, self._scale)
        pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
        return pixmap.tobytes("png")
