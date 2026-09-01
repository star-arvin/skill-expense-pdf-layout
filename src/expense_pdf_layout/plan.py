"""Deterministic grouping and A4 page planning."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

from .models import (
    ClassifiedPage,
    DocumentType,
    LayoutPlan,
    Placement,
    ProcessingError,
    RenderMode,
)

TYPE_PRIORITY = {
    DocumentType.RAILWAY_TICKET: 0,
    DocumentType.ACCOMMODATION_INVOICE: 1,
    DocumentType.TRANSPORT_INVOICE: 2,
    DocumentType.ITINERARY: 3,
    DocumentType.REIMBURSEMENT_FORM: 4,
    DocumentType.GENERAL_INVOICE: 5,
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
INVOICE_TYPES = {
    DocumentType.ACCOMMODATION_INVOICE,
    DocumentType.TRANSPORT_INVOICE,
    DocumentType.GENERAL_INVOICE,
}


def _date_key(value: date | None) -> date:
    return value or date.max


def _sort_key(document: ClassifiedPage) -> tuple[object, ...]:
    page = document.page
    return (
        TYPE_PRIORITY.get(document.document_type, 99),
        _date_key(page.service_date),
        _date_key(page.invoice_date),
        page.source.name.casefold(),
        page.page_index,
    )


def documents_are_related(left: ClassifiedPage, right: ClassifiedPage) -> bool:
    if left.page.amount is not None and left.page.amount == right.page.amount:
        return True
    left_date = left.page.service_date or left.page.invoice_date
    right_date = right.page.service_date or right.page.invoice_date
    return bool(left_date and right_date and abs((left_date - right_date).days) <= 1)


def _compatible_types(left: DocumentType, right: DocumentType) -> bool:
    values = {left, right}
    if values == {DocumentType.ITINERARY, DocumentType.TRANSPORT_INVOICE}:
        return True
    return DocumentType.REIMBURSEMENT_FORM in values and bool(values & INVOICE_TYPES)


def _resolved_mode(document: ClassifiedPage, requested: RenderMode) -> RenderMode:
    if requested is not RenderMode.AUTO:
        return requested
    if document.page.font_risk or document.page.source.suffix.casefold() in IMAGE_EXTENSIONS:
        return RenderMode.RASTER
    return RenderMode.VECTOR


def _placement(
    document: ClassifiedPage,
    slot: str,
    requested_mode: RenderMode,
) -> Placement:
    return Placement(
        source=Path(document.page.source),
        page_index=document.page.page_index,
        slot=slot,
        render_mode=_resolved_mode(document, requested_mode),
        document_type=document.document_type,
        source_hash=document.page.source_hash,
    )


def _page(
    documents: tuple[ClassifiedPage, ...],
    requested_mode: RenderMode,
) -> tuple[Placement, ...]:
    slots = ("top", "bottom")
    return tuple(
        _placement(document, slots[index], requested_mode)
        for index, document in enumerate(documents)
    )


def build_layout_plan(
    documents: Iterable[ClassifiedPage],
    render_mode: RenderMode = RenderMode.AUTO,
) -> LayoutPlan:
    ordered = sorted(tuple(documents), key=_sort_key)
    unclassified = [item.page.source.name for item in ordered if item.document_type is DocumentType.UNCLASSIFIED]
    if unclassified:
        raise ProcessingError(f"unclassified input: {', '.join(unclassified)}")
    if not ordered:
        raise ProcessingError("no supported documents found")

    grouped: dict[DocumentType, list[ClassifiedPage]] = {}
    for document in ordered:
        grouped.setdefault(document.document_type, []).append(document)

    pages: list[tuple[ClassifiedPage, ...]] = []
    remainders: list[ClassifiedPage] = []
    for document_type in sorted(grouped, key=lambda item: TYPE_PRIORITY.get(item, 99)):
        same_type = grouped[document_type]
        for index in range(0, len(same_type) - 1, 2):
            pages.append((same_type[index], same_type[index + 1]))
        if len(same_type) % 2:
            remainders.append(same_type[-1])

    used: set[int] = set()
    cross_type_pages: list[tuple[ClassifiedPage, ...]] = []
    for left_index, left in enumerate(remainders):
        if left_index in used:
            continue
        for right_index in range(left_index + 1, len(remainders)):
            if right_index in used:
                continue
            right = remainders[right_index]
            if _compatible_types(left.document_type, right.document_type) and documents_are_related(left, right):
                pair = (left, right)
                if {left.document_type, right.document_type} == {
                    DocumentType.ITINERARY,
                    DocumentType.TRANSPORT_INVOICE,
                }:
                    pair = tuple(
                        sorted(pair, key=lambda item: item.document_type is DocumentType.TRANSPORT_INVOICE)
                    )
                cross_type_pages.append(pair)
                used.update({left_index, right_index})
                break

    pages.extend(cross_type_pages)
    pages.extend((document,) for index, document in enumerate(remainders) if index not in used)
    placements = tuple(_page(page, render_mode) for page in pages)
    warnings = tuple(
        f"unmatched document placed alone: {page[0].source.name}"
        for page in placements
        if len(page) == 1
    )
    return LayoutPlan(placements, warnings)
