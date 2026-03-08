# Invoice Extraction

Extract structured data from invoice PDFs and images using Google Gemini AI, aggregate by product family, and export to styled Excel.

## Features

- Upload PDFs or images (PNG, JPG, WEBP, BMP, TIFF)
- AI-powered extraction via LangChain + Gemini structured output
- Automatic product family grouping and aggregation
- Styled Excel export with summary rows and raw extraction sheet
- Re-run individual pages without re-processing the entire batch
- Stop/resume extraction with partial results preserved

## Quick Start

### 1. Install

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure API Key

Get a free Gemini API key from [aistudio.google.com](https://aistudio.google.com).

```bash
echo "GOOGLE_API_KEY=AIza...your_key" > .env
```

### 3. Run

```bash
streamlit run invoice_extraction/app.py
```

## Project Structure

```
invoice_extraction/
    app.py                  # Streamlit entry point (thin orchestration)
    config.py               # Centralized constants and settings
    schemas.py              # Pydantic models for structured LLM output
    invoice_extractor.py    # LangChain + Gemini extraction logic
    pdf_processor.py        # PDF-to-image conversion (PyMuPDF)
    aggregator.py           # Group line items by product family
    excel_exporter.py       # Styled Excel workbook builder (openpyxl)
    file_handler.py         # File upload → PageImage conversion
    gemini_manager.py       # API key validation and model listing
    exceptions.py           # Custom exception hierarchy
    logging_config.py       # Centralized logging setup
    ui/
        styles.py           # CSS styling
        sidebar.py          # Sidebar config panel
        session.py          # Streamlit session state helpers
        results.py          # Results display and Excel download
tests/
    conftest.py             # Shared fixtures
    test_aggregator.py      # Grouping, parsing, validation
    test_schemas.py         # Pydantic model tests
    test_excel_exporter.py  # Excel output tests
    test_config.py          # Config immutability
    test_invoice_extractor.py  # Base64, ExtractionResult
    test_pdf_processor.py   # PDF processing tests
```

## Development

```bash
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check invoice_extraction/ tests/
ruff format invoice_extraction/ tests/
```

## Notebook Usage

The extraction pipeline is usable standalone without Streamlit:

```python
from invoice_extraction.invoice_extractor import build_chain, extract_from_image

chain = build_chain(api_key="AIza...")
data = extract_from_image(chain, open("invoice.png", "rb").read())
print(data.vendor_name, data.total, data.line_items)
```

Or extract directly from a file path:

```python
from invoice_extraction.invoice_extractor import extract_from_file

data = extract_from_file("invoice.pdf")
```
