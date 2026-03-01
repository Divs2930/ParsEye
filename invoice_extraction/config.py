"""
config.py
Centralized configuration constants for the invoice extraction pipeline.

All magic numbers and scattered constants are consolidated here.
"""

from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    """Application-level settings."""

    DEFAULT_MODEL: str = "gemini-2.5-flash"
    SUPPORTED_FORMATS: tuple[str, ...] = ("pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff")
    MAX_FILE_SIZE_MB: int = 50


@dataclass(frozen=True)
class PDFConfig:
    """PDF processing settings."""

    DPI: int = 200
    BASE_DPI: int = 72  # PyMuPDF base resolution


@dataclass(frozen=True)
class ExtractionConfig:
    """LLM extraction settings."""

    MAX_RETRIES: int = 3
    RETRY_MULTIPLIER: int = 1
    RETRY_MIN_WAIT: int = 2
    RETRY_MAX_WAIT: int = 30
    JPEG_QUALITY: int = 92
    TEMPERATURE: float = 0


@dataclass(frozen=True)
class ExcelColors:
    """Excel styling color constants."""

    HEADER_BG: str = "1E3A5F"
    TITLE_BG: str = "0D2137"
    SUMMARY_BG: str = "92D050"
    SUMMARY_TX: str = "000000"
    INVALID_BG: str = "FFCDD2"
    INVALID_TX: str = "B71C1C"
    ALT_ROW: str = "F0F4F8"
    YELLOW_HDR: str = "FFFF00"
    BLUE_HDR: str = "00B0F0"
    SEPARATOR_BG: str = "BDD7EE"
    NO_ITEMS_BG: str = "FFFDE7"
    INVOICE_NUM_ROW: str = "FFFF99"


CURRENCY_SYMBOLS: tuple[str, ...] = ("R", "$", "\u20ac", "\u00a3", "\u00a5", "\u20b9")
