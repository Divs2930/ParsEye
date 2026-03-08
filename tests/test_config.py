"""Tests for configuration constants."""

import pytest

from invoice_extraction.config import (
    CURRENCY_SYMBOLS,
    AppConfig,
    ExcelColors,
    ExtractionConfig,
    PDFConfig,
)


class TestAppConfig:
    def test_defaults(self):
        config = AppConfig()
        assert config.DEFAULT_MODEL == "gemini-2.0-flash"
        assert "pdf" in config.SUPPORTED_FORMATS
        assert "png" in config.SUPPORTED_FORMATS
        assert config.MAX_FILE_SIZE_MB == 50

    def test_frozen(self):
        config = AppConfig()
        with pytest.raises(AttributeError):
            config.DEFAULT_MODEL = "other"


class TestPDFConfig:
    def test_defaults(self):
        config = PDFConfig()
        assert config.DPI == 200
        assert config.BASE_DPI == 72

    def test_frozen(self):
        config = PDFConfig()
        with pytest.raises(AttributeError):
            config.DPI = 300


class TestExtractionConfig:
    def test_defaults(self):
        config = ExtractionConfig()
        assert config.MAX_RETRIES == 5
        assert config.RETRY_MIN_WAIT == 2
        assert config.RETRY_MAX_WAIT == 30
        assert config.JPEG_QUALITY == 92
        assert config.TEMPERATURE == 0


class TestExcelColors:
    def test_all_hex(self):
        colors = ExcelColors()
        for field_name in vars(colors):
            value = getattr(colors, field_name)
            if isinstance(value, str):
                assert all(c in "0123456789ABCDEFabcdef" for c in value), (
                    f"{field_name}={value} is not a valid hex color"
                )


class TestCurrencySymbols:
    def test_includes_common_currencies(self):
        assert "R" in CURRENCY_SYMBOLS
        assert "$" in CURRENCY_SYMBOLS

    def test_is_tuple(self):
        assert isinstance(CURRENCY_SYMBOLS, tuple)
