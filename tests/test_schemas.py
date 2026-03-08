"""Tests for Pydantic data models."""

from invoice_extraction.schemas import InvoiceData, LineItem


class TestLineItem:
    def test_defaults(self):
        item = LineItem()
        assert item.product_family == ""
        assert item.stock_code == ""
        assert item.quantity == ""
        assert item.line_total == ""

    def test_with_values(self, sample_line_item):
        assert sample_line_item.product_family == "KISS KIDS DIAPERS"
        assert sample_line_item.quantity == "10"

    def test_model_dump(self, sample_line_item):
        d = sample_line_item.model_dump()
        assert isinstance(d, dict)
        assert d["product_family"] == "KISS KIDS DIAPERS"
        assert d["quantity"] == "10"


class TestInvoiceData:
    def test_defaults(self):
        data = InvoiceData()
        assert data.vendor_name == ""
        assert data.line_items == []

    def test_with_values(self, sample_invoice_data):
        assert sample_invoice_data.vendor_name == "Test Vendor"
        assert sample_invoice_data.document_number == "INV-001"
        assert len(sample_invoice_data.line_items) == 1

    def test_to_dict(self, sample_invoice_data):
        d = sample_invoice_data.to_dict()
        assert isinstance(d, dict)
        assert d["vendor_name"] == "Test Vendor"
        assert isinstance(d["line_items"], list)
        assert len(d["line_items"]) == 1

    def test_to_dict_round_trip(self, sample_invoice_data):
        d = sample_invoice_data.to_dict()
        reconstructed = InvoiceData(**d)
        assert reconstructed.vendor_name == sample_invoice_data.vendor_name
        assert reconstructed.total == sample_invoice_data.total
        assert len(reconstructed.line_items) == len(sample_invoice_data.line_items)
