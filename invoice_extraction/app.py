"""
app.py
Invoice Parser — main Streamlit application entry point.

Thin orchestration layer — all logic lives in dedicated modules:
  - ui/         → styles, status bar, session state, results display
  - file_handler → file-to-image conversion
  - invoice_extractor → LLM extraction
"""

import html

import streamlit as st

from invoice_extraction.config import AppConfig
from invoice_extraction.file_handler import file_to_page_images
from invoice_extraction.invoice_extractor import InvoiceExtractor
from invoice_extraction.logging_config import setup_logging
from invoice_extraction.pdf_processor import PageImage
from invoice_extraction.ui.results import render_results
from invoice_extraction.ui.session import (
    clear_page_images,
    clear_results,
    clear_stop,
    get_results,
    is_stop_requested,
    request_stop,
    set_results,
    store_page_images,
)
from invoice_extraction.ui.sidebar import render_status_bar
from invoice_extraction.ui.styles import apply_styles

setup_logging()

APP = AppConfig()


# ── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Invoice Parser",
    page_icon="🧾",
    layout="wide",
)

apply_styles()

api_key, model_choice, export_filename, status = render_status_bar(APP.DEFAULT_MODEL)


# ── Main UI ───────────────────────────────────────────────────────────────────

st.markdown(
    """
<div class="header-box">
    <h1>🧾 Invoice Parser</h1>
    <p>Upload PDFs or images → Extract structured data → Download Excel</p>
</div>
""",
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "Drop invoice PDFs or images here",
    type=list(APP.SUPPORTED_FORMATS),
    accept_multiple_files=True,
)

if uploaded_files:
    # Validate file sizes
    max_bytes = APP.MAX_FILE_SIZE_MB * 1024 * 1024
    oversized = [f.name for f in uploaded_files if f.size > max_bytes]
    if oversized:
        st.error(f"File(s) exceed {APP.MAX_FILE_SIZE_MB}MB limit: {', '.join(oversized)}")
        st.stop()

    col1, col2 = st.columns(2)
    total_kb = sum(f.size for f in uploaded_files) / 1024
    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="val">{len(uploaded_files)}</div>'
            f'<div class="lbl">Files Uploaded</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="val">{total_kb:.0f} KB</div><div class="lbl">Total Size</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if not api_key:
        st.info("Enter your Gemini API key to get started.")
    elif not status.connected:
        st.error(f"Gemini API error: {html.escape(str(status.error))}")
    else:
        # ── Mode selector ─────────────────────────────────────────────────────
        col_mode, col_opts = st.columns([1, 2])

        with col_mode:
            rerun_mode = st.toggle("Re-run specific page", value=False)

        target_filename = None
        target_page = None

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
                    parts = selected.rsplit(" — page ", 1)
                    target_filename = parts[0]
                    target_page = int(parts[1])

        # ── Action button ─────────────────────────────────────────────────────
        btn_label = f"Re-run page {target_page}" if rerun_mode else "Extract All Invoices"

        if st.button(btn_label):
            extractor = InvoiceExtractor(api_key=api_key, model=model_choice)

            all_pages: list[PageImage] = []
            for f in uploaded_files:
                pages = file_to_page_images(f)
                all_pages.extend(pages)
                f.seek(0)

            # Store page images for side-by-side preview
            store_page_images(all_pages)

            if rerun_mode and target_filename and target_page:
                pages_to_process = [
                    p for p in all_pages if p.source_filename == target_filename and p.page_number == target_page
                ]
                if not pages_to_process:
                    st.error(f"Could not find page {target_page} in {target_filename}")
                    st.stop()

                existing = [
                    r
                    for r in get_results()
                    if not (r.source_filename == target_filename and r.page_number == target_page)
                ]
                all_results = existing
            else:
                clear_results()
                clear_page_images()
                store_page_images(all_pages)
                pages_to_process = all_pages
                all_results = []

            total = len(pages_to_process)
            progress_bar = st.progress(0, text="Starting...")
            status_slot = st.empty()
            stop_slot = st.empty()

            stop_slot.button(
                "Stop after this page",
                on_click=request_stop,
                key="stop_btn",
                type="secondary",
            )

            clear_stop()
            stopped_early = False

            for idx, page in enumerate(pages_to_process):
                if idx > 0 and is_stop_requested():
                    stopped_early = True
                    break

                label = f"{page.source_filename}" + (f" — page {page.page_number}" if page.page_number > 1 else "")
                safe_label = html.escape(label)
                progress_bar.progress(idx / total, text=f"Processing {label} ({idx + 1}/{total})")
                status_slot.markdown(
                    f'<div class="status-box">Extracting: <strong>{safe_label}</strong></div>',
                    unsafe_allow_html=True,
                )

                result = extractor.extract(
                    image_bytes=page.image_bytes,
                    filename=page.source_filename,
                    page_number=page.page_number,
                )
                all_results.append(result)

                # Save after every page — stop won't lose data
                all_results.sort(key=lambda r: (r.source_filename, r.page_number))
                set_results(all_results)

                icon = "OK" if result.success else "!!"
                css_class = "status-ok" if result.success else "status-warn"
                status_slot.markdown(
                    f'<div class="status-box {css_class}">{icon} Done: <strong>{safe_label}</strong></div>',
                    unsafe_allow_html=True,
                )

            stop_slot.empty()
            clear_stop()

            if stopped_early:
                progress_bar.progress(
                    len(all_results) / total,
                    text=f"Stopped — {len(all_results)} of {total} pages extracted",
                )
                st.warning(
                    f"Stopped at page {all_results[-1].page_number}. "
                    "Download partial results or re-run remaining pages."
                )
            else:
                progress_bar.progress(1.0, text="All done!")


# ── Results display ───────────────────────────────────────────────────────────

results = get_results()

if results:
    render_results(results, export_filename)
elif not uploaded_files:
    st.markdown(
        """
    <div style="text-align:center; padding:60px 20px; color:#4a5568;">
        <div style="font-size:64px; margin-bottom:16px;">🧾</div>
        <div style="font-size:18px; color:#718096;">Upload invoice PDFs or images to get started</div>
        <div style="font-size:13px; color:#4a5568; margin-top:8px;">
            PDF pages are rendered automatically · Powered by Gemini
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
