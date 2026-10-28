
import pytest

from studio.schemas import ExtractedInvoice, LineItem
from studio.validation import validate_invoice


def make_valid_invoice() -> ExtractedInvoice:
    return ExtractedInvoice(
        vendor="Acme Supplies Ltd",
        invoice_number="INV-001",
        invoice_date="2026-10-20",
        due_date="2026-11-20",
        currency="USD",
        line_items=[
            LineItem(
                description="Office supplies",
                quantity=2,
                unit_price=50.00,
                amount=100.00,
            )
        ],
        subtotal=100.00,
        tax=10.00,
        total=110.00,
    )


def test_valid_invoice_has_no_errors():
    assert validate_invoice(make_valid_invoice()) == []


def test_missing_invoice_is_rejected():
    errors = validate_invoice(None)

    assert len(errors) == 1
    assert "invoice is missing" in errors[0]


def test_required_fields_are_checked():
    invoice = make_valid_invoice().model_copy(
        update={
            "vendor": None,
            "invoice_number": None,
            "invoice_date": None,
            "total": None,
            "line_items": [],
        }
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 5
    assert {error.split(":")[0] for error in errors} == {"Required fields"}
    assert any("vendor is missing" in error for error in errors)
    assert any("invoice number is missing" in error for error in errors)
    assert any("invoice date is missing" in error for error in errors)
    assert any("total is missing" in error for error in errors)
    assert any("line item is required" in error for error in errors)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("vendor", ""),
        ("vendor", "   "),
        ("invoice_number", ""),
        ("invoice_number", "   "),
    ],
)
def test_blank_required_text_fields_are_rejected(field, value):
    invoice = make_valid_invoice().model_copy(update={field: value})

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Required fields")
    assert "missing" in errors[0]


def test_total_none_produces_only_required_field_error():
    invoice = make_valid_invoice().model_copy(update={"total": None})

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Required fields")
    assert "total is missing" in errors[0]


def test_invalid_invoice_date_is_rejected():
    invoice = make_valid_invoice().model_copy(
        update={"invoice_date": "20/10/2026"}
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Date format")


def test_compact_iso_date_is_rejected_when_yyyy_mm_dd_is_required():
    invoice = make_valid_invoice().model_copy(
        update={"invoice_date": "20261020"}
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Date format")
    assert "YYYY-MM-DD" in errors[0]


def test_whitespace_only_invoice_date_gets_format_error():
    invoice = make_valid_invoice().model_copy(
        update={"invoice_date": "   "}
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Date format")


def test_missing_currency_has_missing_message():
    invoice = make_valid_invoice().model_copy(update={"currency": None})

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert "currency is missing" in errors[0]


def test_whitespace_only_currency_is_missing():
    invoice = make_valid_invoice().model_copy(update={"currency": "   "})

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert "currency is missing" in errors[0]


def test_invalid_currency_message_includes_found_value():
    invoice = make_valid_invoice().model_copy(update={"currency": "US"})

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert "US" in errors[0]
    assert "invalid" in errors[0].lower()


def test_currency_with_surrounding_whitespace_is_accepted():
    invoice = make_valid_invoice().model_copy(update={"currency": " USD "})

    assert validate_invoice(invoice) == []


def test_negative_amounts_and_quantities_are_rejected():
    invoice = make_valid_invoice().model_copy(
        update={
            "tax": -10.00,
            "line_items": [
                LineItem(
                    description="Office supplies",
                    quantity=-2,
                    unit_price=50.00,
                    amount=100.00,
                )
            ],
        }
    )

    errors = validate_invoice(invoice)

    assert {
        error.split(":")[0] for error in errors
    } == {
        "Non-negative amounts",
        "Non-negative line values",
        "Line calculation",
        "Total calculation",
    }


def test_line_calculation_mismatch_over_one_cent_is_rejected():
    invoice = make_valid_invoice().model_copy(
        update={
            "line_items": [
                LineItem(
                    description="Office supplies",
                    quantity=2,
                    unit_price=50.00,
                    amount=100.02,
                )
            ],
            "subtotal": 100.02,
            "total": 110.02,
        }
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Line calculation")


def test_one_cent_line_difference_is_allowed():
    invoice = make_valid_invoice().model_copy(
        update={
            "line_items": [
                LineItem(
                    description="Office supplies",
                    quantity=2,
                    unit_price=50.00,
                    amount=100.01,
                )
            ]
        }
    )

    assert validate_invoice(invoice) == []


def test_missing_line_calculation_value_names_the_field():
    invoice = make_valid_invoice().model_copy(
        update={
            "line_items": [
                LineItem(
                    description="Office supplies",
                    quantity=2,
                    unit_price=None,
                    amount=100.00,
                )
            ]
        }
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Line calculation")
    assert "line 1 is missing unit_price" in errors[0]


def test_missing_line_amount_skips_subtotal_check():
    invoice = make_valid_invoice().model_copy(
        update={
            "line_items": [
                LineItem(
                    description="Office supplies",
                    quantity=2,
                    unit_price=50.00,
                    amount=None,
                )
            ]
        }
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Line calculation")


def test_subtotal_mismatch_reports_both_affected_rules():
    invoice = make_valid_invoice().model_copy(update={"subtotal": 101.00})

    errors = validate_invoice(invoice)

    assert {error.split(":")[0] for error in errors} == {
        "Subtotal calculation",
        "Total calculation",
    }


def test_total_mismatch_is_rejected():
    invoice = make_valid_invoice().model_copy(update={"total": 111.00})

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Total calculation")


def test_tax_none_and_total_equal_to_subtotal_pass():
    invoice = make_valid_invoice().model_copy(
        update={"tax": None, "total": 100.00}
    )

    assert validate_invoice(invoice) == []


def test_tax_none_and_wrong_total_report_one_error_mentioning_tax():
    invoice = make_valid_invoice().model_copy(
        update={"tax": None, "total": 115.00}
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Total calculation")
    assert "tax" in errors[0].lower()
    assert "treated as 0" in errors[0].lower()


def test_subtotal_none_uses_line_amounts_and_valid_total_passes():
    invoice = make_valid_invoice().model_copy(update={"subtotal": None})

    assert validate_invoice(invoice) == []


def test_subtotal_none_and_wrong_total_report_one_error():
    invoice = make_valid_invoice().model_copy(
        update={"subtotal": None, "total": 111.00}
    )

    errors = validate_invoice(invoice)

    assert len(errors) == 1
    assert errors[0].startswith("Total calculation")
