"""
pdf_processor.py
Handles PDF → image conversion using PyMuPDF (no external binaries needed).
"""

from dataclasses import dataclass, field
from pathlib import Path
import fitz  # PyMuPDF


@dataclass
class PageImage:
    """A single rendered page from a PDF."""
    page_number: int        # 1-indexed
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

    DEFAULT_DPI = 200  # Good balance of quality vs speed for invoices

    def __init__(self, dpi: int = DEFAULT_DPI):
        self.dpi = dpi
        self._scale = dpi / 72  # PyMuPDF uses 72 DPI as base

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

            for page_index in range(len(pdf)):
                page = pdf[page_index]
                image_bytes = self._render_page(page)

                doc.pages.append(PageImage(
                    page_number=page_index + 1,
                    image_bytes=image_bytes,
                    width=int(page.rect.width * self._scale),
                    height=int(page.rect.height * self._scale),
                    source_filename=filename,
                ))

            pdf.close()

        except Exception as e:
            doc.error = str(e)

        return doc

    def _render_page(self, page: fitz.Page) -> bytes:
        """Render a single PDF page to PNG bytes."""
        matrix = fitz.Matrix(self._scale, self._scale)
        pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
        return pixmap.tobytes("png")
