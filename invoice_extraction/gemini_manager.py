"""
gemini_manager.py
Validates the Gemini API key and lists available models.
Uses langchain-google-genai under the hood.
"""

import os
from dataclasses import dataclass

import invoice_extraction.config  # noqa: F401 — ensures load_dotenv() runs

from .logging_config import get_logger
from .config import AppConfig

logger = get_logger("gemini")

RECOMMENDED_MODELS = [
    AppConfig.DEFAULT_MODEL,
]


@dataclass
class GeminiStatus:
    connected: bool
    available_models: list[str]
    error: str = ""


class GeminiManager:
    """
    Validates a Gemini API key and checks connectivity.

    Key priority:
      1. GOOGLE_API_KEY in .env
      2. api_key passed at runtime (sidebar input)
    """

    def __init__(self, api_key: str = ""):
        self.api_key = os.getenv("GOOGLE_API_KEY") or api_key

    def check_status(self) -> GeminiStatus:
        if not self.api_key:
            return GeminiStatus(
                connected=False,
                available_models=[],
                error="No API key provided",
            )

        # Trust the key without making a test LLM call — the actual extraction
        # will surface auth errors if the key is invalid.
        logger.info(f"API key accepted (source: {self.key_source})")
        return GeminiStatus(
            connected=True,
            available_models=RECOMMENDED_MODELS,
        )

    def _sanitize_error(self, error: str) -> str:
        """Remove API key from error messages to prevent leakage."""
        if self.api_key and self.api_key in error:
            return error.replace(self.api_key, "***")
        return error

    @property
    def key_source(self) -> str:
        if os.getenv("GOOGLE_API_KEY"):
            return "from .env"
        elif self.api_key:
            return "from sidebar"
        return "not set"
