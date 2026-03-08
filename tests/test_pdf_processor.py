"""Tests for the PDF processor."""

from invoice_extraction.pdf_processor import PageImage, PDFDocument, PDFProcessor


class TestPDFProcessor:
    def test_invalid_bytes_returns_error(self):
        processor = PDFProcessor(dpi=200)
        doc = processor.process(b"not a pdf", "bad.pdf")
        assert doc.success is False
        assert doc.error != ""
        assert doc.total_pages == 0

    def test_empty_bytes_returns_error(self):
        processor = PDFProcessor(dpi=200)
        doc = processor.process(b"", "empty.pdf")
        assert doc.success is False

    def test_custom_dpi(self):
        processor = PDFProcessor(dpi=100)
        assert processor.dpi == 100
        # Scale should be 100/72
        assert abs(processor._scale - 100 / 72) < 0.001


class TestPDFDocument:
    def test_success_with_pages(self):
        page = PageImage(
            page_number=1,
            image_bytes=b"fake_image",
            width=100,
            height=200,
            source_filename="test.pdf",
        )
        doc = PDFDocument(filename="test.pdf", total_pages=1, pages=[page])
        assert doc.success is True

    def test_failure_with_error(self):
        doc = PDFDocument(filename="test.pdf", total_pages=0, error="bad file")
        assert doc.success is False

    def test_failure_no_pages(self):
        doc = PDFDocument(filename="test.pdf", total_pages=0, pages=[])
        assert doc.success is False


class TestPageImage:
    def test_fields(self):
        page = PageImage(
            page_number=2,
            image_bytes=b"\x89PNG",
            width=800,
            height=600,
            source_filename="invoice.pdf",
        )
        assert page.page_number == 2
        assert page.source_filename == "invoice.pdf"
        assert page.width == 800
