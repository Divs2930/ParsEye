"""
invoice_extractor.py
Extracts structured invoice data from images using LangChain + Gemini.

Three layers — use whichever fits your context:

  1. Standalone functions (best for notebooks):
       chain  = build_chain(api_key, model)
       result = extract_from_image(chain, image_bytes)

  2. InvoiceExtractor class (best for the Streamlit app):
       extractor = InvoiceExtractor(api_key, model)
       result    = extractor.extract(image_bytes, filename, page_number)

  3. ExtractionResult dataclass — wraps InvoiceData with metadata
     (filename, page number, success flag, error message)
"""

import base64
import io
import logging
import os
import time
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from PIL import Image
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import ExtractionConfig
from .logging_config import get_logger
from .schemas import InvoiceData

_EXTRACT = ExtractionConfig()
logger = get_logger("extractor")


# ── Prompt ────────────────────────────────────────────────────────────────────
# Kept brief — field-level instructions live in the Pydantic Field descriptions
# so LangChain's structured output passes them directly to the model.

SYSTEM_PROMPT = """You are an invoice data extraction specialist.
READ and COPY values exactly as they appear — never calculate, reformat, or infer.
Remove thousand-separator commas from numbers (e.g. 1466640.00 not 1,466,640.00).
Leave any field empty string if not visible on the invoice.

For product_family: strip all size, variant, weight, and packaging details to find
the core brand/product name. Apply consistently so variants of the same product
always get the same product_family value.
Examples:
  'KISS KIDS BABY DIAPERS XLARGE 100PCS' -> 'KISS KIDS DIAPERS'
  'KISS KIDS BABY DIAPERS LARGE 100PCS'  -> 'KISS KIDS DIAPERS'
  'KISS KIDS BABY DIAPERS SMALL 100PCS'  -> 'KISS KIDS DIAPERS'
  'ELLIS BROWN C/CREAMER CARTON 12X750G' -> 'ELLIS BROWN C/CREAMER'
  'PAMPERS ACTIVE BABY SIZE 3 MEGA PACK' -> 'PAMPERS ACTIVE BABY'
  'GOLD HUGGIES NAPPIES SIZE 4'          -> 'GOLD HUGGIES NAPPIES'

NOTE: Do check if subtotal is VAT-exclusive or inclusive. If the invoice explicitly states "Subtotal (exclusive)" or similar, set sub_total_exclusive to true. Otherwise, leave it false.
"""


# ── Standalone functions — usable directly in notebooks ──────────────────────


def build_chain(api_key: str = "", model: str = "gemini-2.0-flash"):
    """
    Build and return a LangChain structured output chain.

    The chain accepts a list of LangChain messages and returns
    a validated InvoiceData Pydantic object.

    Args:
        api_key: Gemini API key. Falls back to GOOGLE_API_KEY env var if empty.
        model:   Gemini model string e.g. 'gemini-2.0-flash'

    Returns:
        A Runnable chain: list[BaseMessage] → InvoiceData

    Example (notebook):
        chain  = build_chain(api_key="AIza...")
        result = extract_from_image(chain, image_bytes)
        print(result.vendor_name, result.total)
    """
    resolved_key = os.getenv("GOOGLE_API_KEY") or api_key

    if not resolved_key:
        raise ValueError("No API key found. Set GOOGLE_API_KEY in .env or pass api_key=")

    llm = ChatGoogleGenerativeAI(
        model=model,
        api_key=resolved_key,
        temperature=_EXTRACT.TEMPERATURE,
    )

    # with_structured_output enforces the Pydantic schema at the API level
    # method="json_schema" uses Gemini's native JSON mode — most reliable
    return llm.with_structured_output(InvoiceData, method="json_schema")


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(_EXTRACT.MAX_RETRIES),
    wait=wait_exponential(
        multiplier=_EXTRACT.RETRY_MULTIPLIER,
        min=_EXTRACT.RETRY_MIN_WAIT,
        max=_EXTRACT.RETRY_MAX_WAIT,
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _invoke_chain_with_retry(chain, message: HumanMessage) -> InvoiceData:
    """Raw chain call — called by extract_from_image, wrapped with tenacity retry."""
    return chain.invoke([message])


def extract_from_image(chain, image_bytes: bytes, label: str = "") -> InvoiceData:
    """
    Send an image to the chain and return a validated InvoiceData object.
    Retries up to 5 times with exponential backoff on any error.

    Args:
        chain:       The chain returned by build_chain()
        image_bytes: Raw bytes of the invoice image (PNG, JPG, etc.)
        label:       Optional label for log lines e.g. "invoice.pdf pg.3"

    Returns:
        InvoiceData Pydantic object with all extracted fields

    Example (notebook):
        chain  = build_chain()
        data   = extract_from_image(chain, open("invoice.png", "rb").read(), label="invoice.png")
        print(data.document_number)
        print(data.line_items)
    """
    tag = label or "image"
    logger.info(f"[{tag}] Starting extraction")
    start = time.time()

    b64 = _image_to_base64(image_bytes)
    message = HumanMessage(
        content=[
            {"type": "text", "text": SYSTEM_PROMPT},
            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64}"},
        ]
    )

    try:
        result = _invoke_chain_with_retry(chain, message)
        elapsed = time.time() - start
        n_items = len(result.line_items) if result.line_items else 0
        logger.info(f"[{tag}] Extracted {n_items} line items in {elapsed:.1f}s")
        return result
    except RetryError:
        elapsed = time.time() - start
        logger.error(f"[{tag}] All {_EXTRACT.MAX_RETRIES} retries exhausted after {elapsed:.1f}s")
        raise
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"[{tag}] Failed after {elapsed:.1f}s: {e}")
        raise


def extract_from_file(file_path: str, api_key: str = "", model: str = "gemini-2.0-flash") -> InvoiceData:
    """
    Convenience function — load image/PDF page from disk and extract.
    Useful for quick one-off extractions in notebooks.

    Args:
        file_path: Path to invoice image (PNG, JPG) or PDF (first page only)
        api_key:   Gemini API key (optional if set in .env)
        model:     Gemini model string

    Returns:
        InvoiceData Pydantic object

    Example (notebook):
        data = extract_from_file("invoice.pdf")
        print(data.total)
    """
    image_bytes = _load_file_as_image(file_path)
    chain = build_chain(api_key=api_key, model=model)
    return extract_from_image(chain, image_bytes)


# ── InvoiceExtractor class — used by the Streamlit pipeline ──────────────────


@dataclass
class ExtractionResult:
    """
    Wraps InvoiceData with pipeline metadata.
    Used by the Streamlit app to track per-page status, errors, and display names.
    """

    source_filename: str
    page_number: int
    success: bool
    data: InvoiceData = field(default_factory=InvoiceData)
    error: str = ""

    @property
    def display_name(self) -> str:
        if self.page_number > 1:
            return f"{self.source_filename} (page {self.page_number})"
        return self.source_filename

    def to_dict(self) -> dict:
        """Flat dict for Excel export — delegates to InvoiceData."""
        return self.data.to_dict()


class InvoiceExtractor:
    """
    Pipeline wrapper around build_chain() + extract_from_image().

    Builds the chain once on init, then reuses it for every page —
    avoids re-authenticating with the API on each call.

    Usage in app:
        extractor = InvoiceExtractor(api_key=api_key, model=model)
        result    = extractor.extract(image_bytes, filename="invoice.pdf", page_number=3)
    """

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash"):
        self.chain = build_chain(api_key=api_key, model=model)

    def extract(self, image_bytes: bytes, filename: str, page_number: int = 1) -> ExtractionResult:
        """
        Extract structured data from a single invoice page.
        Retries up to 5 times with exponential backoff. All attempts are logged
        to invoice_parser.log with filename and page number for traceability.

        Args:
            image_bytes:  Raw image bytes
            filename:     Source filename for tracking
            page_number:  Page number within the PDF

        Returns:
            ExtractionResult with validated InvoiceData or error details
        """
        label = f"{filename} pg.{page_number}"
        result = ExtractionResult(
            source_filename=filename,
            page_number=page_number,
            success=False,
        )

        logger.debug(f"[{label}] Queuing extraction")

        try:
            invoice_data = extract_from_image(self.chain, image_bytes, label=label)
            result.data = invoice_data
            result.success = True
            logger.debug(
                f"[{label}] Saved to result — vendor: {invoice_data.vendor_name!r}, total: {invoice_data.total!r}"
            )

        except Exception as e:
            result.error = str(e)
            logger.error(f"[{label}] Extraction failed permanently — {e}")

        return result


# ── Private helpers ───────────────────────────────────────────────────────────


def _image_to_base64(image_bytes: bytes) -> str:
    """Convert raw image bytes to base64 JPEG string."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_EXTRACT.JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _load_file_as_image(file_path: str) -> bytes:
    """Load a PNG/JPG/PDF file and return raw image bytes. PDFs use first page."""
    from pathlib import Path

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() == ".pdf":
        import fitz

        pdf = fitz.open(str(path))
        page = pdf[0]
        from .config import PDFConfig

        scale = PDFConfig.DPI / PDFConfig.BASE_DPI
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
        pdf.close()
        return pixmap.tobytes("png")

    return path.read_bytes()
