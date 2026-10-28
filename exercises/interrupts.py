
from typing import Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command


# 1. Define the graph state
class OrderState(TypedDict):
    order_id: str
    reason: str
    approved: bool
    status: str


# 2. Define the nodes
def check_order(state: OrderState):
    print(f"Checking order {state['order_id']}")

    # Demo only: assume the order is eligible for cancellation.
    return {"status": "awaiting_approval"}


def request_approval(state: OrderState):
    # Pause here and expose this request to the application.
    decision = interrupt({
        "type": "order_cancellation",
        "order_id": state["order_id"],
        "reason": state["reason"],
        "question": "Approve this cancellation?",
    })

    # This executes after the graph is resumed.
    return {"approved": decision["approved"]}


def route_after_approval(
    state: OrderState,
) -> Literal["cancel", "reject"]:
    if state["approved"]:
        return "cancel"
    return "reject"


def cancel_order(state: OrderState):
    # Replace with a real order-service/API call.
    print(f"Cancelling {state['order_id']}")
    return {"status": "cancelled"}


def reject_cancellation(state: OrderState):
    print("Cancellation rejected")
    return {"status": "rejected"}


# 3. Build the graph
builder = StateGraph(OrderState)

builder.add_node("check_order", check_order)
builder.add_node("request_approval", request_approval)
builder.add_node("cancel", cancel_order)
builder.add_node("reject", reject_cancellation)

builder.add_edge(START, "check_order")
builder.add_edge("check_order", "request_approval")

builder.add_conditional_edges(
    "request_approval",
    route_after_approval,
    {
        "cancel": "cancel",
        "reject": "reject",
    },
)

builder.add_edge("cancel", END)
builder.add_edge("reject", END)

# 4. Compile with a checkpointer
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)


# 5. Start the workflow
config = {
    "configurable": {
        "thread_id": "order-123"
    }
}

initial_state = {
    "order_id": "ORD-123",
    "reason": "Customer requested cancellation",
    "approved": False,
    "status": "pending",
}

result = graph.invoke(initial_state, config)

# The graph pauses at request_approval.
print(result.get("__interrupt__"))


# 6. Simulate a human approving the cancellation
result = graph.invoke(
    Command(resume={"approved": True}),
    config,
)

print(result["status"])  # cancelled