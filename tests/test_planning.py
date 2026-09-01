from datetime import date

import pytest

from expense_pdf_layout.models import DocumentType, ProcessingError, RenderMode
from expense_pdf_layout.plan import build_layout_plan, documents_are_related
from tests.test_support import classified_page


def test_same_type_pages_pair_before_cross_type_pages() -> None:
    documents = [
        classified_page(
            "return.pdf",
            DocumentType.RAILWAY_TICKET,
            date(2030, 1, 3),
            font_risk=True,
        ),
        classified_page(
            "outbound.pdf",
            DocumentType.RAILWAY_TICKET,
            date(2030, 1, 1),
            font_risk=True,
        ),
        classified_page(
            "ride.pdf",
            DocumentType.TRANSPORT_INVOICE,
            date(2030, 1, 4),
            amount="20.00",
        ),
        classified_page(
            "trip.pdf",
            DocumentType.ITINERARY,
            date(2030, 1, 4),
            amount="20.00",
        ),
    ]
    plan = build_layout_plan(documents)
    assert [item.source.name for item in plan.pages[0]] == ["outbound.pdf", "return.pdf"]
    assert [item.source.name for item in plan.pages[1]] == ["trip.pdf", "ride.pdf"]
    assert all(item.render_mode is RenderMode.RASTER for item in plan.pages[0])


def test_unclassified_page_stops_planning() -> None:
    with pytest.raises(ProcessingError, match="unclassified"):
        build_layout_plan(
            [classified_page("unknown.pdf", DocumentType.UNCLASSIFIED, None)]
        )


def test_unmatched_document_uses_top_slot() -> None:
    plan = build_layout_plan(
        [classified_page("single.pdf", DocumentType.GENERAL_INVOICE, date(2030, 2, 1))]
    )
    assert len(plan.pages) == 1
    assert plan.pages[0][0].slot == "top"


def test_related_documents_match_on_near_date_or_equal_amount() -> None:
    itinerary = classified_page(
        "trip.pdf", DocumentType.ITINERARY, date(2030, 2, 1), amount="35.00"
    )
    transport = classified_page(
        "ride.pdf", DocumentType.TRANSPORT_INVOICE, date(2030, 2, 2), amount="40.00"
    )
    assert documents_are_related(itinerary, transport)


def test_forced_raster_mode_applies_to_every_page() -> None:
    plan = build_layout_plan(
        [classified_page("invoice.pdf", DocumentType.GENERAL_INVOICE, None)],
        render_mode=RenderMode.RASTER,
    )
    assert plan.pages[0][0].render_mode is RenderMode.RASTER
