"""
file_handler.py
Converts uploaded files (PDF or image) into PageImage objects for extraction.
"""

import io

import streamlit as st
from PIL import Image

from .config import PDFConfig
from .logging_config import get_logger
from .pdf_processor import PageImage, PDFDocument, PDFProcessor

logger = get_logger("file_handler")


def file_to_page_images(uploaded_file, dpi: int = PDFConfig.DPI) -> list[PageImage]:
    """
    Convert an uploaded file (PDF or image) into a list of PageImage objects.
    PDFs are rendered page-by-page. Images are wrapped in a single PageImage.
    """
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    if filename.lower().endswith(".pdf"):
        processor = PDFProcessor(dpi=dpi)
        doc: PDFDocument = processor.process(file_bytes, filename)

        if not doc.success:
            st.warning(f"Could not process PDF '{filename}': {doc.error}")
            return []

        return doc.pages

    else:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        logger.debug(f"[{filename}] Converted image to PNG ({img.width}x{img.height})")
        return [
            PageImage(
                page_number=1,
                image_bytes=buf.getvalue(),
                width=img.width,
                height=img.height,
                source_filename=filename,
            )
        ]
