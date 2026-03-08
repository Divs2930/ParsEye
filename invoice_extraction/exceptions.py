"""
exceptions.py
Custom exception hierarchy for the invoice extraction pipeline.
"""


class InvoiceExtractionError(Exception):
    """Base exception for all invoice extraction errors."""


class PDFProcessingError(InvoiceExtractionError):
    """Failed to process a PDF file."""


class ExtractionError(InvoiceExtractionError):
    """LLM extraction failed."""


class RetryableExtractionError(ExtractionError):
    """Transient error that should be retried (rate limit, timeout, server error)."""


class NonRetryableExtractionError(ExtractionError):
    """Permanent error that should not be retried (invalid API key, bad image)."""


class AggregationError(InvoiceExtractionError):
    """Failed to aggregate line items."""


class ExportError(InvoiceExtractionError):
    """Failed to export to Excel."""
