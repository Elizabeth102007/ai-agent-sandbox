from dataclasses import dataclass, field
from typing import Literal, Optional
from pydantic import BaseModel, Field
from pydantic_ai import RunContext
import uuid

OrderStatus = Literal["processing", "shipped", "delivered", "cancelled", "returned"]
TicketPriority = Literal["low", "medium", "high"]
TicketStatus = Literal["open", "in-progress", "resolved", "closed"]

# data models and schemas 
class Order(BaseModel):
    order_id: str
    item_name: str
    status: OrderStatus
    estimated_delivery: str


class Ticket(BaseModel):
    ticket_id: str
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus


class SupportResponse(BaseModel):
    message: str = Field(description="The formal response to give the customer.")
    resolved: bool = Field(description="Whether the user's inquiry is resolved.")
    actions_taken: list[str] = Field(
        default_factory=list,
        description="List of core actions taken, e.g. ['LOOKUP_ORDER', 'ESCALATED']"
    )


# dependencies type
@dataclass
class CustomerSession:
    customer_id: str
    orders: dict[str, Order] = field(default_factory=dict)
    tickets: list[Ticket] = field(default_factory=list)
    escalated: bool = False
    escalated_reason: Optional[str] = None


# Seed data utility

def get_default_seed_orders() -> dict[str, Order]:
    """Generates default seed order data for testing as a pre-existing data."""
    return {
        "ORD-101": Order(
            order_id="ORD-101",
            item_name="SaaS Enterprise License",
            status="shipped",
            estimated_delivery="2026-09-28"
        ),
        "ORD-102": Order(
            order_id="ORD-102",
            item_name="Developer Add-on Tier",
            status="processing",
            estimated_delivery="2026-10-01"
        )
    }


# --- Asynchronous Agent Tools ---

async def get_order_status(ctx: RunContext[CustomerSession], order_id: str) -> str:
    order = ctx.deps.orders.get(order_id)
    if not order:
        return f"Order '{order_id}' was not found for customer {ctx.deps.customer_id}."
    return (
        f"Order {order.order_id} ({order.item_name}) is currently '{order.status}'. "
        f"Estimated delivery: {order.estimated_delivery}."
    )


async def create_support_ticket(
    ctx: RunContext[CustomerSession],
    subject: str,
    description: str,
    priority: TicketPriority
) -> str:
    ticket_id = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    new_ticket = Ticket(
        ticket_id=ticket_id,
        subject=subject,
        description=description,
        priority=priority,
        status="open"
    )
    ctx.deps.tickets.append(new_ticket)
    return f"Support ticket '{ticket_id}' successfully created with priority '{priority}'."


async def get_ticket_status(ctx: RunContext[CustomerSession], ticket_id: str) -> str:
    for ticket in ctx.deps.tickets:
        if ticket.ticket_id == ticket_id:
            return (
                f"Ticket {ticket.ticket_id} ('{ticket.subject}') status: {ticket.status.upper()}. "
                f"Priority: {ticket.priority}."
            )
    return f"Ticket '{ticket_id}' not found in active session."


async def escalate_to_human(ctx: RunContext[CustomerSession], reason: str) -> str:
    ctx.deps.escalated = True
    ctx.deps.escalated_reason = reason
    return f"Customer conversation flagged for human escalation. Reason: {reason}"