# Cross-Host Expense PDF Layout Skill Design

Date: 2026-09-01  
Status: Approved architecture, pending written-spec review  
Repository: `star-arvin/skill-expense-pdf-layout`  
Initial release: `v1.0.0`  
License: MIT

## 1. Objective

Create a portable Agent Skill that turns a folder of reimbursement materials into a print-ready A4 PDF. The same canonical skill must be usable from Cursor, Work Buddy, Codex, and other hosts that support the open Agent Skills directory format.

The skill classifies materials, groups documents of the same type, lays out two compatible items vertically on each A4 page, and preserves the original visual appearance of documents whose PDF text or font layer is unreliable.

## 2. Target users and scope

Target users are knowledge workers and administrative staff preparing reimbursement evidence for printing.

The skill handles local PDF, PNG, and JPEG files. Its primary output is one new A4 PDF plus a machine-readable processing manifest. It may submit that PDF to a local printer only after an explicit print request.

The skill does not:

- fill, approve, upload, or submit reimbursement claims;
- alter accounting amounts, names, dates, tax information, or ticket content;
- infer missing business facts;
- overwrite source documents;
- upload reimbursement materials to a remote service;
- depend on a single agent host's proprietary tool API.

## 3. Portability architecture

### 3.1 Canonical package

The repository root is the canonical Agent Skill package. It follows the open Agent Skills layout:

```text
skill-expense-pdf-layout/
├── SKILL.md
├── README.md
├── LICENSE
├── pyproject.toml
├── agents/
│   └── openai.yaml
├── src/
│   └── expense_pdf_layout/
│       ├── __init__.py
│       ├── models.py
│       ├── inspect.py
│       ├── classify.py
│       ├── plan.py
│       ├── render.py
│       └── manifest.py
├── scripts/
│   ├── layout_expense_documents.py
│   └── inspect_expense_documents.py
├── references/
│   ├── README.md
│   ├── guides/
│   │   ├── getting-started.md
│   │   └── best-practices.md
│   ├── standards/
│   │   ├── classification.md
│   │   ├── layout.md
│   │   └── privacy.md
│   ├── templates/
│   │   └── layout-config.yaml
│   └── examples/
│       ├── getting-started.md
│       ├── common-cases.md
│       └── advanced-cases.md
├── docs/
│   └── skill-guides/
│       └── skill-expense-pdf-layout/
│           └── index.md
└── tests/
    ├── fixtures/
    ├── test_classification.py
    ├── test_layout.py
    ├── test_preservation.py
    ├── test_privacy.py
    └── test_cli.py
```

Host-specific files are optional adapters. They may describe discovery or invocation, but they cannot contain a second copy of the classification, layout, rendering, or safety logic.

### 3.2 Frontmatter compatibility

`SKILL.md` uses only portable frontmatter fields:

```yaml
---
name: skill-expense-pdf-layout
description: Use when arranging expense PDFs for A4 printing.
license: MIT
metadata:
  title: 报销材料分类与 A4 拼版
  version: "1.0.0"
  author: star-arvin
  tags: pdf, expense, invoice, printing
  compatibility: Python 3.10+ with PyMuPDF 1.x on macOS, Windows, or Linux.
---
```

The company-required title, version, author, and tags are preserved under the standard `metadata` mapping. Platform-only fields are kept outside the canonical frontmatter.

### 3.3 Host discovery

- Cursor installs or discovers the canonical folder through `.agents/skills/`, `.cursor/skills/`, or a GitHub repository link.
- Work Buddy imports or projects the canonical folder into its Agent Skills location.
- Codex discovers the same folder through `.agents/skills/` or its compatible skills directory.
- Other hosts can use `SKILL.md` directly or run the scripts without an agent.

## 4. Domain model and truth sources

### 4.1 Entities

- **Source document**: one user-provided file. Its bytes are immutable.
- **Document page**: one visible page extracted or rendered from a source document.
- **Document type**: a reusable category such as railway ticket, accommodation invoice, taxi invoice, itinerary, reimbursement form, or unclassified material.
- **Document group**: pages eligible to share an A4 output page.
- **Output page**: one portrait A4 page containing one or two placed items.
- **Processing manifest**: classification, ordering, rendering mode, source hash, warnings, and output-page mapping.
- **Print job**: an optional local action created only after explicit user authorization.

### 4.2 States

Each source moves through:

`discovered → readable → classified → grouped → rendered → validated`

An unreadable, encrypted, unsupported, or ambiguous source moves to `needs-attention`. Default execution stops before producing a misleading final result when any input remains in that state.

### 4.3 Sources of truth

- Source bytes are authoritative for content.
- Visible rendering is authoritative for appearance.
- Extracted text is evidence for classification only; it is never rewritten into the ticket or invoice.
- The manifest is authoritative for how inputs map to output pages.

## 5. Classification and ordering

Classification uses visible text, embedded text, page proportions, and filename hints. No single filename or organization-specific keyword is required.

Initial reusable types are:

- `railway-ticket`
- `accommodation-invoice`
- `transport-invoice`
- `itinerary`
- `reimbursement-form`
- `general-invoice`
- `unclassified`

Rules:

1. Classify by document purpose, not by issuer or employer name.
2. Group the same type before considering cross-type pairing.
3. Within a type, sort by service or travel date, then invoice date, then stable filename order.
4. Pair a remaining invoice with its related itinerary or reimbursement form when the relationship is supported by date, amount, or explicit document type.
5. Leave an unmatched item alone in the upper slot. Do not fabricate a relationship merely to fill a page.
6. Record uncertain classifications in the manifest and stop for user review.

## 6. Rendering and A4 layout

### 6.1 Page geometry

- Output size: portrait A4, 210 × 297 mm.
- Printable side margin: 8 mm.
- Standard page structure: two equal vertical slots.
- Every item keeps its original aspect ratio.
- Center items within their slots.
- Do not stretch, reflow, rewrite, or reconstruct document text.
- Crop only verified blank margins, never visible content.

### 6.2 Visual-preservation mode

Railway electronic tickets and any page with unembedded, substitute-prone, or otherwise unreliable fonts use visual-preservation mode:

1. Render the complete visible page at 300 DPI or higher.
2. Treat the rendered image as a single immutable object.
3. Place the image proportionally in the target slot.
4. Confirm that the output page contains the expected raster object and no reconstructed ticket text layer.

The user can force `raster`, `vector`, or `auto` mode. `auto` always selects raster mode for railway tickets and selects raster mode when font inspection indicates appearance risk.

### 6.3 Pairing examples

- Two railway tickets share one A4 page vertically.
- Two accommodation invoices share one A4 page vertically.
- One taxi invoice can share a page with its related itinerary.
- One unmatched invoice occupies the upper slot and leaves the lower slot blank.

## 7. Command-line contract

The deterministic entry point is:

```bash
python scripts/layout_expense_documents.py INPUT_DIR \
  --output OUTPUT.pdf \
  --manifest OUTPUT.manifest.json
```

Supported options include:

- `--dpi 300`
- `--render-mode auto|raster|vector`
- `--config PATH`
- `--dry-run`
- `--overwrite`

Default execution never overwrites an existing output. `--dry-run` performs discovery, classification, pairing, and validation planning without writing a PDF.

The script uses Python 3.10+ and PyMuPDF 1.24+. It must avoid hard-coded user paths, company names, printer names, host APIs, and operating-system-specific assumptions in the core layout path.

## 8. Printing contract

PDF creation and physical printing are separate operations.

- The skill submits a print job only when the user explicitly asks to print.
- Default print intent is one copy, A4, one-sided, monochrome.
- Before submission, the host checks the selected printer and supported options.
- If the host cannot guarantee monochrome or page size, it reports the limitation instead of pretending the setting applied.
- The skill reports the printer destination, copy count, and observed job identifier or status.

## 9. Error handling and rollback

Stop before final output when:

- an input is unreadable or password-protected;
- classification remains ambiguous;
- rendering clips visible content;
- output validation cannot confirm A4 geometry or source coverage;
- a required dependency is unavailable;
- the requested output already exists and `--overwrite` was not supplied.

Temporary files are written outside the source folder where possible. Final output is written to a temporary sibling file and atomically renamed after validation. Source hashes are recorded before and after processing to prove that inputs were unchanged.

If printing fails, retain the validated output PDF and report the print failure. Never regenerate or alter the PDF merely because a printer rejected the job.

## 10. Privacy and de-identification

The public repository contains no real employer, issuer, traveler, invoice number, tax identifier, phone number, address, internal host, local username, or private network address.

Fixtures and examples use synthetic names such as `示例科技有限公司`, generated identifiers, and non-routable example paths. A privacy test scans tracked files for forbidden terms, realistic identifiers, home-directory paths, and private network addresses.

The runtime does not upload source files or extracted text. Logs and manifests use filenames and hashes but avoid extracted personal fields unless the user explicitly requests a detailed local report.

## 11. Documentation and company maturity requirements

The release satisfies every company Must Have item and every relevant Should Have item:

- complete frontmatter information;
- clear positioning and differentiation;
- pinned major versions and runtime dependencies;
- concrete capabilities with input and output contracts;
- at least five dialogue examples;
- `references/README.md` navigation;
- published guide at `docs/skill-guides/skill-expense-pdf-layout/index.md`;
- configuration template;
- best practices and troubleshooting;
- getting-started, common-case, and advanced examples;
- semantic versioning, last-updated date, and changelog;
- runnable tests and synthetic fixtures.

`references/standards/` contains the detailed rules. `SKILL.md` remains concise enough for progressive loading and links to the relevant reference only when needed.

## 12. Test strategy

### 12.1 Unit tests

- classify each supported type from synthetic text and filenames;
- sort by service date and stable fallback order;
- pair same-type documents before related cross-type documents;
- preserve aspect ratio and printable margins;
- detect font-risk conditions;
- reject ambiguous, unreadable, and overwrite cases.

### 12.2 Integration tests

- six synthetic source documents produce the expected three A4 pages;
- two railway tickets produce two 300-DPI raster objects on one A4 page;
- ticket output contains no reconstructed ticket text layer;
- every input appears exactly once in the manifest;
- every output page is A4 portrait;
- all visible content stays within printable bounds;
- source hashes remain unchanged;
- all output pages render successfully.

### 12.3 Portability tests

- run the CLI on macOS, Windows, and Linux in GitHub Actions;
- validate `SKILL.md` against the open Agent Skills specification;
- verify the package can be placed under `.agents/skills/skill-expense-pdf-layout` without path edits;
- verify no script imports a host-specific SDK.

### 12.4 Privacy tests

- scan tracked text for organization-specific wording and local paths;
- scan fixtures for realistic invoice, tax, phone, identity, and account numbers;
- ensure generated manifests omit extracted personal fields by default.

## 13. Acceptance criteria

The skill is ready for `v1.0.0` only when:

1. The open-standard validator and company checklist pass.
2. All automated tests pass on macOS, Windows, and Linux.
3. A synthetic mixed folder is converted to the expected A4 grouping without changing any source hash.
4. Railway tickets are visibly identical to their rendered sources and are represented as images in the output.
5. The repository contains no identifiable company or personal information.
6. Cursor, Work Buddy, and Codex installation instructions all point to the same canonical package.
7. A fresh user can complete the getting-started example in five minutes.
8. The public GitHub repository is tagged `v1.0.0` after all checks pass.

## 14. Publication

Create the public repository `star-arvin/skill-expense-pdf-layout`. Publish only synthetic fixtures and documentation. Push the validated `main` branch, create tag `v1.0.0`, and include installation instructions for the generic `.agents/skills/` path plus host-specific discovery notes.

No release action may include the user's reimbursement PDFs, generated reimbursement output, browser state, local paths, or private-company terminology.
