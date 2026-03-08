"""Tests for invoice extractor — unit tests only, LLM calls are mocked."""

import io

from PIL import Image

from invoice_extraction.invoice_extractor import (
    ExtractionResult,
    _image_to_base64,
)
from invoice_extraction.schemas import InvoiceData


class TestImageToBase64:
    def test_converts_png_to_base64(self):
        # Create a tiny test image
        img = Image.new("RGB", (10, 10), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        result = _image_to_base64(image_bytes)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_is_valid_base64(self):
        import base64

        img = Image.new("RGB", (10, 10), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        b64 = _image_to_base64(buf.getvalue())
        # Should decode without error
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0


class TestExtractionResult:
    def test_display_name_single_page(self):
        result = ExtractionResult(
            source_filename="invoice.pdf",
            page_number=1,
            success=True,
        )
        assert result.display_name == "invoice.pdf"

    def test_display_name_multi_page(self):
        result = ExtractionResult(
            source_filename="invoice.pdf",
            page_number=3,
            success=True,
        )
        assert result.display_name == "invoice.pdf (page 3)"

    def test_to_dict(self):
        data = InvoiceData(vendor_name="Test")
        result = ExtractionResult(
            source_filename="test.pdf",
            page_number=1,
            success=True,
            data=data,
        )
        d = result.to_dict()
        assert d["vendor_name"] == "Test"

    def test_failed_result(self):
        result = ExtractionResult(
            source_filename="bad.pdf",
            page_number=1,
            success=False,
            error="API error",
        )
        assert result.success is False
        assert result.error == "API error"
