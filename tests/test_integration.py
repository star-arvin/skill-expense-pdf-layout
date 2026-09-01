import json
import subprocess
import sys
from pathlib import Path

import pymupdf as fitz

from tests.helpers import make_pdf

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "layout_expense_documents.py"


def test_six_mixed_documents_produce_three_a4_pages(tmp_path: Path) -> None:
    inputs = tmp_path / "input"
    inputs.mkdir()
    fixtures = {
        "railway-ticket-01.pdf": "RAILWAY E-TICKET 2030-01-01 FARE: CNY 80.00",
        "railway-ticket-02.pdf": "RAILWAY E-TICKET 2030-01-03 FARE: CNY 90.00",
        "accommodation-01.pdf": "HOTEL ACCOMMODATION 2030-01-02 TOTAL: CNY 300.00",
        "accommodation-02.pdf": "HOTEL ACCOMMODATION 2030-01-03 TOTAL: CNY 400.00",
        "itinerary-01.pdf": "ITINERARY 2030-01-04 TOTAL: CNY 35.00",
        "transport-invoice-01.pdf": "TAXI SERVICE 2030-01-04 TOTAL: CNY 35.00",
    }
    for filename, text in fixtures.items():
        make_pdf(inputs / filename, text)
    output = tmp_path / "result.pdf"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(inputs), "--output", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["page_count"] == 3
    document = fitz.open(output)
    try:
        assert len(document) == 3
    finally:
        document.close()
