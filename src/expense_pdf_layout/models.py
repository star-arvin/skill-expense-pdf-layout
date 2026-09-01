"""Domain contracts shared by inspection, planning, and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path


class ProcessingError(RuntimeError):
    """Raised when safe processing cannot continue."""


class DocumentType(str, Enum):
    RAILWAY_TICKET = "railway-ticket"
    ACCOMMODATION_INVOICE = "accommodation-invoice"
    TRANSPORT_INVOICE = "transport-invoice"
    ITINERARY = "itinerary"
    REIMBURSEMENT_FORM = "reimbursement-form"
    GENERAL_INVOICE = "general-invoice"
    UNCLASSIFIED = "unclassified"


class RenderMode(str, Enum):
    AUTO = "auto"
    RASTER = "raster"
    VECTOR = "vector"


class DocumentState(str, Enum):
    DISCOVERED = "discovered"
    READABLE = "readable"
    CLASSIFIED = "classified"
    GROUPED = "grouped"
    RENDERED = "rendered"
    VALIDATED = "validated"
    NEEDS_ATTENTION = "needs-attention"


@dataclass(frozen=True)
class PageInspection:
    source: Path
    page_index: int
    source_hash: str
    width_pt: float
    height_pt: float
    text: str
    font_risk: bool
    service_date: date | None
    invoice_date: date | None
    amount: Decimal | None
    state: DocumentState


@dataclass(frozen=True)
class ClassifiedPage:
    page: PageInspection
    document_type: DocumentType
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Placement:
    source: Path
    page_index: int
    slot: str
    render_mode: RenderMode
    document_type: DocumentType = DocumentType.UNCLASSIFIED
    source_hash: str = ""

    def __post_init__(self) -> None:
        if self.slot not in {"top", "bottom"}:
            raise ProcessingError("slot must be top or bottom")


@dataclass(frozen=True)
class LayoutPlan:
    pages: tuple[tuple[Placement, ...], ...]
    warnings: tuple[str, ...] = ()

