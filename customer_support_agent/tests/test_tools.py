import pytest
from unittest.mock import MagicMock
from pydantic_ai import RunContext

from tools import (
    CustomerSession,
    Order,
    Ticket,
    get_order_status,
    create_support_ticket,
    get_ticket_status,
    escalate_to_human,
    get_default_seed_orders,
)

@pytest.fixture
def session() -> CustomerSession:
    return CustomerSession(
        customer_id="CUST-1001",
        orders=get_default_seed_orders()
    )


# get_order_status

@pytest.mark.asyncio
async def test_get_order_status_existing(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    result = await get_order_status(ctx, "ORD-101")
    assert result == "Order ORD-101 (SaaS Enterprise License) is currently 'shipped'. Estimated delivery: 2026-09-28."


@pytest.mark.asyncio
async def test_get_order_status_non_existent(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    result = await get_order_status(ctx, "ORD-999")
    assert result == "Order 'ORD-999' was not found for customer CUST-1001."


# create_support_ticket

@pytest.mark.asyncio
async def test_create_support_ticket_side_effect(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    assert len(session.tickets) == 0
    res = await create_support_ticket(ctx, "Billing Issue", "Charged twice", "high")

    assert len(session.tickets) == 1
    created_ticket = session.tickets[0]
    assert created_ticket.subject == "Billing Issue"
    assert created_ticket.description == "Charged twice"
    assert created_ticket.priority == "high"
    assert created_ticket.status == "open"
    assert res == f"Support ticket '{created_ticket.ticket_id}' successfully created with priority 'high'."


@pytest.mark.asyncio
async def test_create_support_ticket_unique_ids(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    res1 = await create_support_ticket(ctx, "Sub 1", "Desc 1", "low")
    res2 = await create_support_ticket(ctx, "Sub 2", "Desc 2", "medium")

    t1_id = session.tickets[0].ticket_id
    t2_id = session.tickets[1].ticket_id

    assert len(session.tickets) == 2
    assert t1_id != t2_id
    assert res1 == f"Support ticket '{t1_id}' successfully created with priority 'low'."
    assert res2 == f"Support ticket '{t2_id}' successfully created with priority 'medium'."


@pytest.mark.asyncio
async def test_create_support_ticket_priorities(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    for p in ["low", "medium", "high"]:
        await create_support_ticket(ctx, f"Sub {p}", f"Desc {p}", p)  # type: ignore

    assert len(session.tickets) == 3
    priorities = [t.priority for t in session.tickets]
    assert priorities == ["low", "medium", "high"]


# get_ticket_status 

@pytest.mark.asyncio
async def test_get_ticket_status_existing(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    ticket = Ticket(
        ticket_id="TCK-12345678",
        subject="Login Failure",
        description="Cannot reset password",
        priority="medium",
        status="in-progress"
    )
    session.tickets.append(ticket)

    res = await get_ticket_status(ctx, "TCK-12345678")
    assert res == "Ticket TCK-12345678 ('Login Failure') status: IN-PROGRESS. Priority: medium."


@pytest.mark.asyncio
async def test_get_ticket_status_non_existent(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    res = await get_ticket_status(ctx, "TCK-UNKNOWN")
    assert res == "Ticket 'TCK-UNKNOWN' not found in active session."


@pytest.mark.asyncio
async def test_get_ticket_status_multiple_tickets(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    t1 = Ticket(ticket_id="TCK-1", subject="Issue 1", description="D1", priority="low", status="open")
    t2 = Ticket(ticket_id="TCK-2", subject="Issue 2", description="D2", priority="high", status="resolved")
    session.tickets.extend([t1, t2])

    res = await get_ticket_status(ctx, "TCK-2")
    assert res == "Ticket TCK-2 ('Issue 2') status: RESOLVED. Priority: high."


# escalate_to_human

@pytest.mark.asyncio
async def test_escalate_to_human_sets_flags(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    assert session.escalated is False
    assert session.escalated_reason is None

    res = await escalate_to_human(ctx, "User requested agent")
    assert session.escalated is True
    assert session.escalated_reason == "User requested agent"
    assert res == "Customer conversation flagged for human escalation. Reason: User requested agent"


@pytest.mark.asyncio
async def test_escalate_to_human_overwrite_reason(session: CustomerSession):
    ctx = MagicMock(spec=RunContext)
    ctx.deps = session

    await escalate_to_human(ctx, "Initial Reason")
    assert session.escalated_reason == "Initial Reason"

    res = await escalate_to_human(ctx, "Updated Reason")
    assert session.escalated is True
    assert session.escalated_reason == "Updated Reason"
    assert res == "Customer conversation flagged for human escalation. Reason: Updated Reason"