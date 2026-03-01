"""
app.py
Invoice Parser — main Streamlit application.

This file is intentionally kept thin.
All logic lives in the imported classes:
  - GeminiManager    → API key validation + model listing
  - PDFProcessor     → PDF → page images
  - InvoiceExtractor → image → structured JSON via Gemini
  - ExcelExporter    → results → styled .xlsx
"""

import io
import os
import streamlit as st
from PIL import Image

from gemini_manager import GeminiManager
from pdf_processor import PDFProcessor, PDFDocument, PageImage
from invoice_extractor import InvoiceExtractor, ExtractionResult
from aggregator import Aggregator, AggregatedInvoice
from excel_exporter import ExcelExporter


# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_MODEL     = "gemini-2.0-flash"
SUPPORTED_FORMATS = ["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"]
PDF_DPI           = 200


# ── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Invoice Parser",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main, .stApp { background-color: #0f1117; }

    .header-box {
        background: linear-gradient(135deg, #1a1f2e, #252d3d);
        border: 1px solid #2d3748; border-radius: 12px;
        padding: 24px 32px; margin-bottom: 24px;
    }
    .header-box h1 { color: #e2e8f0; font-size: 28px; margin: 0 0 4px 0; }
    .header-box p  { color: #718096; margin: 0; font-size: 14px; }

    .status-box {
        background: #1a1f2e; border: 1px solid #2d3748;
        border-radius: 8px; padding: 14px 18px;
        margin: 8px 0; font-size: 14px; color: #a0aec0;
    }
    .status-ok   { border-left: 3px solid #48bb78; }
    .status-err  { border-left: 3px solid #fc8181; }
    .status-warn { border-left: 3px solid #f6ad55; }

    .metric-card {
        background: #1a1f2e; border: 1px solid #2d3748;
        border-radius: 10px; padding: 16px 20px; text-align: center;
    }
    .metric-card .val { font-size: 26px; font-weight: 700; color: #63b3ed; }
    .metric-card .lbl { font-size: 12px; color: #718096; margin-top: 4px; }

    .stButton > button {
        background: linear-gradient(135deg, #3182ce, #2b6cb0);
        color: white; border: none; border-radius: 8px;
        padding: 10px 24px; font-weight: 600; width: 100%;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2b6cb0, #2c5282);
    }
</style>
""", unsafe_allow_html=True)


# ── Session state helpers ─────────────────────────────────────────────────────

def get_results() -> list[ExtractionResult]:
    return st.session_state.get("results", [])

def set_results(results: list[ExtractionResult]) -> None:
    st.session_state["results"] = results

def clear_results() -> None:
    st.session_state.pop("results", None)

def is_stop_requested() -> bool:
    return st.session_state.get("stop_requested", False)

def request_stop() -> None:
    st.session_state["stop_requested"] = True

def clear_stop() -> None:
    st.session_state["stop_requested"] = False


# ── File handling helpers ─────────────────────────────────────────────────────

def file_to_page_images(uploaded_file) -> list[PageImage]:
    """
    Convert an uploaded file (PDF or image) into a list of PageImage objects.
    PDFs are rendered page-by-page. Images are wrapped in a single PageImage.
    """
    file_bytes = uploaded_file.read()
    filename   = uploaded_file.name

    if filename.lower().endswith(".pdf"):
        processor = PDFProcessor(dpi=PDF_DPI)
        doc: PDFDocument = processor.process(file_bytes, filename)

        if not doc.success:
            st.warning(f"⚠️ Could not process PDF '{filename}': {doc.error}")
            return []

        return doc.pages

    else:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return [PageImage(
            page_number=1,
            image_bytes=buf.getvalue(),
            width=img.width,
            height=img.height,
            source_filename=filename,
        )]


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # Check if key already loaded from .env
    env_key = os.getenv("GOOGLE_API_KEY", "")

    if env_key:
        # Key found in .env — no need to show input, just confirm
        st.markdown(
            '<div class="status-box status-ok">🔑 API key loaded from .env</div>',
            unsafe_allow_html=True,
        )
        api_key = env_key
    else:
        # No .env key — show input field
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Or set GOOGLE_API_KEY in your .env file",
        )

    # Validate key and list models
    manager = GeminiManager(api_key=api_key)
    status  = manager.check_status()

    if not api_key:
        st.markdown(
            '<div class="status-box status-warn">🔑 Enter API key above or add to .env</div>',
            unsafe_allow_html=True,
        )
        model_choice = DEFAULT_MODEL
    elif status.connected:
        st.markdown(
            '<div class="status-box status-ok">✅ Gemini connected</div>',
            unsafe_allow_html=True,
        )
        default_index = (
            status.available_models.index(DEFAULT_MODEL)
            if DEFAULT_MODEL in status.available_models
            else 0
        )
        model_choice = st.selectbox("Model", status.available_models, index=default_index)
    else:
        st.markdown(
            f'<div class="status-box status-err">❌ API key invalid<br>{status.error}</div>',
            unsafe_allow_html=True,
        )
        model_choice = st.text_input("Model name", value=DEFAULT_MODEL)

    st.markdown("---")
    st.markdown("### 📋 Export")
    export_filename = st.text_input("Excel filename", value="invoices_extracted.xlsx")

    st.markdown("---")
    st.markdown("### ℹ️ Setup Guide")
    with st.expander("Steps"):
        st.markdown("""
**1. Get a free Gemini API key**
Go to [aistudio.google.com](https://aistudio.google.com),
sign in and click **Get API Key**.

**2. Add key to .env**
```
GOOGLE_API_KEY=AIza...your_key
```

**3. Install dependencies**
```
pip install -r requirements.txt
```

**4. Run this app**
```
streamlit run app.py
```

**Remote access via Tailscale:**
Install Tailscale on both machines,
sign in with same account, then open:
`http://<desktop-ip>:8501`
        """)


# ── Main UI ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="header-box">
    <h1>🧾 Invoice Parser</h1>
    <p>Upload PDFs or images → Extract structured data → Download Excel</p>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drop invoice PDFs or images here",
    type=SUPPORTED_FORMATS,
    accept_multiple_files=True,
)

if uploaded_files:
    col1, col2, col3 = st.columns(3)
    total_kb = sum(f.size for f in uploaded_files) / 1024
    with col1:
        st.markdown(f'<div class="metric-card"><div class="val">{len(uploaded_files)}</div><div class="lbl">Files Uploaded</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="val">{total_kb:.0f} KB</div><div class="lbl">Total Size</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="val">{model_choice.split(":")[0]}</div><div class="lbl">Model</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    if not api_key:
        st.info("👈 Enter your Gemini API key in the sidebar to get started.")
    elif not status.connected:
        st.error(f"❌ Gemini API error: {status.error}")
    else:
        # ── Mode selector ─────────────────────────────────────────────────────
        col_mode, col_opts = st.columns([1, 2])

        with col_mode:
            rerun_mode = st.toggle("🔁 Re-run specific page", value=False)

        target_filename = None
        target_page     = None

        if rerun_mode:
            with col_opts:
                page_options = []
                for f in uploaded_files:
                    if f.name.lower().endswith(".pdf"):
                        import fitz
                        pdf = fitz.open(stream=f.read(), filetype="pdf")
                        for p in range(len(pdf)):
                            page_options.append(f"{f.name} — page {p + 1}")
                        pdf.close()
                        f.seek(0)
                    else:
                        page_options.append(f"{f.name} — page 1")

                selected = st.selectbox("Select page to re-run", page_options)

                if selected:
                    parts           = selected.rsplit(" — page ", 1)
                    target_filename = parts[0]
                    target_page     = int(parts[1])

        # ── Action button ─────────────────────────────────────────────────────
        btn_label = f"🔁 Re-run page {target_page}" if rerun_mode else "🚀 Extract All Invoices"

        if st.button(btn_label):
            extractor = InvoiceExtractor(api_key=api_key, model=model_choice)

            all_pages: list[PageImage] = []
            for f in uploaded_files:
                pages = file_to_page_images(f)
                all_pages.extend(pages)
                f.seek(0)

            if rerun_mode and target_filename and target_page:
                pages_to_process = [
                    p for p in all_pages
                    if p.source_filename == target_filename and p.page_number == target_page
                ]
                if not pages_to_process:
                    st.error(f"Could not find page {target_page} in {target_filename}")
                    st.stop()

                existing    = [
                    r for r in get_results()
                    if not (r.source_filename == target_filename and r.page_number == target_page)
                ]
                all_results = existing
            else:
                clear_results()
                pages_to_process = all_pages
                all_results      = []

            total        = len(pages_to_process)
            progress_bar = st.progress(0, text="Starting…")
            status_slot  = st.empty()
            stop_slot    = st.empty()

            stop_slot.button(
                "⏹ Stop after this page",
                on_click=request_stop,
                key="stop_btn",
                type="secondary",
            )

            clear_stop()
            stopped_early = False

            for idx, page in enumerate(pages_to_process):

                # Check stop flag before starting next page
                if idx > 0 and is_stop_requested():
                    stopped_early = True
                    break

                label = f"{page.source_filename}" + (f" — page {page.page_number}" if page.page_number > 1 else "")
                progress_bar.progress(idx / total, text=f"Processing {label} ({idx+1}/{total})")
                status_slot.markdown(f'<div class="status-box">⏳ Extracting: <strong>{label}</strong></div>', unsafe_allow_html=True)

                result = extractor.extract(
                    image_bytes=page.image_bytes,
                    filename=page.source_filename,
                    page_number=page.page_number,
                )
                all_results.append(result)

                # Save after every page — stop won't lose data
                all_results.sort(key=lambda r: (r.source_filename, r.page_number))
                set_results(all_results)

                icon = "✅" if result.success else "⚠️"
                status_slot.markdown(f'<div class="status-box {"status-ok" if result.success else "status-warn"}">{icon} Done: <strong>{label}</strong></div>', unsafe_allow_html=True)

            stop_slot.empty()
            clear_stop()

            if stopped_early:
                progress_bar.progress(
                    len(all_results) / total,
                    text=f"⏹ Stopped — {len(all_results)} of {total} pages extracted",
                )
                st.warning(f"Stopped at page {all_results[-1].page_number}. Download partial results or re-run remaining pages.")
            else:
                progress_bar.progress(1.0, text="✅ All done!")


# ── Results display ───────────────────────────────────────────────────────────

results = get_results()

if results:
    # Run aggregator on all results
    aggregator   = Aggregator()
    aggregated   = [aggregator.aggregate(r) for r in results]

    ok_count     = sum(1 for r in results if r.success)
    fail_count   = len(results) - ok_count
    valid_count  = sum(1 for a in aggregated if a.valid)
    invalid_count= len(aggregated) - valid_count
    rate         = f"{ok_count / len(results) * 100:.0f}%" if results else "0%"

    st.markdown("---")
    st.markdown("## 📊 Results")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="val" style="color:#48bb78">{ok_count}</div><div class="lbl">Extracted</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="val" style="color:#fc8181">{fail_count}</div><div class="lbl">Failed</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="val" style="color:#48bb78">{valid_count}</div><div class="lbl">Ready for Excel</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="val" style="color:#f6ad55">{invalid_count}</div><div class="lbl">Need Review</div></div>', unsafe_allow_html=True)

    # ── Per-invoice expandable cards ──────────────────────────────────────────
    for result, agg in zip(results, aggregated):
        icon = "✅" if agg.valid else ("⚠️" if result.success else "❌")
        with st.expander(f"{icon} {result.display_name}", expanded=False):
            if result.success:
                d = result.data

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

                # Raw line items (what LLM extracted)
                if d.line_items:
                    st.markdown(f"**Raw Line Items ({len(d.line_items)})**")
                    st.dataframe(
                        [item.model_dump() for item in d.line_items],
                        use_container_width=True,
                        hide_index=True,
                    )

                # Aggregated product rows (what goes into Excel)
                if agg.valid and agg.product_rows:
                    st.markdown(f"**Aggregated Product Rows ({len(agg.product_rows)}) → Excel preview**")
                    preview = [{
                        "Product":   r.product_family,
                        "Qty":       r.quantity,
                        "Rate":      r.unit_price,
                        "VAT":       round(r.vat, 2),
                        "Sub Total": round(r.sub_total, 2),
                        "Total":     round(r.total, 2),
                    } for r in agg.product_rows]
                    st.dataframe(preview, use_container_width=True, hide_index=True)
                elif not agg.valid:
                    st.warning(f"⚠️ Aggregation issue: {agg.warning}")

    # ── Excel download ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📥 Export to Excel")

    if invalid_count > 0:
        st.warning(f"{invalid_count} invoice(s) could not be aggregated and will appear as red rows in the Excel for manual review.")

    exporter    = ExcelExporter()
    excel_bytes = exporter.export(aggregated, raw_results=results)
    fname       = export_filename if export_filename.endswith(".xlsx") else export_filename + ".xlsx"

    st.download_button(
        label="⬇️ Download Excel Report",
        data=excel_bytes,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.caption("2 sheets: Invoices (aggregated) · Raw Extraction (all line items as extracted)")

elif not uploaded_files:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; color:#4a5568;">
        <div style="font-size:64px; margin-bottom:16px;">🧾</div>
        <div style="font-size:18px; color:#718096;">Upload invoice PDFs or images to get started</div>
        <div style="font-size:13px; color:#4a5568; margin-top:8px;">
            PDF pages are rendered automatically · Powered by Gemini
        </div>
    </div>
    """, unsafe_allow_html=True)
