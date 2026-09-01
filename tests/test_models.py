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
        text="rail ticket",
        font_risk=True,
        service_date=date(2030, 1, 2),
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
        Placement(
            source=Path("sample.pdf"),
            page_index=0,
            slot="left",
            render_mode=RenderMode.RASTER,
        )
