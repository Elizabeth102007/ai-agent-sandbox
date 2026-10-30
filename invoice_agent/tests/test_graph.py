
import pytest
from openai import APIConnectionError, APITimeoutError
from httpx import Request

import studio.graph as graph_module
from studio.schemas import ExtractedInvoice, InvoiceResult, LineItem
from studio.validation import MAX_ATTEMPTS


def make_valid_invoice() -> ExtractedInvoice:
    return ExtractedInvoice(
        vendor="Acme Supplies Ltd",
        invoice_number="INV-001",
        invoice_date="2026-10-20",
        currency="USD",
        line_items=[
            LineItem(
                description="Office supplies",
                quantity=2,
                unit_price=50,
                amount=100,
            )
        ],
        subtotal=100,
        tax=10,
        total=110,
    )


def make_invalid_invoice() -> ExtractedInvoice:
    return ExtractedInvoice(
        vendor="Acme Supplies Ltd",
        invoice_number=None,
        invoice_date="2026-10-20",
        currency="USD",
        line_items=[
            LineItem(
                description="Office supplies",
                quantity=2,
                unit_price=50,
                amount=100,
            )
        ],
        subtotal=100,
        tax=10,
        total=110,
    )


def make_initial_state() -> dict:
    return {
        "raw_text": "Sample invoice text",
        "invoice": None,
        "errors": [],
        "attempts": 0,
        "path": [],
        "result": None,
    }


@pytest.mark.asyncio
async def test_valid_invoice_succeeds_on_first_attempt(monkeypatch):
    async def fake_extract_invoice(raw_text, previous_errors):
        return make_valid_invoice()

    monkeypatch.setattr(
        graph_module, "extract_invoice", fake_extract_invoice
    )

    graph = graph_module.build_graph()
    final_state = await graph.ainvoke(make_initial_state())

    result = final_state["result"]

    assert isinstance(result, InvoiceResult)
    assert result.status == "validated"
    assert result.errors == []
    assert result.attempts == 1
    assert final_state["path"] == [
        "extract_fields",
        "validate",
        "format_output",
    ]


@pytest.mark.asyncio
async def test_invalid_invoice_then_valid_invoice_retries(monkeypatch):
    invoices = [make_invalid_invoice(), make_valid_invoice()]
    calls = []

    async def fake_extract_invoice(raw_text, previous_errors):
        calls.append(list(previous_errors))
        return invoices.pop(0)

    monkeypatch.setattr(
        graph_module, "extract_invoice", fake_extract_invoice
    )

    graph = graph_module.build_graph()
    final_state = await graph.ainvoke(make_initial_state())

    result = final_state["result"]

    assert result.status == "validated"
    assert result.errors == []
    assert result.attempts == 2
    assert len(calls) == 2
    assert calls[0] == []
    assert calls[1]  # Validation errors reached the next extraction.
    assert final_state["path"] == [
        "extract_fields",
        "validate",
        "extract_fields",
        "validate",
        "format_output",
    ]


@pytest.mark.asyncio
async def test_always_invalid_invoice_reaches_attempt_limit(monkeypatch):
    async def fake_extract_invoice(raw_text, previous_errors):
        return make_invalid_invoice()

    monkeypatch.setattr(
        graph_module, "extract_invoice", fake_extract_invoice
    )

    graph = graph_module.build_graph()
    final_state = await graph.ainvoke(make_initial_state())

    result = final_state["result"]

    assert result.status == "needs_review"
    assert result.errors
    assert result.attempts == MAX_ATTEMPTS
    assert final_state["path"][-1] == "flag_for_human"
    assert final_state["path"].count("extract_fields") == MAX_ATTEMPTS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception",
    [
        APITimeoutError(request=Request("POST", "https://api.openai.com")),
        APIConnectionError(request=Request("POST", "https://api.openai.com")),
    ],
)
async def test_transient_api_failures_retry_then_succeed(
    monkeypatch, exception
):
    calls = 0

    async def fake_extract_invoice(raw_text, previous_errors):
        nonlocal calls
        calls += 1

        if calls == 1:
            raise exception

        return make_valid_invoice()

    monkeypatch.setattr(
        graph_module, "extract_invoice", fake_extract_invoice
    )

    graph = graph_module.build_graph()
    final_state = await graph.ainvoke(make_initial_state())

    result = final_state["result"]

    assert result.status == "validated"
    assert result.attempts == 2
    assert calls == 2
    assert final_state["path"] == [
        "extract_fields",
        "validate",
        "extract_fields",
        "validate",
        "format_output",
    ]


@pytest.mark.asyncio
async def test_repeated_extraction_failures_end_in_review(monkeypatch):
    calls = 0

    async def fake_extract_invoice(raw_text, previous_errors):
        nonlocal calls
        calls += 1
        raise APITimeoutError(
            request=Request("POST", "https://api.openai.com")
        )

    monkeypatch.setattr(
        graph_module, "extract_invoice", fake_extract_invoice
    )

    graph = graph_module.build_graph()
    final_state = await graph.ainvoke(make_initial_state())

    result = final_state["result"]

    assert result.status == "needs_review"
    assert result.attempts == MAX_ATTEMPTS
    assert calls == MAX_ATTEMPTS
    assert result.invoice is None
    assert any("APITimeoutError" in error for error in result.errors)
    assert final_state["path"][-1] == "flag_for_human"


@pytest.mark.asyncio
async def test_validation_exception_propagates(monkeypatch):
    async def fake_extract_invoice(raw_text, previous_errors):
        return make_valid_invoice()

    def fake_validate_invoice(invoice):
        raise RuntimeError("Validator programming bug")

    monkeypatch.setattr(
        graph_module, "extract_invoice", fake_extract_invoice
    )
    monkeypatch.setattr(
        graph_module, "validate_invoice", fake_validate_invoice
    )

    graph = graph_module.build_graph()

    with pytest.raises(RuntimeError, match="Validator programming bug"):
        await graph.ainvoke(make_initial_state())
