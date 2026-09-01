from pathlib import Path

import pymupdf as fitz

from expense_pdf_layout.inspect import inspect_path
from tests.helpers import make_pdf, sha256_file


def test_inspect_pdf_extracts_stable_evidence(tmp_path: Path) -> None:
    source = make_pdf(
        tmp_path / "rail-ticket.pdf",
        "RAILWAY E-TICKET 2030-01-02 Fare: CNY 88.00",
    )
    before = sha256_file(source)
    pages = inspect_path(source)
    assert len(pages) == 1
    assert "RAILWAY E-TICKET" in pages[0].text
    assert pages[0].service_date.isoformat() == "2030-01-02"
    assert str(pages[0].amount) == "88.00"
    assert pages[0].source_hash == before
    assert sha256_file(source) == before


def test_inspect_png_reports_one_page(tmp_path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=400)
    pixmap = page.get_pixmap()
    source = tmp_path / "receipt.png"
    pixmap.save(source)
    document.close()
    pages = inspect_path(source)
    assert len(pages) == 1
    assert pages[0].width_pt > pages[0].height_pt
