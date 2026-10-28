
import pytest

from studio.schemas import ExtractedInvoice, InvoiceResult


def make_invoice() -> ExtractedInvoice:
    return ExtractedInvoice(
        vendor="Acme Supplies Ltd",
        invoice_number="INV-001",
        invoice_date="2026-10-20",
        currency="USD",
        subtotal=100.00,
        tax=10.00,
        total=110.00,
    )


def test_validated_result_with_invoice_and_no_errors_is_allowed():
    result = InvoiceResult(
        invoice=make_invoice(),
        errors=[],
        attempts=1,
        status="validated",
    )

    assert result.status == "validated"


def test_validated_result_with_errors_is_rejected():
    with pytest.raises(ValueError, match="A validated result must contain no errors "):
        InvoiceResult(
            invoice=make_invoice(),
            errors=["Total mismatch"],
            attempts=1,
            status="validated",
        )


def test_validated_result_without_invoice_is_rejected():
    with pytest.raises(ValueError, match="A validated result must contain an invoice"):
        InvoiceResult(
            invoice=None,
            errors=[],
            attempts=1,
            status="validated",
        )


def test_needs_review_without_errors_is_rejected():
    with pytest.raises(ValueError, match="Status 'needs_review' requires at least one error message."):
        InvoiceResult(
            invoice=make_invoice(),
            errors=[],
            attempts=3,
            status="needs_review",
        )


def test_needs_review_without_invoice_is_allowed_when_errors_exist():
    result = InvoiceResult(
        invoice=None,
        errors=["Extraction failed"],
        attempts=3,
        status="needs_review",
    )

    assert result.status == "needs_review"
    assert result.invoice is None
