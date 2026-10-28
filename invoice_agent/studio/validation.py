
from datetime import date
from decimal import Decimal
import re
from typing import Any, Literal, Mapping

from studio.schemas import ExtractedInvoice


MAX_ATTEMPTS = 3
MONEY_TOLERANCE = Decimal("0.01")


def to_decimal(value: int | float) -> Decimal:
    """Convert a numeric value to Decimal for money calculations."""
    return Decimal(str(value))


def within_tolerance(actual: Decimal, expected: Decimal) -> bool:
    """Return True when the difference is at most one cent."""
    return abs(actual - expected) <= MONEY_TOLERANCE


def validate_invoice(invoice: ExtractedInvoice | None) -> list[str]:
    """Validate invoice data without modifying the extracted values."""
    errors: list[str] = []

    if invoice is None:
        return [
            "Required fields: invoice is missing; "
            "no invoice data is available."
        ]

    # Rule 1: Required fields.
    if not invoice.vendor or not invoice.vendor.strip():
        errors.append("Required fields: vendor is missing.")

    if not invoice.invoice_number or not invoice.invoice_number.strip():
        errors.append("Required fields: invoice number is missing.")

    if not invoice.invoice_date:
        errors.append("Required fields: invoice date is missing.")

    if invoice.total is None:
        errors.append("Required fields: total is missing.")

    if not invoice.line_items:
        errors.append("Required fields: at least one line item is required.")

    # Rule 2: Invoice date must be exactly YYYY-MM-DD and be a real date.
    if invoice.invoice_date:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", invoice.invoice_date):
            errors.append(
                f"Date format: invoice date {invoice.invoice_date!r} "
                "must use YYYY-MM-DD."
            )
        else:
            try:
                date.fromisoformat(invoice.invoice_date)
            except ValueError:
                errors.append(
                    f"Date format: invoice date {invoice.invoice_date!r} "
                    "is not a valid calendar date in YYYY-MM-DD format."
                )

    # Rule 3: Currency must contain exactly three letters.
    # Surrounding whitespace is ignored for validation.
    if invoice.currency is None or not invoice.currency.strip():
        errors.append("Currency format: currency is missing.")
    else:
        currency = invoice.currency.strip()
        if not re.fullmatch(r"[A-Za-z]{3}", currency):
            errors.append(
                f"Currency format: currency {invoice.currency!r} is invalid; "
                "expected exactly three letters."
            )

    # Rule 4: Monetary amounts and quantities must not be negative.
    money_fields = {
        "subtotal": invoice.subtotal,
        "tax": invoice.tax,
        "total": invoice.total,
    }

    for field_name, value in money_fields.items():
        if value is not None and to_decimal(value) < 0:
            errors.append(
                f"Non-negative amounts: {field_name}={value} is negative."
            )

    for index, item in enumerate(invoice.line_items, start=1):
        for field_name, value in (
            ("quantity", item.quantity),
            ("unit_price", item.unit_price),
            ("amount", item.amount),
        ):
            if value is not None and to_decimal(value) < 0:
                errors.append(
                    f"Non-negative line values: line {index} "
                    f"{field_name}={value} is negative."
                )

    # Rule 5: Each line's quantity × unit price must equal its amount.
    for index, item in enumerate(invoice.line_items, start=1):
        missing_fields = [
            field_name
            for field_name, value in (
                ("quantity", item.quantity),
                ("unit_price", item.unit_price),
                ("amount", item.amount),
            )
            if value is None
        ]

        if missing_fields:
            for field_name in missing_fields:
                errors.append(
                    f"Line calculation: line {index} is missing {field_name}."
                )
            continue

        calculated = to_decimal(item.quantity) * to_decimal(item.unit_price)
        reported = to_decimal(item.amount)

        if not within_tolerance(calculated, reported):
            difference = abs(calculated - reported)
            errors.append(
                f"Line calculation: line {index}, "
                f"quantity={item.quantity} * unit_price={item.unit_price} "
                f"gives {calculated}, but amount={reported}; "
                f"mismatch={difference}."
            )

    # Rule 6: Line amounts must sum to subtotal.
    # Skip if there are no lines or any line amount is missing.
    if (
        invoice.line_items
        and all(item.amount is not None for item in invoice.line_items)
        and invoice.subtotal is not None
    ):
        line_sum = sum(
            (to_decimal(item.amount) for item in invoice.line_items),
            start=Decimal("0"),
        )
        subtotal = to_decimal(invoice.subtotal)

        if not within_tolerance(line_sum, subtotal):
            difference = abs(line_sum - subtotal)
            errors.append(
                f"Subtotal calculation: line amounts sum to {line_sum}, "
                f"but subtotal={subtotal}; mismatch={difference}."
            )

    # Rule 7: Base amount + tax must equal total.
    # Skip if total is missing; Rule 1 already reports that.
    if invoice.total is not None:
        base_amount: Decimal | None = None

        if invoice.subtotal is not None:
            base_amount = to_decimal(invoice.subtotal)
        
        elif (
            invoice.line_items
            and all(item.amount is not None for item in invoice.line_items)
        ):
            base_amount = sum(
                (to_decimal(item.amount) for item in invoice.line_items),
                start=Decimal("0"),
            )

        # If neither base amount can be established, skip this check.
        if base_amount is not None:
            tax_missing = invoice.tax is None
            tax_amount = (
                Decimal("0")
                if tax_missing
                else to_decimal(invoice.tax)
            )

            calculated_total = base_amount + tax_amount
            reported_total = to_decimal(invoice.total)

            if not within_tolerance(calculated_total, reported_total):
                difference = abs(calculated_total - reported_total)
                tax_note = (
                    " Tax not found, treated as 0."
                    if tax_missing
                    else ""
                )
                errors.append(
                    f"Total calculation: base amount={base_amount} + "
                    f"tax={tax_amount} gives {calculated_total}, "
                    f"but total={reported_total}; mismatch={difference}."
                    f"{tax_note}"
                )

    return errors


def route(
    state: Mapping[str, Any],
) -> Literal["format_output", "extract_fields", "flag_for_human"]:
    """Choose the next graph node after validation."""
    
    if not state["errors"]:
        return "format_output"

    if state["attempts"] < MAX_ATTEMPTS:
        return "extract_fields"

    return "flag_for_human"
