"""
sidebar.py
Top status bar — replaces the old sidebar with a compact inline status indicator.
Shows connection status (green/red dot) and model name as plain text.
"""

import html
import os

import streamlit as st

from ..gemini_manager import GeminiManager


def render_status_bar(default_model: str) -> tuple[str, str, str, object]:
    """Render a compact top status bar and return (api_key, model_choice, export_filename, status)."""
    env_key = os.getenv("GOOGLE_API_KEY", "")

    if env_key:
        api_key = env_key
    else:
        api_key = st.session_state.get("manual_api_key", "")

    manager = GeminiManager(api_key=api_key)
    status = manager.check_status()

    model_choice = default_model
    export_filename = "invoices_extracted.xlsx"

    # Build the status bar
    if api_key and status.connected:
        dot_color = "#48bb78"
        status_text = "Connected"
    elif api_key and not status.connected:
        dot_color = "#fc8181"
        status_text = f"Error: {html.escape(str(status.error))}"
    else:
        dot_color = "#f6ad55"
        status_text = "No API key"

    safe_model = html.escape(model_choice)

    st.markdown(
        f"""
        <div class="top-status-bar">
            <div class="status-indicator">
                <span class="status-dot" style="background:{dot_color};"></span>
                <span class="status-text">{status_text}</span>
            </div>
            <div class="model-label">Model: <strong>{safe_model}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # If no env key, show a small inline input (collapsed by default)
    if not env_key:
        with st.expander("Enter API Key", expanded=not api_key):
            manual_key = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="AIza...",
                help="Or set GOOGLE_API_KEY in your .env file",
                key="api_key_input",
            )
            if manual_key:
                st.session_state["manual_api_key"] = manual_key
                st.rerun()

    return api_key, model_choice, export_filename, status


# Keep backward-compatible alias
render_sidebar = render_status_bar
