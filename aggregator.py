"""
aggregator.py
Groups raw line items by product_family and computes per-group and per-invoice totals.

This sits between InvoiceExtractor and ExcelExporter in the pipeline.
Also usable standalone in notebooks.

Output shape:
  AggregatedInvoice
    ├── invoice metadata (date, number, vendor, client...)
    ├── product_rows: list[ProductRow]   ← one row per product family
    │     ├── product_family
    │     ├── quantity        (sum)
    │     ├── unit_price      (common price, or "" if mixed)
    │     ├── vat             (sum)
    │     ├── sub_total       (total - vat)
    │     └── total           (sum)
    └── summary: InvoiceSummary          ← totals across all product rows
          ├── total_quantity
          ├── total_vat
          ├── sub_total
          └── grand_total
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductRow:
    """One aggregated row in the Excel output — represents a product family."""
    product_family: str
    quantity:       float = 0.0
    unit_price:     str   = ""     # blank if mixed prices across variants
    vat:            float = 0.0
    sub_total:      float = 0.0
    total:          float = 0.0


@dataclass
class InvoiceSummary:
    """Totals row (green row in the Excel) — sums across all ProductRows."""
    total_quantity: float = 0.0
    total_vat:      float = 0.0
    sub_total:      float = 0.0
    grand_total:    float = 0.0


@dataclass
class AggregatedInvoice:
    """
    Full aggregated result for one invoice page.
    Ready to be written directly to Excel.
    """
    # ── Invoice metadata ──────────────────────────────────────────────────────
    source_filename: str = ""
    page_number:     int = 1
    document_date:   str = ""
    document_number: str = ""
    vendor_name:     str = ""
    client_name:     str = ""

    # ── Aggregated data ───────────────────────────────────────────────────────
    product_rows: list[ProductRow]  = field(default_factory=list)
    summary:      InvoiceSummary    = field(default_factory=InvoiceSummary)

    # ── Validation flag ───────────────────────────────────────────────────────
    valid:        bool = True
    warning:      str  = ""   # human-readable reason if valid=False


class Aggregator:
    """
    Converts an ExtractionResult into an AggregatedInvoice.

    Grouping rules:
      - Line items with the same product_family are merged into one ProductRow
      - quantity, vat_amount, line_total are summed (parsed as floats)
      - unit_price is kept if all items in the group share the same price,
        otherwise set to "" (flagged for manual review — invoice not rejected)
      - sub_total per group = total - vat

    Validation rules (sets valid=False, goes to human review):
      - Any line item has empty product_family
      - Any numeric field cannot be parsed as float
    """

    def aggregate(self, result) -> AggregatedInvoice:
        """
        Args:
            result: ExtractionResult from InvoiceExtractor

        Returns:
            AggregatedInvoice ready for Excel export
        """
        inv = AggregatedInvoice(
            source_filename = result.source_filename,
            page_number     = result.page_number,
            document_date   = result.data.document_date   or "",
            document_number = result.data.document_number or "",
            vendor_name     = result.data.vendor_name     or "",
            client_name     = result.data.client_name     or "",
        )

        if not result.success:
            inv.valid   = False
            inv.warning = f"Extraction failed: {result.error}"
            return inv

        line_items = result.data.line_items or []

        if not line_items:
            inv.valid   = False
            inv.warning = "No line items extracted"
            return inv

        # ── Group by product_family ───────────────────────────────────────────
        groups: dict[str, list] = {}
        for item in line_items:
            family = (item.product_family or "").strip()
            if not family:
                inv.valid   = False
                inv.warning = f"Empty product_family on item: {item.description!r} — sent for manual review"
                return inv
            groups.setdefault(family, []).append(item)

        # ── Build ProductRow per group ────────────────────────────────────────
        for family, items in groups.items():
            row, ok, warn = self._build_product_row(family, items)
            if not ok:
                inv.valid   = False
                inv.warning = warn
                return inv
            inv.product_rows.append(row)

        # ── Build summary ─────────────────────────────────────────────────────
        inv.summary = InvoiceSummary(
            total_quantity = sum(r.quantity  for r in inv.product_rows),
            total_vat      = sum(r.vat       for r in inv.product_rows),
            sub_total      = sum(r.sub_total for r in inv.product_rows),
            grand_total    = sum(r.total     for r in inv.product_rows),
        )

        return inv

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_product_row(self, family: str, items: list) -> tuple:
        """
        Aggregate a list of LineItems into a single ProductRow.

        Returns:
            (ProductRow, success: bool, warning: str)
        """
        total_qty   = 0.0
        total_vat   = 0.0
        total_amt   = 0.0
        prices      = set()

        for item in items:
            qty, ok = self._parse_float(item.quantity)
            if not ok:
                return None, False, f"Cannot parse quantity '{item.quantity}' for {family!r}"

            vat, ok = self._parse_float(item.vat_amount)
            if not ok:
                return None, False, f"Cannot parse vat_amount '{item.vat_amount}' for {family!r}"

            amt, ok = self._parse_float(item.line_total)
            if not ok:
                return None, False, f"Cannot parse line_total '{item.line_total}' for {family!r}"

            total_qty += qty
            total_vat += vat
            total_amt += amt

            price = (item.unit_price or "").strip()
            if price:
                prices.add(price)

        # Unit price — show if all variants share the same price, blank if mixed
        unit_price = prices.pop() if len(prices) == 1 else ""

        sub_total = total_amt - total_vat

        row = ProductRow(
            product_family = family,
            quantity       = total_qty,
            unit_price     = unit_price,
            vat            = total_vat,
            sub_total      = sub_total,
            total          = total_amt,
        )

        return row, True, ""

    def _parse_float(self, value: str) -> tuple[float, bool]:
        """
        Safely parse a string to float.
        Strips commas, spaces, currency symbols.

        Returns:
            (float_value, success: bool)
        """
        if not value:
            return 0.0, True   # empty = treat as zero, not an error

        cleaned = (
            str(value)
            .replace(",", "")
            .replace(" ", "")
            .replace("R", "")   # South African Rand symbol
            .replace("$", "")
            .replace("€", "")
            .strip()
        )

        try:
            return float(cleaned), True
        except ValueError:
            return 0.0, False
