#!/usr/bin/env python3
"""Validate the portable SKILL.md contract without a host-specific SDK."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

ALLOWED_FIELDS = {"name", "description", "license", "metadata"}
REQUIRED_METADATA = {"title", "version", "author", "tags", "compatibility"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_skill(repository: Path) -> list[str]:
    repository = Path(repository).resolve()
    skill_file = repository / "SKILL.md"
    if not skill_file.is_file():
        return ["SKILL.md is missing"]
    content = skill_file.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", content, re.DOTALL)
    if not match:
        return ["SKILL.md frontmatter is invalid"]
    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return [f"SKILL.md frontmatter is invalid YAML: {exc}"]
    if not isinstance(frontmatter, dict):
        return ["SKILL.md frontmatter must be a mapping"]

    issues: list[str] = []
    extra = set(frontmatter) - ALLOWED_FIELDS
    missing = ALLOWED_FIELDS - set(frontmatter)
    if extra:
        issues.append(f"unsupported frontmatter fields: {', '.join(sorted(extra))}")
    if missing:
        issues.append(f"missing frontmatter fields: {', '.join(sorted(missing))}")

    name = frontmatter.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        issues.append("name must use lowercase hyphenated form")
    elif name != repository.name:
        issues.append("name must match the skill folder")

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.startswith("Use when"):
        issues.append("description must start with 'Use when'")
    elif len(description) > 50 or "|" in description or "->" in description:
        issues.append("description must be one portable line of at most 50 characters")

    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        issues.append("metadata must be a mapping")
    else:
        missing_metadata = REQUIRED_METADATA - set(metadata)
        if missing_metadata:
            issues.append(f"missing metadata keys: {', '.join(sorted(missing_metadata))}")

    for heading in (
        "## 一、技能定位",
        "## 二、技术栈约束",
        "## 三、核心能力",
        "## 四、使用指南",
        "## 五、最佳实践",
        "## 六、参考资料",
        "## 变更日志",
    ):
        if heading not in match.group(2):
            issues.append(f"missing required section: {heading}")
    if not (repository / "references" / "README.md").is_file():
        issues.append("references/README.md is missing")
    guide = repository / "docs" / "skill-guides" / repository.name / "index.md"
    if not guide.is_file():
        issues.append("published skill guide is missing")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    issues = validate_skill(args.repository)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print("Skill is valid!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
