import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _skill_parts() -> tuple[dict[str, object], str]:
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", content, re.DOTALL)
    assert match, "SKILL.md must contain valid YAML frontmatter"
    return yaml.safe_load(match.group(1)), match.group(2)


def test_frontmatter_is_portable_and_complete() -> None:
    metadata, _ = _skill_parts()
    assert ROOT.name == metadata["name"]
    assert set(metadata) == {"name", "description", "license", "metadata"}
    description = metadata["description"]
    assert isinstance(description, str)
    assert description.startswith("Use when")
    assert "\n" not in description
    assert "|" not in description and "->" not in description
    assert len(description) <= 50
    details = metadata["metadata"]
    assert isinstance(details, dict)
    assert {"title", "version", "author", "tags", "compatibility"} <= set(details)


def test_required_sections_references_and_examples_exist() -> None:
    _, body = _skill_parts()
    for heading in (
        "## 一、技能定位",
        "## 二、技术栈约束",
        "## 三、核心能力",
        "## 四、使用指南",
        "## 五、最佳实践",
        "## 六、参考资料",
        "## 变更日志",
    ):
        assert heading in body

    links = re.findall(r"\[[^]]+\]\((\.?/?(?:references|docs)/[^)]+)\)", body)
    assert links
    for link in links:
        assert (ROOT / link.removeprefix("./")).exists(), link

    assert (ROOT / "references" / "README.md").is_file()
    guide = ROOT / "docs" / "skill-guides" / ROOT.name / "index.md"
    assert guide.is_file()
    example_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [guide, *(ROOT / "references" / "examples").glob("*.md")]
    )
    assert example_text.count("> 用户：") >= 5

