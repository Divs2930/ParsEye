"""
results.py
Results display — side-by-side invoice preview + extracted data, metrics, and Excel download.
"""

import os

import streamlit as st

from ..aggregator import Aggregator
from ..excel_exporter import ExcelExporter
from ..invoice_extractor import ExtractionResult
from .session import get_page_images


def render_results(results: list[ExtractionResult], export_filename: str) -> None:
    """Render results with side-by-side invoice image and extracted data."""
    aggregator = Aggregator()
    aggregated = [aggregator.aggregate(r) for r in results]

    ok_count = sum(1 for r in results if r.success)
    fail_count = len(results) - ok_count
    valid_count = sum(1 for a in aggregated if a.valid)
    invalid_count = len(aggregated) - valid_count

    st.markdown("---")
    st.markdown("## Results")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="metric-card"><div class="val" style="color:#48bb78">'
            f'{ok_count}</div><div class="lbl">Extracted</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-card"><div class="val" style="color:#fc8181">'
            f'{fail_count}</div><div class="lbl">Failed</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-card"><div class="val" style="color:#48bb78">'
            f'{valid_count}</div><div class="lbl">Ready for Excel</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="metric-card"><div class="val" style="color:#f6ad55">'
            f'{invalid_count}</div><div class="lbl">Need Review</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    page_images = get_page_images()

    # Per-invoice expandable cards with side-by-side preview
    for result, agg in zip(results, aggregated):
        icon = "+" if agg.valid else ("!" if result.success else "x")
        with st.expander(f"{icon} {result.display_name}", expanded=False):
            image_key = f"{result.source_filename}::{result.page_number}"
            has_image = image_key in page_images

            if has_image:
                col_img, col_data = st.columns([1, 1])
            else:
                col_img = None
                col_data = st.container()

            # Left column: invoice image
            if has_image and col_img is not None:
                with col_img:
                    st.markdown("**Original Invoice**")
                    st.image(page_images[image_key], use_container_width=True)

            # Right column: extracted data
            with col_data:
                if result.success:
                    _render_extracted_data(result, agg)
                else:
                    st.error(f"Extraction failed: {result.error}")

    # Excel download
    st.markdown("---")
    st.markdown("## Export to Excel")

    if invalid_count > 0:
        st.warning(
            f"{invalid_count} invoice(s) could not be aggregated and will appear "
            "as red rows in the Excel for manual review."
        )

    exporter = ExcelExporter()
    excel_bytes = exporter.export(aggregated, raw_results=results)

    safe_export = os.path.basename(export_filename).strip() or "invoices_extracted"
    fname = safe_export if safe_export.endswith(".xlsx") else safe_export + ".xlsx"

    st.download_button(
        label="Download Excel Report",
        data=excel_bytes,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.caption("2 sheets: Invoices (aggregated) · Raw Extraction (all line items as extracted)")


def _render_extracted_data(result: ExtractionResult, agg) -> None:
    """Render the extracted data for a single invoice."""
    d = result.data

    st.markdown("**Extracted Data**")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Invoice Info**")
        for key in ["document_number", "document_date", "vat_number"]:
            if val := getattr(d, key, ""):
                st.text(f"{key.replace('_', ' ').title()}: {val}")
    with col_b:
        st.markdown("**Amounts**")
        for key in ["subtotal", "vat_total", "total"]:
            if val := getattr(d, key, ""):
                st.text(f"{key.replace('_', ' ').title()}: {val}")

    st.markdown("**Vendor**")
    st.text(d.vendor_name or "—")
    st.markdown("**Client**")
    st.text(d.client_name or "—")

    # Raw line items
    if d.line_items:
        st.markdown(f"**Raw Line Items ({len(d.line_items)})**")
        st.dataframe(
            [item.model_dump() for item in d.line_items],
            use_container_width=True,
            hide_index=True,
        )

    # Aggregated product rows
    if agg.valid and agg.product_rows:
        st.markdown(f"**Aggregated Product Rows ({len(agg.product_rows)})**")
        preview = [
            {
                "Product": r.product_family,
                "Qty": r.quantity,
                "Rate": r.unit_price,
                "VAT": round(r.vat, 2),
                "Sub Total": round(r.sub_total, 2),
                "Total": round(r.total, 2),
            }
            for r in agg.product_rows
        ]
        st.dataframe(preview, use_container_width=True, hide_index=True)
    elif not agg.valid:
        st.warning(f"Aggregation issue: {agg.warning}")
