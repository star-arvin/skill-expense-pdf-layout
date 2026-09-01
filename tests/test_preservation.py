import json
from pathlib import Path

import pytest

from expense_pdf_layout.inspect import inspect_path
from expense_pdf_layout.models import ClassifiedPage, DocumentType
from expense_pdf_layout.plan import build_layout_plan
from expense_pdf_layout.render import render_plan
from tests.helpers import make_pdf


def _single_plan(source: Path):
    page = inspect_path(source)[0]
    return build_layout_plan(
        [ClassifiedPage(page, DocumentType.GENERAL_INVOICE, 1.0, ("synthetic",))]
    )


def test_manifest_contains_mapping_without_extracted_text(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "invoice-01.pdf", "SYNTHETIC INVOICE AMOUNT 42.00")
    output = tmp_path / "result.pdf"
    manifest = tmp_path / "result.manifest.json"
    render_plan(_single_plan(source), output, manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["sources"][0]["file"] == source.name
    assert "text" not in payload["sources"][0]
    assert "SYNTHETIC INVOICE" not in manifest.read_text(encoding="utf-8")


def test_validation_failure_leaves_no_final_or_temporary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_pdf(tmp_path / "invoice-01.pdf", "SYNTHETIC INVOICE")
    output = tmp_path / "result.pdf"
    manifest = tmp_path / "result.manifest.json"

    def fail_validation(*_args, **_kwargs):
        raise RuntimeError("validation failed")

    monkeypatch.setattr("expense_pdf_layout.render.validate_output", fail_validation)
    with pytest.raises(RuntimeError, match="validation failed"):
        render_plan(_single_plan(source), output, manifest)
    assert not output.exists()
    assert not manifest.exists()
    assert not (tmp_path / ".result.pdf.tmp.pdf").exists()


def test_existing_output_requires_overwrite(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "invoice-01.pdf", "SYNTHETIC INVOICE")
    output = tmp_path / "result.pdf"
    output.write_bytes(b"existing")
    with pytest.raises(Exception, match="already exists"):
        render_plan(_single_plan(source), output, tmp_path / "manifest.json")
