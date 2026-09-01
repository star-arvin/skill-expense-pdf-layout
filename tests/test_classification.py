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
    ],
)
def test_classification_uses_document_purpose(
    filename: str,
    text: str,
    expected: DocumentType,
) -> None:
    result = classify_text(filename, text)
    assert result.document_type is expected
    assert all("company" not in evidence.lower() for evidence in result.evidence)


def test_filename_hint_can_identify_railway_ticket() -> None:
    result = classify_text("railway-ticket-01.pdf", "")
    assert result.document_type is DocumentType.RAILWAY_TICKET
