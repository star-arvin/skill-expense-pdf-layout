import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import make_pdf

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "layout_expense_documents.py"


def _run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_dry_run_writes_no_files(tmp_path: Path) -> None:
    inputs = tmp_path / "input"
    inputs.mkdir()
    make_pdf(inputs / "invoice-01.pdf", "ELECTRONIC INVOICE")
    output = tmp_path / "result.pdf"
    result = _run(inputs, "--output", output, "--dry-run")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["page_count"] == 1
    assert not output.exists()
    assert not (tmp_path / "result.manifest.json").exists()


def test_real_run_writes_pdf_and_manifest(tmp_path: Path) -> None:
    inputs = tmp_path / "input"
    inputs.mkdir()
    make_pdf(inputs / "invoice-01.pdf", "ELECTRONIC INVOICE")
    output = tmp_path / "result.pdf"
    result = _run(inputs, "--output", output)
    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert (tmp_path / "result.manifest.json").exists()


def test_existing_output_returns_code_two(tmp_path: Path) -> None:
    inputs = tmp_path / "input"
    inputs.mkdir()
    make_pdf(inputs / "invoice-01.pdf", "ELECTRONIC INVOICE")
    output = tmp_path / "result.pdf"
    output.write_bytes(b"existing")
    result = _run(inputs, "--output", output)
    assert result.returncode == 2


def test_unclassified_document_returns_code_three(tmp_path: Path) -> None:
    inputs = tmp_path / "input"
    inputs.mkdir()
    make_pdf(inputs / "unknown.pdf", "MEETING NOTES")
    result = _run(inputs, "--output", tmp_path / "result.pdf")
    assert result.returncode == 3
    assert "unknown.pdf" in result.stderr


def test_unsupported_input_returns_code_four(tmp_path: Path) -> None:
    inputs = tmp_path / "input"
    inputs.mkdir()
    (inputs / "notes.txt").write_text("synthetic", encoding="utf-8")
    result = _run(inputs, "--output", tmp_path / "result.pdf")
    assert result.returncode == 4

