#!/usr/bin/env python3
"""Run the local publication gate for this Agent Skill."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

EXPECTED_VERSION = "1.0.0"
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yaml", ".yml", ".txt", ".json", ""}
FORBIDDEN_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".zip"}
REQUIRED_FILES = {
    "SKILL.md",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "references/README.md",
    "references/guides/getting-started.md",
    "references/guides/best-practices.md",
    "references/templates/layout-config.yaml",
    "references/examples/getting-started.md",
    "references/examples/common-cases.md",
    "references/examples/advanced-cases.md",
    "docs/skill-guides/skill-expense-pdf-layout/index.md",
    ".github/workflows/test.yml",
}
DENYLIST_HASHES = {
    "3782074709f4762dd71de95ad503ed9af21674abf4b84d0d2fadd86d9587b064",
    "8e4fb9f3dbd38d16aff4960dc73850d88e3a28e93d70322f47f0f211fb12d630",
    "c98243b41fd830b58e9eefe0cd98f7fee24bfbd9ff7a36de865e2105aab5cd4f",
    "9888fb7da1155f982ca6505e5200098f41e471980f97719e99e99825dd5c5e9a",
    "17df46f430bccd65214df1d9d1e79d0ff5bde2b2ca36c41598f9bdc1b595de0f",
    "7e6700bdffca60b32513bc67596c1b53b4f0333a58cb4d2f8f381c4cebecbb81",
    "b9101c6e5ae854a5227fefbe02eb35b0cad68dc82de3fb252ce0c9cab1902495",
    "d80fc1424435adccc5cdf15589bdc158054afa1cbf116983ad12a8e73289e7c0",
}


def _repository_files(repository: Path) -> list[Path]:
    git_directory = repository / ".git"
    if git_directory.exists():
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return [repository / name for name in result.stdout.splitlines() if (repository / name).is_file()]
    return [
        path
        for path in repository.rglob("*")
        if path.is_file() and not any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in path.parts)
    ]


def _privacy_issues(repository: Path, files: list[Path]) -> list[str]:
    issues: list[str] = []
    patterns = {
        "absolute home path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
        "private network address": re.compile(
            r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
        ),
        "phone-like number": re.compile(r"(?<!\d)1\d{10}(?!\d)"),
        "tax-like identifier": re.compile(r"(?<![A-Z0-9])[A-Z0-9]{18}(?![A-Z0-9])"),
        "invoice-like identifier": re.compile(r"(?<!\d)\d{20}(?!\d)"),
        "non-example email": re.compile(r"\b[A-Z0-9._%+-]+@(?!example\.com\b)[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
        "credential-like value": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})\b"),
    }
    for path in files:
        if path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(repository).as_posix()
        for label, pattern in patterns.items():
            if pattern.search(content):
                issues.append(f"{relative}: {label}")
        for line_number, line in enumerate(content.splitlines(), start=1):
            for length in range(2, min(32, len(line)) + 1):
                for start in range(0, len(line) - length + 1):
                    digest = hashlib.sha256(line[start : start + length].encode("utf-8")).hexdigest()
                    if digest in DENYLIST_HASHES:
                        issues.append(f"{relative}:{line_number}: denied identifying phrase")
    return issues


def _version_issues(repository: Path) -> list[str]:
    issues: list[str] = []
    pyproject = repository / "pyproject.toml"
    skill = repository / "SKILL.md"
    changelog = repository / "CHANGELOG.md"
    if not all(path.is_file() for path in (pyproject, skill, changelog)):
        return ["version files are incomplete"]
    project_match = re.search(
        r"^version\s*=\s*[\"']([^\"']+)[\"']",
        pyproject.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    skill_content = skill.read_text(encoding="utf-8")
    frontmatter_match = re.match(r"\A---\n(.*?)\n---", skill_content, re.DOTALL)
    metadata_version = None
    if frontmatter_match:
        payload = yaml.safe_load(frontmatter_match.group(1))
        if isinstance(payload, dict) and isinstance(payload.get("metadata"), dict):
            metadata_version = str(payload["metadata"].get("version"))
    versions = {
        "pyproject.toml": project_match.group(1) if project_match else None,
        "SKILL.md": metadata_version,
        "CHANGELOG.md": EXPECTED_VERSION if f"[{EXPECTED_VERSION}]" in changelog.read_text(encoding="utf-8") else None,
    }
    for filename, version in versions.items():
        if version != EXPECTED_VERSION:
            issues.append(f"{filename}: version does not match {EXPECTED_VERSION}")
    return issues


def _command_issue(repository: Path, command: list[str], label: str) -> str | None:
    result = subprocess.run(command, cwd=repository, text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return None
    detail = (result.stdout + result.stderr).strip().splitlines()
    return f"{label} failed" + (f": {detail[-1]}" if detail else "")


def release_check(
    repository: Path,
    run_commands: bool = False,
    require_clean: bool = True,
) -> list[str]:
    repository = Path(repository).resolve()
    files = _repository_files(repository)
    relative_files = {path.relative_to(repository).as_posix() for path in files}
    issues = [f"missing required guide or release file: {name}" for name in sorted(REQUIRED_FILES - relative_files)]
    issues.extend(_version_issues(repository))
    issues.extend(_privacy_issues(repository, files))

    for path in files:
        relative = path.relative_to(repository).as_posix()
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            issues.append(f"{relative}: binary reimbursement or archive file is not allowed")
        if path.name.casefold() in {".env", ".ds_store", "cookies", "cookies.json", "token", "token.json"}:
            issues.append(f"{relative}: local runtime or credential file is not allowed")

    if require_clean and (repository / ".git").exists():
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
        if status.returncode != 0 or status.stdout.strip():
            issues.append("git worktree is not clean")

    if run_commands:
        for command, label in (
            ([sys.executable, "-m", "pytest", "-q"], "test suite"),
            ([sys.executable, "scripts/validate_skill.py", "."], "skill validation"),
        ):
            issue = _command_issue(repository, command, label)
            if issue:
                issues.append(issue)
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", nargs="?", default=".", type=Path)
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    issues = release_check(
        args.repository,
        run_commands=not args.skip_commands,
        require_clean=not args.allow_dirty,
    )
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print("Release check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

