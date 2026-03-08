"""
schemas.py
Pydantic models defining the structured output shape for invoice extraction.

These are the single source of truth for the data structure —
used by LangChain's with_structured_output(), the Excel exporter,
and directly importable into notebooks.
"""

from typing import Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single row from the invoice line items table."""

    product_family: Optional[str] = Field(
        default="",
        description=(
            "Normalized product family name — strip size, variant, and packaging details. "
            "Examples: 'KISS KIDS BABY DIAPERS XLARGE 100PCS' → 'KISS KIDS BABY DIAPERS', "
            "'ELLIS BROWN C/CREAMER CARTON 12X750G' → 'ELLIS BROWN C/CREAMER', "
            "'PAMPERS ACTIVE BABY SIZE 3 MEGA PACK' → 'PAMPERS ACTIVE BABY'. "
            "Use the shortest unambiguous brand or product name."
        ),
    )
    stock_code: Optional[str] = Field(default="", description="Stock code for the item")
    supp_code: Optional[str] = Field(default="", description="Supplier code for the item")
    description: Optional[str] = Field(default="", description="Full item description exactly as printed")
    quantity: Optional[str] = Field(default="", description="Quantity as printed — no reformatting")
    unit_price: Optional[str] = Field(default="", description="Unit price as printed — no reformatting")
    vat_amount: Optional[str] = Field(
        default="",
        description="VAT amount for this line — copy exactly, do not compute",
    )
    line_total: Optional[str] = Field(
        default="",
        description="Line total from TOTAL column — copy exactly, do not compute",
    )


class InvoiceData(BaseModel):
    """
    All structured fields extracted from a single invoice page.
    Field descriptions guide the LLM on what to extract.
    """

    vendor_name: Optional[str] = Field(
        default="",
        description="Name of the company ISSUING the invoice, usually at the top",
    )
    client_name: Optional[str] = Field(
        default="",
        description="Name of the company RECEIVING the invoice",
    )
    document_number: Optional[str] = Field(
        default="",
        description="Document number, labelled 'Document No.' on the invoice",
    )
    document_date: Optional[str] = Field(
        default="",
        description="Invoice date, labelled 'Document Date' on the invoice",
    )
    vat_number: Optional[str] = Field(
        default="",
        description="VAT registration number, labelled 'VAT Number' on the invoice",
    )
    subtotal: Optional[str] = Field(
        default="",
        description="Subtotal before VAT — copy exactly as printed, do not compute",
    )
    sub_total_exclusive: bool = Field(default=False, description="Whether the subtotal is exclusive of VAT")
    vat_total: Optional[str] = Field(
        default="",
        description="Total VAT amount — copy exactly as printed, do not compute",
    )
    total: Optional[str] = Field(
        default="",
        description="Final invoice total — copy exactly as printed, do not compute",
    )
    line_items: list[LineItem] = Field(
        default_factory=list,
        description="Every row from the invoice line items table",
    )

    def to_dict(self) -> dict:
        """Convert to plain dict for Excel export or notebook display."""
        return self.model_dump()
