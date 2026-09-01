from pathlib import Path

from scripts.release_check import release_check

ROOT = Path(__file__).resolve().parents[1]


def test_release_gate_reports_missing_guide_and_private_network(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "private endpoint " + ".".join(("192", "168", "5", "9")),
        encoding="utf-8",
    )
    issues = release_check(tmp_path, run_commands=False, require_clean=False)
    assert any("guide" in issue for issue in issues)
    assert any("private network" in issue for issue in issues)


def test_real_repository_passes_validation_only_release_gate() -> None:
    assert release_check(ROOT, run_commands=False, require_clean=False) == []
