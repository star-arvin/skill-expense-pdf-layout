"""Issuer-neutral reimbursement document classification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .inspect import inspect_path
from .models import ClassifiedPage, DocumentType, PageInspection


@dataclass(frozen=True)
class ClassificationResult:
    document_type: DocumentType
    confidence: float
    evidence: tuple[str, ...]


TEXT_PATTERNS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.RAILWAY_TICKET: ("铁路电子客票", "铁路客票", "railway e-ticket", "railway ticket"),
    DocumentType.ACCOMMODATION_INVOICE: ("住宿费", "住宿服务", "hotel accommodation"),
    DocumentType.TRANSPORT_INVOICE: ("交通运输服务", "客运服务", "出租车", "taxi service"),
    DocumentType.ITINERARY: ("出行行程单", "行程单", "trip table", "itinerary"),
    DocumentType.REIMBURSEMENT_FORM: ("差旅费报销单", "费用报销单", "reimbursement form"),
    DocumentType.GENERAL_INVOICE: ("电子发票", "普通发票", "invoice"),
}

FILENAME_PATTERNS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.RAILWAY_TICKET: ("railway-ticket", "train-ticket", "rail-ticket", "铁路客票"),
    DocumentType.ACCOMMODATION_INVOICE: ("accommodation", "hotel-invoice", "住宿"),
    DocumentType.TRANSPORT_INVOICE: ("transport-invoice", "taxi-invoice", "交通"),
    DocumentType.ITINERARY: ("itinerary", "trip-table", "行程单"),
    DocumentType.REIMBURSEMENT_FORM: ("reimbursement-form", "报销单"),
    DocumentType.GENERAL_INVOICE: ("invoice", "发票"),
}


def classify_text(filename: str, text: str) -> ClassificationResult:
    normalized_text = text.casefold()
    normalized_name = filename.casefold()
    scores: dict[DocumentType, int] = {}
    evidence: dict[DocumentType, list[str]] = {}

    for document_type, patterns in TEXT_PATTERNS.items():
        for pattern in patterns:
            if pattern.casefold() in normalized_text:
                weight = 4 if document_type is DocumentType.GENERAL_INVOICE else 10
                scores[document_type] = scores.get(document_type, 0) + weight
                evidence.setdefault(document_type, []).append(f"text:{document_type.value}")
                break

    for document_type, patterns in FILENAME_PATTERNS.items():
        for pattern in patterns:
            if pattern.casefold() in normalized_name:
                weight = 1 if document_type is DocumentType.GENERAL_INVOICE else 3
                scores[document_type] = scores.get(document_type, 0) + weight
                evidence.setdefault(document_type, []).append(f"filename:{document_type.value}")
                break

    if not scores:
        return ClassificationResult(DocumentType.UNCLASSIFIED, 0.0, ("no-match",))
    highest = max(scores.values())
    winners = [document_type for document_type, score in scores.items() if score == highest]
    if len(winners) != 1:
        return ClassificationResult(DocumentType.UNCLASSIFIED, 0.0, ("ambiguous",))
    winner = winners[0]
    confidence = min(1.0, highest / 13.0)
    return ClassificationResult(winner, confidence, tuple(evidence[winner]))


def classify_page(page: PageInspection) -> ClassifiedPage:
    result = classify_text(page.source.name, page.text)
    return ClassifiedPage(page, result.document_type, result.confidence, result.evidence)


def classify_paths(paths: Iterable[Path]) -> tuple[ClassifiedPage, ...]:
    classified: list[ClassifiedPage] = []
    for path in sorted((Path(item) for item in paths), key=lambda item: item.as_posix().casefold()):
        classified.extend(classify_page(page) for page in inspect_path(path))
    return tuple(classified)
