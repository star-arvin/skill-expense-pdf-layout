#!/usr/bin/env python3
"""Inspect and classify a folder without creating output files."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from expense_pdf_layout.classify import classify_paths  # noqa: E402
from expense_pdf_layout.inspect import SUPPORTED_EXTENSIONS  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    args = parser.parse_args()
    paths = sorted(
        (
            path
            for path in args.input_dir.iterdir()
            if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: path.name.casefold(),
    )
    documents = classify_paths(paths)
    payload = {
        "documents": [
            {
                "file": item.page.source.name,
                "source_page": item.page.page_index + 1,
                "type": item.document_type.value,
                "confidence": item.confidence,
                "sha256": item.page.source_hash,
                "font_risk": item.page.font_risk,
            }
            for item in documents
        ]
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
