"""Tests for the Aggregator — grouping, parsing, and validation logic."""

import pytest

from invoice_extraction.aggregator import Aggregator
from invoice_extraction.invoice_extractor import ExtractionResult
from invoice_extraction.schemas import InvoiceData, LineItem


@pytest.fixture
def aggregator():
    return Aggregator()


class TestParseFloat:
    def test_empty_string(self, aggregator):
        val, ok = aggregator._parse_float("")
        assert ok is True
        assert val == 0.0

    def test_none_like(self, aggregator):
        val, ok = aggregator._parse_float(None)
        assert ok is True
        assert val == 0.0

    def test_plain_number(self, aggregator):
        val, ok = aggregator._parse_float("1234.56")
        assert ok is True
        assert val == 1234.56

    def test_with_commas(self, aggregator):
        val, ok = aggregator._parse_float("1,234,567.89")
        assert ok is True
        assert val == 1234567.89

    def test_with_spaces(self, aggregator):
        val, ok = aggregator._parse_float("1 234.56")
        assert ok is True
        assert val == 1234.56

    def test_rand_symbol(self, aggregator):
        val, ok = aggregator._parse_float("R1234.56")
        assert ok is True
        assert val == 1234.56

    def test_dollar_symbol(self, aggregator):
        val, ok = aggregator._parse_float("$1234.56")
        assert ok is True
        assert val == 1234.56

    def test_euro_symbol(self, aggregator):
        val, ok = aggregator._parse_float("\u20ac1234.56")
        assert ok is True
        assert val == 1234.56

    def test_invalid_string(self, aggregator):
        val, ok = aggregator._parse_float("abc")
        assert ok is False
        assert val == 0.0

    def test_negative_number(self, aggregator):
        val, ok = aggregator._parse_float("-123.45")
        assert ok is True
        assert val == -123.45

    def test_integer(self, aggregator):
        val, ok = aggregator._parse_float("100")
        assert ok is True
        assert val == 100.0


class TestAggregate:
    def test_successful_single_item(self, aggregator, sample_extraction_result):
        result = aggregator.aggregate(sample_extraction_result)
        assert result.valid is True
        assert len(result.product_rows) == 1
        assert result.product_rows[0].product_family == "KISS KIDS DIAPERS"
        assert result.product_rows[0].quantity == 10.0
        assert result.product_rows[0].total == 1725.0

    def test_failed_extraction(self, aggregator, failed_extraction_result):
        result = aggregator.aggregate(failed_extraction_result)
        assert result.valid is False
        assert "Extraction failed" in result.warning

    def test_no_line_items(self, aggregator):
        data = InvoiceData(vendor_name="Test", line_items=[])
        extraction = ExtractionResult(source_filename="test.pdf", page_number=1, success=True, data=data)
        result = aggregator.aggregate(extraction)
        assert result.valid is False
        assert "No line items" in result.warning

    def test_empty_product_family(self, aggregator):
        item = LineItem(product_family="", quantity="10", vat_amount="15", line_total="115")
        data = InvoiceData(line_items=[item])
        extraction = ExtractionResult(source_filename="test.pdf", page_number=1, success=True, data=data)
        result = aggregator.aggregate(extraction)
        assert result.valid is False
        assert "Empty product_family" in result.warning

    def test_unparseable_quantity(self, aggregator):
        item = LineItem(product_family="PRODUCT", quantity="abc", vat_amount="15", line_total="115")
        data = InvoiceData(line_items=[item])
        extraction = ExtractionResult(source_filename="test.pdf", page_number=1, success=True, data=data)
        result = aggregator.aggregate(extraction)
        assert result.valid is False
        assert "Cannot parse quantity" in result.warning

    def test_grouping_same_family(self, aggregator, sample_line_item, sample_line_item_2):
        data = InvoiceData(line_items=[sample_line_item, sample_line_item_2])
        extraction = ExtractionResult(source_filename="test.pdf", page_number=1, success=True, data=data)
        result = aggregator.aggregate(extraction)
        assert result.valid is True
        assert len(result.product_rows) == 1
        row = result.product_rows[0]
        assert row.quantity == 15.0  # 10 + 5
        assert row.total == 2587.5  # 1725 + 862.5

    def test_mixed_prices_blank_unit_price(self, aggregator):
        item1 = LineItem(
            product_family="PRODUCT",
            quantity="10",
            unit_price="100.00",
            vat_amount="150",
            line_total="1150",
        )
        item2 = LineItem(
            product_family="PRODUCT",
            quantity="5",
            unit_price="200.00",
            vat_amount="150",
            line_total="1150",
        )
        data = InvoiceData(line_items=[item1, item2])
        extraction = ExtractionResult(source_filename="test.pdf", page_number=1, success=True, data=data)
        result = aggregator.aggregate(extraction)
        assert result.valid is True
        assert result.product_rows[0].unit_price == ""

    def test_same_prices_kept(self, aggregator):
        item1 = LineItem(
            product_family="PRODUCT",
            quantity="10",
            unit_price="100.00",
            vat_amount="150",
            line_total="1150",
        )
        item2 = LineItem(
            product_family="PRODUCT",
            quantity="5",
            unit_price="100.00",
            vat_amount="75",
            line_total="575",
        )
        data = InvoiceData(line_items=[item1, item2])
        extraction = ExtractionResult(source_filename="test.pdf", page_number=1, success=True, data=data)
        result = aggregator.aggregate(extraction)
        assert result.valid is True
        assert result.product_rows[0].unit_price == "100.00"

    def test_summary_totals(self, aggregator, sample_extraction_result):
        result = aggregator.aggregate(sample_extraction_result)
        assert result.summary.total_quantity == 10.0
        assert result.summary.grand_total == 1725.0
        assert result.summary.total_vat == 225.0

    def test_metadata_propagation(self, aggregator, sample_extraction_result):
        result = aggregator.aggregate(sample_extraction_result)
        assert result.source_filename == "test_invoice.pdf"
        assert result.document_number == "INV-001"
        assert result.vendor_name == "Test Vendor"
