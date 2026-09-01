# Portable Expense PDF Layout Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a portable Agent Skill that classifies reimbursement materials, groups compatible documents, preserves visually sensitive tickets as raster images, and creates validated A4 print PDFs without changing source files.

**Architecture:** A host-neutral Python package owns inspection, classification, pairing, rendering, manifests, and validation. Thin scripts expose the package as a CLI, while one open-standard `SKILL.md` and progressively loaded references make the same repository usable by Cursor, Work Buddy, Codex, and other Agent Skills hosts.

**Tech Stack:** Python 3.10+, PyMuPDF 1.x, PyYAML 6.x, pytest 8.x, GitHub Actions, Markdown, YAML.

**Spec:** `docs/superpowers/specs/2026-09-01-skill-expense-pdf-layout-design.md`

## Global Constraints

- Skill name and repository name are `skill-expense-pdf-layout`.
- The canonical package uses open Agent Skills fields only: `name`, `description`, `license`, and `metadata`.
- Company metadata lives under `metadata`: Chinese title, semantic version `1.0.0`, author `star-arvin`, tags, and compatibility.
- Core code supports macOS, Windows, and Linux and imports no host-specific SDK.
- Source PDF, PNG, and JPEG files are read-only; successful output creation must preserve every source hash.
- Output pages are portrait A4, use 8 mm side margins, and contain at most two vertically arranged items.
- Railway tickets and font-risk pages render as immutable source images at 300 DPI or higher.
- Physical printing requires a separate explicit user request; default intent is one copy, A4, one-sided, monochrome.
- Repository content uses only synthetic names, identifiers, amounts, addresses, and paths.
- Public release is MIT licensed, tagged `v1.0.0`, and contains no reimbursement source files.

---

### Task 1: Package foundation and domain contracts

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/expense_pdf_layout/__init__.py`
- Create: `src/expense_pdf_layout/models.py`
- Create: `tests/__init__.py`
- Create: `tests/helpers.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces: `DocumentType`, `RenderMode`, `DocumentState`, `PageInspection`, `ClassifiedPage`, `Placement`, `LayoutPlan`, `ProcessingError`.
- Produces: `sha256_file(path: Path) -> str` and `make_pdf(path: Path, text: str, width: float, height: float) -> Path` for tests.

- [ ] **Step 1: Write the failing model tests**

Create `tests/test_models.py` with tests that construct a `PageInspection`, verify enum values, and reject a placement whose slot is not `top` or `bottom`:

```python
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from expense_pdf_layout.models import (
    ClassifiedPage,
    DocumentState,
    DocumentType,
    PageInspection,
    Placement,
    ProcessingError,
    RenderMode,
)


def test_page_contract_keeps_source_identity() -> None:
    page = PageInspection(
        source=Path("sample.pdf"),
        page_index=0,
        source_hash="a" * 64,
        width_pt=595.0,
        height_pt=397.0,
        text="铁路电子客票",
        font_risk=True,
        service_date=date(2026, 1, 2),
        invoice_date=None,
        amount=Decimal("88.00"),
        state=DocumentState.READABLE,
    )
    classified = ClassifiedPage(
        page=page,
        document_type=DocumentType.RAILWAY_TICKET,
        confidence=1.0,
        evidence=("railway-text",),
    )
    assert classified.page.source_hash == "a" * 64
    assert classified.document_type.value == "railway-ticket"


def test_placement_rejects_unknown_slot() -> None:
    with pytest.raises(ProcessingError, match="slot"):
        Placement(source=Path("sample.pdf"), page_index=0, slot="left", render_mode=RenderMode.RASTER)
```

- [ ] **Step 2: Run the model test and verify RED**

Run: `python -m pytest tests/test_models.py -v`  
Expected: collection fails because `expense_pdf_layout.models` does not exist.

- [ ] **Step 3: Add packaging and exact domain types**

Create `pyproject.toml` with:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "expense-pdf-layout"
version = "1.0.0"
description = "Portable reimbursement document classification and A4 layout engine"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = [
  "PyMuPDF>=1.24,<2",
  "PyYAML>=6,<7",
]

[project.optional-dependencies]
test = ["pytest>=8,<9"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `src/expense_pdf_layout/models.py` with string enums and frozen dataclasses. `Placement.__post_init__` raises `ProcessingError("slot must be top or bottom")` for any other value. `LayoutPlan` contains `pages: tuple[tuple[Placement, ...], ...]` and `warnings: tuple[str, ...]`.

Create `src/expense_pdf_layout/__init__.py` that exports `__version__ = "1.0.0"`.

Create `.gitignore` with `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `dist/`, `build/`, and `*.tmp.pdf`.

- [ ] **Step 4: Add deterministic synthetic fixture helpers**

Create `tests/helpers.py`:

```python
from hashlib import sha256
from pathlib import Path

import fitz


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_pdf(path: Path, text: str, width: float = 595.0, height: float = 397.0) -> Path:
    document = fitz.open()
    page = document.new_page(width=width, height=height)
    page.insert_textbox(fitz.Rect(36, 36, width - 36, height - 36), text, fontsize=14)
    document.save(path)
    document.close()
    return path
```

- [ ] **Step 5: Run foundation tests and verify GREEN**

Run: `python -m pytest tests/test_models.py -v`  
Expected: 2 tests pass.

- [ ] **Step 6: Commit the foundation**

Run:

```bash
git add pyproject.toml .gitignore src tests/helpers.py tests/test_models.py
git commit -m "feat: define portable expense layout contracts"
```

### Task 2: Source inspection and generic classification

**Files:**
- Create: `src/expense_pdf_layout/inspect.py`
- Create: `src/expense_pdf_layout/classify.py`
- Create: `tests/test_inspection.py`
- Create: `tests/test_classification.py`

**Interfaces:**
- Consumes: Task 1 domain types.
- Produces: `inspect_path(path: Path) -> tuple[PageInspection, ...]`.
- Produces: `classify_page(page: PageInspection) -> ClassifiedPage`.
- Produces: `classify_paths(paths: Iterable[Path]) -> tuple[ClassifiedPage, ...]`.

- [ ] **Step 1: Write failing inspection tests**

Create tests that prove PDF inspection extracts text, dates, amounts, dimensions, hashes, and detects font risk without changing the source hash. Create a second test that opens a PNG and reports one readable page.

```python
from pathlib import Path

import fitz

from expense_pdf_layout.inspect import inspect_path
from tests.helpers import make_pdf, sha256_file


def test_inspect_pdf_extracts_stable_evidence(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "ticket.pdf", "铁路电子客票 2026年01月02日 票价：¥88.00")
    before = sha256_file(source)
    pages = inspect_path(source)
    assert len(pages) == 1
    assert "铁路电子客票" in pages[0].text
    assert pages[0].service_date.isoformat() == "2026-01-02"
    assert str(pages[0].amount) == "88.00"
    assert pages[0].source_hash == before
    assert sha256_file(source) == before


def test_inspect_png_reports_one_page(tmp_path: Path) -> None:
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 600, 400), False)
    pixmap.clear_with(255)
    source = tmp_path / "receipt.png"
    pixmap.save(source)
    pages = inspect_path(source)
    assert len(pages) == 1
    assert pages[0].width_pt > pages[0].height_pt
```

- [ ] **Step 2: Run inspection tests and verify RED**

Run: `python -m pytest tests/test_inspection.py -v`  
Expected: import fails because `inspect_path` does not exist.

- [ ] **Step 3: Implement read-only inspection**

In `inspect.py`, accept only `.pdf`, `.png`, `.jpg`, and `.jpeg`. Use `fitz.open(path)`, reject `document.needs_pass`, calculate SHA-256 before and after inspection, and raise `ProcessingError` if they differ. Extract dates with compiled patterns for `YYYY年MM月DD日`, `YYYY-MM-DD`, and `YYYY/MM/DD`. Extract the first currency amount following `价税合计`, `票价`, `金额`, or `合计`.

Font risk is true when the filename or visible text identifies a railway ticket, or when `page.get_fonts(full=True)` reports a non-embedded CJK font. Store page dimensions from `page.rect` and set state to `DocumentState.READABLE`.

- [ ] **Step 4: Run inspection tests and verify GREEN**

Run: `python -m pytest tests/test_inspection.py -v`  
Expected: 2 tests pass.

- [ ] **Step 5: Write failing classification tests**

Create `tests/test_classification.py` with parameterized cases for railway tickets, accommodation invoices, transport invoices, itineraries, reimbursement forms, general invoices, and unclassified pages. Include one filename-only railway case and one organization-neutrality assertion.

```python
import pytest

from expense_pdf_layout.classify import classify_text
from expense_pdf_layout.models import DocumentType


@pytest.mark.parametrize(
    ("filename", "text", "expected"),
    [
        ("rail.pdf", "电子发票（铁路电子客票）", DocumentType.RAILWAY_TICKET),
        ("stay.pdf", "电子发票 项目名称 住宿费", DocumentType.ACCOMMODATION_INVOICE),
        ("ride.pdf", "电子发票 交通运输服务 客运服务", DocumentType.TRANSPORT_INVOICE),
        ("trip.pdf", "出行行程单 TRIP TABLE", DocumentType.ITINERARY),
        ("form.pdf", "差旅费报销单", DocumentType.REIMBURSEMENT_FORM),
        ("invoice.pdf", "电子发票 普通发票", DocumentType.GENERAL_INVOICE),
        ("scan.pdf", "会议资料", DocumentType.UNCLASSIFIED),
)
def test_classification_uses_document_purpose(filename: str, text: str, expected: DocumentType) -> None:
    result = classify_text(filename, text)
    assert result.document_type is expected
    assert all("company" not in evidence.lower() for evidence in result.evidence)
```

- [ ] **Step 6: Run classification tests and verify RED**

Run: `python -m pytest tests/test_classification.py -v`  
Expected: import fails because `classify_text` does not exist.

- [ ] **Step 7: Implement scored, issuer-neutral classification**

Define reusable pattern tables keyed by `DocumentType`. Score text matches before filename matches. Return a small immutable `ClassificationResult` carrying type, confidence, and evidence. If no score is positive or two top types tie, return `UNCLASSIFIED` with confidence `0.0`.

`classify_page` forces `RenderMode.RASTER` later through `font_risk`; it does not alter the extracted text. `classify_paths` sorts paths by normalized POSIX name before inspection so identical input folders produce identical manifests.

- [ ] **Step 8: Run inspection and classification tests**

Run: `python -m pytest tests/test_inspection.py tests/test_classification.py -v`  
Expected: all tests pass.

- [ ] **Step 9: Commit inspection and classification**

Run:

```bash
git add src/expense_pdf_layout/inspect.py src/expense_pdf_layout/classify.py tests/test_inspection.py tests/test_classification.py
git commit -m "feat: inspect and classify reimbursement materials"
```

### Task 3: Pairing and page planning

**Files:**
- Create: `src/expense_pdf_layout/plan.py`
- Create: `tests/test_planning.py`

**Interfaces:**
- Consumes: `tuple[ClassifiedPage, ...]`.
- Produces: `build_layout_plan(documents: Iterable[ClassifiedPage], render_mode: RenderMode = RenderMode.AUTO) -> LayoutPlan`.
- Produces: `documents_are_related(left: ClassifiedPage, right: ClassifiedPage) -> bool`.

- [ ] **Step 1: Write failing planner tests**

Create synthetic `ClassifiedPage` values without opening files. Verify chronological order, same-type priority, related itinerary pairing, unmatched upper-slot placement, forced render mode, and fail-closed unclassified behavior.

```python
from datetime import date
from pathlib import Path

import pytest

from expense_pdf_layout.models import DocumentType, ProcessingError, RenderMode
from expense_pdf_layout.plan import build_layout_plan
from tests.test_support import classified_page


def test_same_type_pages_pair_before_cross_type_pages() -> None:
    documents = [
        classified_page("return.pdf", DocumentType.RAILWAY_TICKET, date(2026, 1, 3), font_risk=True),
        classified_page("outbound.pdf", DocumentType.RAILWAY_TICKET, date(2026, 1, 1), font_risk=True),
        classified_page("ride.pdf", DocumentType.TRANSPORT_INVOICE, date(2026, 1, 4), amount="20.00"),
        classified_page("trip.pdf", DocumentType.ITINERARY, date(2026, 1, 4), amount="20.00"),
    ]
    plan = build_layout_plan(documents)
    assert [item.source.name for item in plan.pages[0]] == ["outbound.pdf", "return.pdf"]
    assert [item.source.name for item in plan.pages[1]] == ["trip.pdf", "ride.pdf"]
    assert all(item.render_mode is RenderMode.RASTER for item in plan.pages[0])


def test_unclassified_page_stops_planning() -> None:
    with pytest.raises(ProcessingError, match="unclassified"):
        build_layout_plan([classified_page("unknown.pdf", DocumentType.UNCLASSIFIED, None)])
```

Create `tests/test_support.py` with a complete `classified_page` factory that populates Task 1 dataclasses using synthetic hashes and paths.

- [ ] **Step 2: Run planner tests and verify RED**

Run: `python -m pytest tests/test_planning.py -v`  
Expected: import fails because `build_layout_plan` does not exist.

- [ ] **Step 3: Implement deterministic planning**

In `plan.py`:

1. Reject any `UNCLASSIFIED` input and list its filename in the error.
2. Sort by document-type priority, service date, invoice date, and case-folded filename.
3. Pair adjacent items of the same type.
4. Collect odd remainders and pair `ITINERARY` with `TRANSPORT_INVOICE`, or `REIMBURSEMENT_FORM` with an invoice, only when `documents_are_related` observes equal amounts or dates within one day.
5. Place unmatched remainders alone in the upper slot.
6. Resolve `AUTO` to `RASTER` for `font_risk` pages and source images; otherwise use `VECTOR`.

Every page tuple contains one or two placements in top-to-bottom order.

- [ ] **Step 4: Run planner tests and verify GREEN**

Run: `python -m pytest tests/test_planning.py -v`  
Expected: all planner tests pass.

- [ ] **Step 5: Commit the planner**

Run:

```bash
git add src/expense_pdf_layout/plan.py tests/test_planning.py tests/test_support.py
git commit -m "feat: plan same-type and related document layouts"
```

### Task 4: Raster-safe A4 rendering, manifest, and validation

**Files:**
- Create: `src/expense_pdf_layout/render.py`
- Create: `src/expense_pdf_layout/manifest.py`
- Create: `tests/test_layout.py`
- Create: `tests/test_preservation.py`

**Interfaces:**
- Consumes: `LayoutPlan` and source paths.
- Produces: `render_plan(plan: LayoutPlan, output: Path, manifest_path: Path, dpi: int = 300, overwrite: bool = False) -> dict[str, object]`.
- Produces: `validate_output(output: Path, expected_pages: int) -> None`.
- Produces: `manifest_dict(plan: LayoutPlan, output: Path) -> dict[str, object]`.

- [ ] **Step 1: Write failing geometry and preservation tests**

Generate two synthetic railway-ticket PDFs and two accommodation invoices. Render a two-page plan and assert:

- both output pages are A4 portrait within 0.2 points;
- the railway page contains exactly two image objects;
- `get_text().strip()` is empty on the railway page;
- both invoice placements remain within the 8 mm margin;
- every source hash matches its pre-render value;
- output and manifest are absent after any validation exception.

Use `page.get_images(full=True)` and `page.get_image_rects(xref)` for observable assertions.

- [ ] **Step 2: Run renderer tests and verify RED**

Run: `python -m pytest tests/test_layout.py tests/test_preservation.py -v`  
Expected: import fails because `render_plan` does not exist.

- [ ] **Step 3: Implement A4 placement and image preservation**

In `render.py`, set:

```python
MM_TO_PT = 72.0 / 25.4
A4 = fitz.Rect(0, 0, 210 * MM_TO_PT, 297 * MM_TO_PT)
SIDE_MARGIN = 8 * MM_TO_PT
```

Build top and bottom slot rectangles. Use `fitz.Rect` containment checks before inserting content. For raster placement, render the visible source page with `page.get_pixmap(dpi=max(dpi, 300), alpha=False)` and insert its PNG bytes with `keep_proportion=True`. For vector placement, use `show_pdf_page` only for PDF sources; image sources always use raster mode.

Write to `output.with_name(f".{output.name}.tmp.pdf")`. Open the temporary file, validate page count and A4 geometry, close it, compare all source hashes, and then call `os.replace(temp_output, output)`. Write the manifest through the same temporary-and-replace pattern after the PDF succeeds.

- [ ] **Step 4: Implement a privacy-safe manifest**

`manifest_dict` contains:

```json
{
  "schema_version": "1.0",
  "output": "result.pdf",
  "page_count": 3,
  "sources": [
    {
      "file": "ticket-01.pdf",
      "sha256": "hex digest",
      "type": "railway-ticket",
      "output_page": 1,
      "slot": "top",
      "render_mode": "raster"
    }
  ],
  "warnings": []
}
```

Do not include extracted names, identifiers, addresses, phone numbers, or invoice text.

- [ ] **Step 5: Run renderer tests and verify GREEN**

Run: `python -m pytest tests/test_layout.py tests/test_preservation.py -v`  
Expected: all tests pass and the source hashes remain unchanged.

- [ ] **Step 6: Commit rendering and manifests**

Run:

```bash
git add src/expense_pdf_layout/render.py src/expense_pdf_layout/manifest.py tests/test_layout.py tests/test_preservation.py
git commit -m "feat: render validated raster-safe A4 output"
```

### Task 5: Command-line entry points and dry-run workflow

**Files:**
- Create: `src/expense_pdf_layout/cli.py`
- Create: `scripts/layout_expense_documents.py`
- Create: `scripts/inspect_expense_documents.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_integration.py`

**Interfaces:**
- Consumes: inspection, classification, planning, rendering.
- Produces: `main(argv: Sequence[str] | None = None) -> int`.
- Produces CLI JSON on stdout and stable nonzero exit codes on failure.

- [ ] **Step 1: Write failing CLI tests**

Use `subprocess.run` against `scripts/layout_expense_documents.py` and a synthetic input directory. Verify:

- `--dry-run` returns code 0, prints classification and grouping JSON, and writes no PDF;
- a real run writes both PDF and manifest;
- an existing output returns code 2 without `--overwrite`;
- an unclassified document returns code 3 and names only the filename;
- unsupported input returns code 4;
- six synthetic mixed documents produce three A4 pages.

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `python -m pytest tests/test_cli.py tests/test_integration.py -v`  
Expected: subprocess fails because the scripts do not exist.

- [ ] **Step 3: Implement CLI parsing and orchestration**

`cli.py` uses `argparse` with positional `input_dir` and options `--output`, `--manifest`, `--dpi`, `--render-mode`, `--config`, `--dry-run`, and `--overwrite`. Default manifest path is `<output-stem>.manifest.json`.

Load YAML configuration only when `--config` is provided. Accept `type_overrides` keyed by basename and validate values against `DocumentType`. Print UTF-8 JSON with `ensure_ascii=False`.

`scripts/layout_expense_documents.py` adds `../src` to `sys.path` relative to its own location, imports `main`, and exits with its return value. `scripts/inspect_expense_documents.py` runs only discovery and classification and prints the privacy-safe inspection summary.

- [ ] **Step 4: Run CLI and integration tests and verify GREEN**

Run: `python -m pytest tests/test_cli.py tests/test_integration.py -v`  
Expected: all tests pass.

- [ ] **Step 5: Run the complete suite**

Run: `python -m pytest -v`  
Expected: all tests pass with no warnings.

- [ ] **Step 6: Commit CLI behavior**

Run:

```bash
git add src/expense_pdf_layout/cli.py scripts tests/test_cli.py tests/test_integration.py
git commit -m "feat: add portable inspection and layout CLI"
```

### Task 6: Agent Skill instructions, company documentation, and de-identification

**Files:**
- Create: `SKILL.md`
- Create: `README.md`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `agents/openai.yaml`
- Create: `references/README.md`
- Create: `references/guides/getting-started.md`
- Create: `references/guides/best-practices.md`
- Create: `references/standards/classification.md`
- Create: `references/standards/layout.md`
- Create: `references/standards/privacy.md`
- Create: `references/templates/layout-config.yaml`
- Create: `references/examples/getting-started.md`
- Create: `references/examples/common-cases.md`
- Create: `references/examples/advanced-cases.md`
- Create: `docs/skill-guides/skill-expense-pdf-layout/index.md`
- Create: `scripts/validate_skill.py`
- Create: `tests/test_skill_package.py`
- Create: `tests/test_privacy.py`

**Interfaces:**
- Produces: one host-neutral `SKILL.md` whose scripts and references use only relative paths.
- Produces: company maturity mapping and five complete dialogue examples.

- [ ] **Step 1: Write failing package and privacy tests**

`test_skill_package.py` parses `SKILL.md` and asserts:

- parent folder and `name` match;
- description is a single line, starts with `Use when`, excludes `|` and `->`, and is at most 50 characters;
- only `name`, `description`, `license`, and `metadata` exist at the top level;
- metadata includes title, version, author, tags, and compatibility;
- the six required Chinese body sections and changelog exist;
- every relative reference exists;
- the company guide path and `references/README.md` exist;
- at least five dialogue examples exist across the guide and examples.

`test_privacy.py` scans tracked text and rejects:

- absolute home paths;
- `192.168.x.x`, `10.x.x.x`, and `172.16-31.x.x` addresses;
- phone-like 11-digit runs;
- tax-identifier-like 18-character uppercase alphanumeric runs;
- invoice-like 20-digit runs;
- email addresses outside `example.com`;
- any 2-to-32-character text substring whose SHA-256 digest matches this committed denylist hash set (the original identifying phrases remain outside the repository):

```text
3782074709f4762dd71de95ad503ed9af21674abf4b84d0d2fadd86d9587b064
8e4fb9f3dbd38d16aff4960dc73850d88e3a28e93d70322f47f0f211fb12d630
c98243b41fd830b58e9eefe0cd98f7fee24bfbd9ff7a36de865e2105aab5cd4f
9888fb7da1155f982ca6505e5200098f41e471980f97719e99e99825dd5c5e9a
17df46f430bccd65214df1d9d1e79d0ff5bde2b2ca36c41598f9bdc1b595de0f
7e6700bdffca60b32513bc67596c1b53b4f0333a58cb4d2f8f381c4cebecbb81
b9101c6e5ae854a5227fefbe02eb35b0cad68dc82de3fb252ce0c9cab1902495
d80fc1424435adccc5cdf15589bdc158054afa1cbf116983ad12a8e73289e7c0
```

- [ ] **Step 2: Run documentation tests and verify RED**

Run: `python -m pytest tests/test_skill_package.py tests/test_privacy.py -v`  
Expected: failures report missing `SKILL.md`, references, guide, and metadata.

- [ ] **Step 3: Write the concise portable SKILL.md**

Use the approved frontmatter from the spec. Body sections are:

1. 技能定位
2. 技术栈约束
3. 核心能力
4. 使用指南
5. 最佳实践
6. 参考资料
7. 变更日志

The execution contract instructs the host to inspect first, stop on ambiguous classification, use raster preservation for railway/font-risk pages, validate source hashes, and separate PDF creation from explicit printing. Link detailed rules rather than duplicating them.

- [ ] **Step 4: Write complete guides and synthetic cases**

Use only `示例科技有限公司`, `示例酒店`, `示例出行平台`, dates in 2030, short synthetic amounts, `000000******0000`, and relative paths such as `./sample-input`.

The getting-started guide includes install, dependency, dry-run, real-run, expected three-page output, and validation commands. Common cases cover two railway tickets, two accommodation invoices, an itinerary plus transport invoice, and one unmatched document. Advanced cases cover mixed folders, forced raster mode, and explicit type overrides.

The company guide includes five user/agent dialogues and an input/output table. The README explains installation under `.agents/skills/`, Cursor, Work Buddy, and Codex without duplicating the operational rules.

- [ ] **Step 5: Generate Codex UI metadata without changing the core skill**

Create `agents/openai.yaml`:

```yaml
interface:
  display_name: "Expense PDF Layout"
  short_description: "Classify receipts and build print-safe A4 PDFs"
  default_prompt: "Use $skill-expense-pdf-layout to inspect this folder and create a validated A4 reimbursement PDF without changing source files."
```

This file is an optional adapter and is not referenced by the core scripts.

- [ ] **Step 6: Run package, privacy, and open-standard validation**

Run:

```bash
python -m pytest tests/test_skill_package.py tests/test_privacy.py -v
python scripts/validate_skill.py .
```

Expected: all tests pass and validator prints `Skill is valid!`.

- [ ] **Step 7: Commit skill documentation**

Run:

```bash
git add SKILL.md README.md LICENSE CHANGELOG.md agents references docs/skill-guides tests/test_skill_package.py tests/test_privacy.py
git commit -m "docs: publish portable expense PDF layout skill"
```

### Task 7: Cross-platform CI, release gate, and GitHub publication

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `scripts/release_check.py`
- Create: `tests/test_release_check.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `release_check(repository: Path, run_commands: bool = False, require_clean: bool = True) -> list[str]`, returning an empty list only for a publishable tree under the selected checks.
- Produces: GitHub Actions matrix for Ubuntu, macOS, and Windows with Python 3.10 and 3.12.

- [ ] **Step 1: Write a failing release-gate test**

Create a temporary repository fixture missing a guide and containing a private IP. Assert that `release_check` returns both failures. Assert that `release_check(repository, run_commands=False, require_clean=False)` returns no failures for the real repository only after all required files exist.

- [ ] **Step 2: Run release-gate test and verify RED**

Run: `python -m pytest tests/test_release_check.py -v`  
Expected: import fails because `release_check` does not exist.

- [ ] **Step 3: Implement the release gate**

`scripts/release_check.py` verifies:

- clean git worktree;
- version `1.0.0` agrees across `pyproject.toml`, `SKILL.md`, and `CHANGELOG.md`;
- required company documentation exists;
- no tracked PDF, PNG, JPEG, TIFF, ZIP, token, cookie, or local runtime file exists outside approved synthetic assets;
- privacy scan passes;
- `python -m pytest -q` succeeds;
- skill validation succeeds;
- `git grep` finds no private paths or network addresses.

The command-line interface runs the full checks by default and accepts `--skip-commands` and `--allow-dirty` for CI and the pre-commit checkpoint. Exit 0 only when the issue list is empty; otherwise print one issue per line and exit 1.

- [ ] **Step 4: Add the GitHub Actions matrix**

The workflow checks out the repository, sets up Python, installs `.[test]`, runs `python -m pytest -q`, and invokes the release check in validation-only mode. Use only official `actions/checkout` and `actions/setup-python` actions pinned to current major versions.

- [ ] **Step 5: Run all release checks locally**

Run:

```bash
python -m pytest -q
python scripts/release_check.py . --allow-dirty
git diff --check
git status --short
```

Expected: tests pass, release check reports no issues, diff check is clean, and only intentional uncommitted release files appear before the final commit.

- [ ] **Step 6: Commit release automation**

Run:

```bash
git add .github scripts/release_check.py tests/test_release_check.py README.md CHANGELOG.md
git commit -m "ci: add cross-platform skill release gate"
```

After the commit, run `python scripts/release_check.py .` again and require a clean, fully validated result before creating the remote repository.

- [ ] **Step 7: Create and push the public GitHub repository**

Run:

```bash
gh repo create star-arvin/skill-expense-pdf-layout --public --source=. --remote=origin --description "Portable Agent Skill for classifying reimbursement materials and creating print-safe A4 PDFs"
git push -u origin main
git tag -a v1.0.0 -m "skill-expense-pdf-layout v1.0.0"
git push origin v1.0.0
```

- [ ] **Step 8: Verify the remote release**

Run:

```bash
gh repo view star-arvin/skill-expense-pdf-layout --json nameWithOwner,visibility,url,defaultBranchRef
gh api repos/star-arvin/skill-expense-pdf-layout/git/ref/tags/v1.0.0 --jq .ref
gh run list --repo star-arvin/skill-expense-pdf-layout --limit 5
```

Expected: repository is public, default branch is `main`, tag ref is `refs/tags/v1.0.0`, and the test workflow reaches a successful conclusion.
