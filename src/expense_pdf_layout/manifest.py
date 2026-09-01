"""Privacy-safe output manifest generation."""

from __future__ import annotations

from pathlib import Path

from .models import LayoutPlan


def manifest_dict(plan: LayoutPlan, output: Path) -> dict[str, object]:
    sources: list[dict[str, object]] = []
    for output_page, placements in enumerate(plan.pages, start=1):
        for placement in placements:
            sources.append(
                {
                    "file": placement.source.name,
                    "sha256": placement.source_hash,
                    "type": placement.document_type.value,
                    "source_page": placement.page_index + 1,
                    "output_page": output_page,
                    "slot": placement.slot,
                    "render_mode": placement.render_mode.value,
                }
            )
    return {
        "schema_version": "1.0",
        "output": Path(output).name,
        "page_count": len(plan.pages),
        "sources": sources,
        "warnings": list(plan.warnings),
    }

