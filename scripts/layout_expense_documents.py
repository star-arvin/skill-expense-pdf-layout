#!/usr/bin/env python3
"""Portable script entry point for expense document layout."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from expense_pdf_layout.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

