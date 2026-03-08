"""
logging_config.py
Centralized logging setup for the invoice extraction pipeline.

All modules use get_logger() to obtain a child logger under the
'invoice_extraction' namespace, ensuring consistent formatting
and a single pair of handlers (file + console).
"""

import logging
import sys


def setup_logging(level: int = logging.INFO, log_file: str = "invoice_parser.log") -> None:
    """Configure the root 'invoice_extraction' logger with file and console handlers.

    Safe to call multiple times — skips if handlers already exist.
    """
    root_logger = logging.getLogger("invoice_extraction")

    if root_logger.handlers:
        return

    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — full debug trace
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)

    # Console handler — info and above
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the invoice_extraction namespace."""
    return logging.getLogger(f"invoice_extraction.{name}")
