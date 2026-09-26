import pytest

from pydantic_ai import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.function import AgentInfo, FunctionModel

from main import support_agent
from tools import CustomerSession, SupportResponse, get_default_seed_orders


def make_session() -> CustomerSession:
    return CustomerSession(
        customer_id="CUST-AGENT-001",
        orders=get_default_seed_orders(),
    )


def get_output_tool_name(info: AgentInfo) -> str:
    assert info.output_tools, "Expected SupportResponse output tool to exist."
    return info.output_tools[0].name


def make_final_output(
    info: AgentInfo,
    *,
    message: str,
    resolved: bool,
    actions_taken: list[str],
) -> ModelResponse:
    output_tool_name = get_output_tool_name(info)

    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name=output_tool_name,
                args={
                    "message": message,
                    "resolved": resolved,
                    "actions_taken": actions_taken,
                },
                tool_call_id="final-output-call",
            )
        ]
    )


@pytest.mark.asyncio
async def test_agent_calls_get_order_status_with_specific_order_id():
    observed = {
        "tool_called": False,
        "order_id": None,
    }

    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        if not observed["tool_called"]:
            available_tools = {
                tool.name
                for tool in info.function_tools
            }

            assert "get_order_status" in available_tools

            observed["tool_called"] = True
            observed["order_id"] = "ORD-101"

            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="get_order_status",
                        args={
                            "order_id": "ORD-101",
                        },
                        tool_call_id="order-lookup-1",
                    )
                ]
            )

        return make_final_output(
            info,
            message=(
                "Order ORD-101 (SaaS Enterprise License) is currently "
                "'shipped'. Estimated delivery: 2026-09-28."
            ),
            resolved=True,
            actions_taken=["LOOKUP_ORDER"],
        )

    model = FunctionModel(model_function)
    session = make_session()

    with support_agent.override(model=model):
        result = await support_agent.run(
            "Where is order ORD-101?",
            deps=session,
        )

    assert observed["tool_called"] is True
    assert observed["order_id"] == "ORD-101"

    assert isinstance(result.output, SupportResponse)

    assert result.output.message == (
        "Order ORD-101 (SaaS Enterprise License) is currently "
        "'shipped'. Estimated delivery: 2026-09-28."
    )
    assert result.output.resolved is True
    assert result.output.actions_taken == ["LOOKUP_ORDER"]

    history = str(result.all_messages())

    assert "ORD-101" in history
    assert "SaaS Enterprise License" in history
    assert "shipped" in history
    assert "2026-09-28" in history


@pytest.mark.asyncio
async def test_customer_session_dependencies_reach_tool():
    call_count = 0

    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        nonlocal call_count

        if call_count == 0:
            call_count += 1

            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="get_order_status",
                        args={
                            "order_id": "ORD-102",
                        },
                        tool_call_id="dependency-test-1",
                    )
                ]
            )

        call_count += 1

        return make_final_output(
            info,
            message=(
                "Order ORD-102 (Dependency Test Add-on) is currently "
                "'processing'. Estimated delivery: 2099-12-31."
            ),
            resolved=True,
            actions_taken=["LOOKUP_ORDER"],
        )

    model = FunctionModel(model_function)
    session = make_session()

    session.customer_id = "CUST-DEPENDENCY-999"
    session.orders["ORD-102"].item_name = "Dependency Test Add-on"
    session.orders["ORD-102"].status = "processing"
    session.orders["ORD-102"].estimated_delivery = "2099-12-31"

    with support_agent.override(model=model):
        result = await support_agent.run(
            "Check order ORD-102.",
            deps=session,
        )

    assert isinstance(result.output, SupportResponse)
    assert result.output.actions_taken == ["LOOKUP_ORDER"]

    history = str(result.all_messages())

    assert "ORD-102" in history
    assert "Dependency Test Add-on" in history
    assert "processing" in history
    assert "2099-12-31" in history


@pytest.mark.asyncio
async def test_agent_returns_actual_support_response_object():
    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        return make_final_output(
            info,
            message="Your request has been resolved.",
            resolved=True,
            actions_taken=[],
        )

    model = FunctionModel(model_function)
    session = make_session()

    with support_agent.override(model=model):
        result = await support_agent.run(
            "Can you help me?",
            deps=session,
        )

    assert isinstance(result.output, SupportResponse)

    assert result.output.message == "Your request has been resolved."
    assert result.output.resolved is True
    assert result.output.actions_taken == []


@pytest.mark.asyncio
async def test_invalid_ticket_priority_eventually_exhausts_tool_retries():
    call_count = 0

    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        nonlocal call_count

        call_count += 1

        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="create_support_ticket",
                    args={
                        "subject": "Invalid priority test",
                        "description": (
                            "This deliberately uses an invalid priority."
                        ),
                        "priority": "urgent",
                    },
                    tool_call_id=f"invalid-ticket-{call_count}",
                )
            ]
        )

    model = FunctionModel(model_function)
    session = make_session()

    with support_agent.override(model=model):
        with pytest.raises(UnexpectedModelBehavior):
            await support_agent.run(
                "Create a ticket with urgent priority.",
                deps=session,
            )

    assert session.tickets == []
    assert call_count > 1


@pytest.mark.asyncio
async def test_output_validator_retry_exhaustion_raises_unexpected_model_behavior():
    call_count = 0

    async def model_function(
        messages: list[ModelMessage],
        info: AgentInfo,
    ) -> ModelResponse:
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="escalate_to_human",
                        args={
                            "reason": (
                                "Customer explicitly requested human support."
                            )
                        },
                        tool_call_id="escalation-1",
                    )
                ]
            )

        return make_final_output(
            info,
            message="A human has been requested.",
            resolved=True,
            actions_taken=["ESCALATED"],
        )

    model = FunctionModel(model_function)
    session = make_session()

    with support_agent.override(model=model):
        with pytest.raises(UnexpectedModelBehavior):
            await support_agent.run(
                "I want to speak to a human.",
                deps=session,
            )

    assert session.escalated is True

    assert session.escalated_reason == (
        "Customer explicitly requested human support."
    )

    assert call_count > 1