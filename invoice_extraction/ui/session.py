"""
session.py
Streamlit session state helpers for tracking extraction results, stop requests,
and page images (for side-by-side preview).
"""

import streamlit as st

from ..invoice_extractor import ExtractionResult
from ..pdf_processor import PageImage


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


# ── Page image storage (for side-by-side preview) ────────────────────────────

def get_page_images() -> dict[str, bytes]:
    """Return dict mapping 'filename::page_number' → PNG bytes."""
    return st.session_state.get("page_images", {})


def set_page_images(images: dict[str, bytes]) -> None:
    st.session_state["page_images"] = images


def store_page_images(pages: list[PageImage]) -> None:
    """Merge page images into session state (additive)."""
    existing = get_page_images()
    for p in pages:
        key = f"{p.source_filename}::{p.page_number}"
        existing[key] = p.image_bytes
    set_page_images(existing)


def clear_page_images() -> None:
    st.session_state.pop("page_images", None)
