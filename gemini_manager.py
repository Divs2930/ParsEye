"""
gemini_manager.py
Validates the Gemini API key and lists available models.
Uses langchain-google-genai under the hood.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

RECOMMENDED_MODELS = [
    "gemini-3-flash-preview",
]


@dataclass
class GeminiStatus:
    connected:        bool
    available_models: list
    error:            str = ""


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

        try:
            # Validate key with a lightweight test call via LangChain
            llm = ChatGoogleGenerativeAI(
                model=RECOMMENDED_MODELS[0],
                api_key=self.api_key,
                temperature=0,
                max_tokens=1,
            )
            llm.invoke("hi")  # minimal call just to validate the key

            return GeminiStatus(
                connected=True,
                available_models=RECOMMENDED_MODELS,
            )

        except Exception as e:
            return GeminiStatus(
                connected=False,
                available_models=[],
                error=str(e),
            )

    @property
    def key_source(self) -> str:
        if os.getenv("GOOGLE_API_KEY"):
            return "from .env"
        elif self.api_key:
            return "from sidebar"
        return "not set"
