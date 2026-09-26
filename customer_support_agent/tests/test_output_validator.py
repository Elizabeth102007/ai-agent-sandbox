import pytest
from pydantic_ai import ModelRetry

from main import validate_support_response
from tools import (
    CustomerSession,
    SupportResponse,
    Ticket,
    get_default_seed_orders,
)


def make_session() -> CustomerSession:
    return CustomerSession(
        customer_id="CUST-TEST-001",
        orders=get_default_seed_orders(),
    )


def make_response(
    *,
    resolved: bool,
    actions_taken: list[str] | None = None,
) -> SupportResponse:
    return SupportResponse(
        message="Test support response.",
        resolved=resolved,
        actions_taken=actions_taken or [],
    )


def make_context(session: CustomerSession):
    return type("TestRunContext", (), {"deps": session})()


@pytest.mark.asyncio
async def test_escalated_true_and_resolved_true_raises_model_retry():
    session = make_session()
    session.escalated = True
    session.escalated_reason = "Issue requires human intervention."

    response = make_response(
        resolved=True,
        actions_taken=["ESCALATED"],
    )

    with pytest.raises(
        ModelRetry,
        match=r"Issue was escalated to a human; 'resolved' MUST be set to False\.",
    ):
        await validate_support_response(
            make_context(session),
            response,
        )


@pytest.mark.asyncio
async def test_escalated_true_and_resolved_false_returns_response_unchanged():
    session = make_session()
    session.escalated = True
    session.escalated_reason = "Issue requires human intervention."

    response = make_response(
        resolved=False,
        actions_taken=["ESCALATED"],
    )

    result = await validate_support_response(
        make_context(session),
        response,
    )

    assert result is response
    assert result.resolved is False
    assert result.actions_taken == ["ESCALATED"]


@pytest.mark.asyncio
async def test_not_escalated_and_resolved_true_returns_response_unchanged():
    session = make_session()
    session.escalated = False

    response = make_response(
        resolved=True,
        actions_taken=[],
    )

    result = await validate_support_response(
        make_context(session),
        response,
    )

    assert result is response
    assert result.resolved is True
    assert result.actions_taken == []


@pytest.mark.asyncio
async def test_ticket_created_without_ticket_raises_model_retry():
    session = make_session()

    assert session.tickets == []

    response = make_response(
        resolved=False,
        actions_taken=["TICKET_CREATED"],
    )

    with pytest.raises(
        ModelRetry,
        match=(
            r"You reported creating a ticket, but no ticket exists "
            r"in session state\. Do not claim this action unless "
            r"create_support_ticket was actually called\."
        ),
    ):
        await validate_support_response(
            make_context(session),
            response,
        )


@pytest.mark.asyncio
async def test_ticket_created_with_real_ticket_passes_validation():
    session = make_session()

    session.tickets.append(
        Ticket(
            ticket_id="TCK-TEST123",
            subject="Test ticket",
            description="Testing validator behavior.",
            priority="medium",
            status="open",
        )
    )

    response = make_response(
        resolved=False,
        actions_taken=["TICKET_CREATED"],
    )

    result = await validate_support_response(
        make_context(session),
        response,
    )

    assert result is response
    assert result.actions_taken == ["TICKET_CREATED"]
    assert len(session.tickets) == 1