"""Read-only source inspection."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

import pymupdf as fitz

from .models import DocumentState, PageInspection, ProcessingError

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
DATE_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日"),
    re.compile(r"(?P<year>20\d{2})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})"),
)
AMOUNT_PATTERN = re.compile(
    r"(?:价税合计|票价|金额|合计|fare|amount|total)\s*[:：]?\s*(?:CNY|RMB|[¥￥])?\s*([0-9]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
RAILWAY_MARKERS = ("铁路电子客票", "铁路客票", "railway e-ticket", "railway ticket")
CJK_FONT_MARKERS = ("cjk", "song", "hei", "kai", "fang", "mincho", "gothic")


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_date(text: str) -> date | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                return date(*(int(match.group(name)) for name in ("year", "month", "day")))
            except ValueError:
                continue
    return None


def _first_amount(text: str) -> Decimal | None:
    match = AMOUNT_PATTERN.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except InvalidOperation:
        return None


def _has_font_risk(page: fitz.Page, filename: str, text: str) -> bool:
    searchable = f"{filename} {text}".casefold()
    if any(marker in searchable for marker in RAILWAY_MARKERS):
        return True
    for font in page.get_fonts(full=True):
        xref = font[0]
        font_name = " ".join(str(value) for value in font[3:5]).casefold()
        if xref == 0 and any(marker in font_name for marker in CJK_FONT_MARKERS):
            return True
    return False


def inspect_path(path: Path) -> tuple[PageInspection, ...]:
    """Inspect a supported source while proving its bytes did not change."""

    path = Path(path)
    if path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
        raise ProcessingError(f"unsupported input: {path.name}")
    if not path.is_file():
        raise ProcessingError(f"input is not a file: {path.name}")

    before = sha256_file(path)
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise ProcessingError(f"unreadable input: {path.name}") from exc

    try:
        if document.needs_pass:
            raise ProcessingError(f"password-protected input: {path.name}")
        inspected: list[PageInspection] = []
        for index, page in enumerate(document):
            text = page.get_text("text") if path.suffix.casefold() == ".pdf" else ""
            inspected.append(
                PageInspection(
                    source=path,
                    page_index=index,
                    source_hash=before,
                    width_pt=float(page.rect.width),
                    height_pt=float(page.rect.height),
                    text=text,
                    font_risk=_has_font_risk(page, path.name, text),
                    service_date=_first_date(text),
                    invoice_date=_first_date(text),
                    amount=_first_amount(text),
                    state=DocumentState.READABLE,
                )
            )
    finally:
        document.close()

    if sha256_file(path) != before:
        raise ProcessingError(f"source changed during inspection: {path.name}")
    return tuple(inspected)

