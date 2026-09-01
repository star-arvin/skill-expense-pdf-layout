import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yaml", ".yml", ".txt", ".json", ""}


def repository_text_files(root: Path = ROOT) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return [
        root / name
        for name in result.stdout.splitlines()
        if (root / name).is_file() and (root / name).suffix.casefold() in TEXT_SUFFIXES
    ]


def privacy_issues(root: Path = ROOT) -> list[str]:
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
    }
    for path in repository_text_files(root):
        content = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(root).as_posix()
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


def test_repository_contains_no_identifying_content() -> None:
    assert privacy_issues() == []
