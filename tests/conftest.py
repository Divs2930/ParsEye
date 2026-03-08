"""Shared test fixtures for the invoice extraction test suite."""

import pytest

from invoice_extraction.invoice_extractor import ExtractionResult
from invoice_extraction.schemas import InvoiceData, LineItem


@pytest.fixture
def sample_line_item() -> LineItem:
    return LineItem(
        product_family="KISS KIDS DIAPERS",
        stock_code="KK001",
        supp_code="SUP001",
        description="KISS KIDS BABY DIAPERS XLARGE 100PCS",
        quantity="10",
        unit_price="150.00",
        vat_amount="225.00",
        line_total="1725.00",
    )


@pytest.fixture
def sample_line_item_2() -> LineItem:
    return LineItem(
        product_family="KISS KIDS DIAPERS",
        stock_code="KK002",
        supp_code="SUP002",
        description="KISS KIDS BABY DIAPERS LARGE 100PCS",
        quantity="5",
        unit_price="150.00",
        vat_amount="112.50",
        line_total="862.50",
    )


@pytest.fixture
def sample_invoice_data(sample_line_item: LineItem) -> InvoiceData:
    return InvoiceData(
        vendor_name="Test Vendor",
        client_name="Test Client",
        document_number="INV-001",
        document_date="2026-01-15",
        vat_number="VAT123456",
        subtotal="1500.00",
        vat_total="225.00",
        total="1725.00",
        line_items=[sample_line_item],
    )


@pytest.fixture
def sample_extraction_result(sample_invoice_data: InvoiceData) -> ExtractionResult:
    return ExtractionResult(
        source_filename="test_invoice.pdf",
        page_number=1,
        success=True,
        data=sample_invoice_data,
    )


@pytest.fixture
def failed_extraction_result() -> ExtractionResult:
    return ExtractionResult(
        source_filename="bad_invoice.pdf",
        page_number=1,
        success=False,
        error="API timeout",
    )
