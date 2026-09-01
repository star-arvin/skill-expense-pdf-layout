from datetime import date
from decimal import Decimal
from pathlib import Path

from expense_pdf_layout.models import (
    ClassifiedPage,
    DocumentState,
    DocumentType,
    PageInspection,
)


def classified_page(
    filename: str,
    document_type: DocumentType,
    service_date: date | None,
    *,
    amount: str | None = None,
    font_risk: bool = False,
    page_index: int = 0,
) -> ClassifiedPage:
    page = PageInspection(
        source=Path(filename),
        page_index=page_index,
        source_hash=(filename.encode("utf-8").hex() + "0" * 64)[:64],
        width_pt=595.0,
        height_pt=397.0,
        text="synthetic document",
        font_risk=font_risk,
        service_date=service_date,
        invoice_date=service_date,
        amount=Decimal(amount) if amount is not None else None,
        state=DocumentState.READABLE,
    )
    return ClassifiedPage(page, document_type, 1.0, ("synthetic",))

