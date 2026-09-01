from pathlib import Path

import pymupdf as fitz

from expense_pdf_layout.inspect import inspect_path
from expense_pdf_layout.models import ClassifiedPage, DocumentType
from expense_pdf_layout.plan import build_layout_plan
from expense_pdf_layout.render import A4, SIDE_MARGIN, render_plan
from tests.helpers import make_pdf, sha256_file


def _classified(path: Path, document_type: DocumentType, font_risk: bool = False) -> ClassifiedPage:
    inspected = inspect_path(path)[0]
    if font_risk and not inspected.font_risk:
        inspected = inspected.__class__(**{**inspected.__dict__, "font_risk": True})
    return ClassifiedPage(inspected, document_type, 1.0, ("synthetic",))


def test_render_preserves_railway_pages_as_images_and_builds_a4(tmp_path: Path) -> None:
    sources = [
        make_pdf(tmp_path / "rail-ticket-01.pdf", "RAILWAY E-TICKET ONE"),
        make_pdf(tmp_path / "rail-ticket-02.pdf", "RAILWAY E-TICKET TWO"),
        make_pdf(tmp_path / "stay-01.pdf", "ACCOMMODATION INVOICE ONE"),
        make_pdf(tmp_path / "stay-02.pdf", "ACCOMMODATION INVOICE TWO"),
    ]
    before = {path: sha256_file(path) for path in sources}
    documents = [
        _classified(sources[0], DocumentType.RAILWAY_TICKET, font_risk=True),
        _classified(sources[1], DocumentType.RAILWAY_TICKET, font_risk=True),
        _classified(sources[2], DocumentType.ACCOMMODATION_INVOICE),
        _classified(sources[3], DocumentType.ACCOMMODATION_INVOICE),
    ]
    plan = build_layout_plan(documents)
    output = tmp_path / "result.pdf"
    manifest = tmp_path / "result.manifest.json"
    result = render_plan(plan, output, manifest)

    assert result["page_count"] == 2
    rendered = fitz.open(output)
    try:
        assert len(rendered) == 2
        for page in rendered:
            assert abs(page.rect.width - A4.width) < 0.2
            assert abs(page.rect.height - A4.height) < 0.2
        railway_page = rendered[0]
        assert len(railway_page.get_images(full=True)) == 2
        assert railway_page.get_text().strip() == ""
        invoice_page = rendered[1]
        for block in invoice_page.get_text("blocks"):
            assert block[0] >= SIDE_MARGIN - 0.2
            assert block[2] <= A4.width - SIDE_MARGIN + 0.2
    finally:
        rendered.close()
    assert {path: sha256_file(path) for path in sources} == before

