"""Validated A4 rendering with raster preservation for sensitive pages."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pymupdf as fitz

from .inspect import sha256_file
from .manifest import manifest_dict
from .models import LayoutPlan, Placement, ProcessingError, RenderMode

MM_TO_PT = 72.0 / 25.4
A4 = fitz.Rect(0, 0, 210 * MM_TO_PT, 297 * MM_TO_PT)
SIDE_MARGIN = 8 * MM_TO_PT


def _slot_rect(slot: str) -> fitz.Rect:
    usable_height = A4.height - 2 * SIDE_MARGIN
    slot_height = usable_height / 2
    top = SIDE_MARGIN if slot == "top" else SIDE_MARGIN + slot_height
    return fitz.Rect(SIDE_MARGIN, top, A4.width - SIDE_MARGIN, top + slot_height)


def _insert_raster(
    output_page: fitz.Page,
    placement: Placement,
    target: fitz.Rect,
    dpi: int,
) -> None:
    source = fitz.open(placement.source)
    try:
        page = source[placement.page_index]
        pixmap = page.get_pixmap(dpi=max(dpi, 300), alpha=False)
        output_page.insert_image(
            target,
            stream=pixmap.tobytes("png"),
            keep_proportion=True,
        )
    finally:
        source.close()


def _insert_vector(
    output_page: fitz.Page,
    placement: Placement,
    target: fitz.Rect,
) -> None:
    if placement.source.suffix.casefold() != ".pdf":
        raise ProcessingError(f"vector mode requires PDF input: {placement.source.name}")
    source = fitz.open(placement.source)
    try:
        output_page.show_pdf_page(
            target,
            source,
            placement.page_index,
            keep_proportion=True,
        )
    finally:
        source.close()


def validate_output(output: Path, expected_pages: int) -> None:
    try:
        document = fitz.open(output)
    except Exception as exc:
        raise ProcessingError("output PDF cannot be opened") from exc
    try:
        if len(document) != expected_pages:
            raise ProcessingError("output page count does not match the layout plan")
        for page in document:
            if abs(page.rect.width - A4.width) >= 0.2 or abs(page.rect.height - A4.height) >= 0.2:
                raise ProcessingError("output page is not portrait A4")
            page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2), alpha=False)
    finally:
        document.close()


def render_plan(
    plan: LayoutPlan,
    output: Path,
    manifest_path: Path,
    dpi: int = 300,
    overwrite: bool = False,
) -> dict[str, object]:
    output = Path(output)
    manifest_path = Path(manifest_path)
    if dpi < 72:
        raise ProcessingError("dpi must be at least 72")
    if not overwrite and output.exists():
        raise ProcessingError(f"output already exists: {output.name}")
    if not overwrite and manifest_path.exists():
        raise ProcessingError(f"manifest already exists: {manifest_path.name}")

    source_hashes = {
        placement.source: placement.source_hash or sha256_file(placement.source)
        for page in plan.pages
        for placement in page
    }
    temporary_output = output.with_name(f".{output.name}.tmp.pdf")
    temporary_manifest = manifest_path.with_name(f".{manifest_path.name}.tmp")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    document = fitz.open()
    output_replaced = False
    try:
        for placements in plan.pages:
            output_page = document.new_page(width=A4.width, height=A4.height)
            for placement in placements:
                target = _slot_rect(placement.slot)
                if not A4.contains(target):
                    raise ProcessingError("placement exceeds A4 page bounds")
                if placement.render_mode is RenderMode.RASTER:
                    _insert_raster(output_page, placement, target, dpi)
                elif placement.render_mode is RenderMode.VECTOR:
                    _insert_vector(output_page, placement, target)
                else:
                    raise ProcessingError("layout plan contains unresolved render mode")
        document.save(temporary_output, garbage=4, deflate=True)
        document.close()
        validate_output(temporary_output, len(plan.pages))
        for source, expected_hash in source_hashes.items():
            if sha256_file(source) != expected_hash:
                raise ProcessingError(f"source changed during rendering: {source.name}")

        payload = manifest_dict(plan, output)
        temporary_manifest.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_output, output)
        output_replaced = True
        os.replace(temporary_manifest, manifest_path)
        return payload
    except Exception:
        if not document.is_closed:
            document.close()
        temporary_output.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
        if output_replaced:
            output.unlink(missing_ok=True)
        raise
