import json
from unittest.mock import MagicMock, patch
import pytest

from openai import RateLimitError
from tools import FinanceSession
from main import run_finance_agent, start_finance_session, MAX_ITERATIONS


@pytest.fixture
def base_messages():
    return [{"role": "system", "content": "Test system prompt"}]


@pytest.fixture
def finance_session():
    return FinanceSession()



# Standard Response (No Tool Calls)

@patch("main.client.responses.create")
def test_run_finance_agent_direct_response(mock_responses_create, 
                                            base_messages, 
                                            finance_session):
    """Test standard flow where LLM returns a plain response without requesting tools."""
    # item in the output list similar to what the OpenAI API would return
    mock_msg_item = MagicMock(type="message") 
    
    mock_loop_response = MagicMock()
    mock_loop_response.output = [mock_msg_item]

    mock_stream_event = MagicMock()
    mock_stream_event.type = "response.output_text.delta"
    mock_stream_event.delta = "Hello! How can I help you today?"

    mock_responses_create.side_effect = [
        mock_loop_response,      # First call in tool execution loop
        [mock_stream_event]     # Second call during final response streaming
    ]

    run_finance_agent(base_messages, finance_session)

    assert mock_responses_create.call_count == 2
    assert base_messages[-1] == {"role": "assistant", "content": "Hello! How can I help you today?"}



# Successful Tool Call Execution & Message Propagation


@patch("main.execute_tool")
@patch("main.client.responses.create")
def test_run_finance_agent_with_tool_call(mock_responses_create, 
                                          mock_execute_tool, 
                                          base_messages, 
                                          finance_session):
    """Test full agent loop when LLM triggers a tool call, executes router, and stream returns."""
    tool_call_item = MagicMock()
    tool_call_item.type = "function_call"
    tool_call_item.name = "add_transaction"
    tool_call_item.call_id = "call_abc123"

    mock_tool_loop_response = MagicMock()
    mock_tool_loop_response.output = [tool_call_item]

    mock_final_loop_response = MagicMock()
    mock_final_loop_response.output = []

    mock_execute_tool.return_value = json.dumps({
        "amount": 25.0,
        "category": "coffee",
        "date": "2026-09-18",
        "description": "latte"
    })

    mock_stream_event = MagicMock()
    mock_stream_event.type = "response.output_text.delta"
    mock_stream_event.delta = "Logged your $25 coffee transaction!"

    mock_responses_create.side_effect = [
        mock_tool_loop_response,   # Iteration 1: returns tool call
        mock_final_loop_response,  # Iteration 2: no tool calls -> break
        [mock_stream_event]        # Final stream
    ]

    run_finance_agent(base_messages, finance_session)

    mock_execute_tool.assert_called_once_with(tool_call_item, finance_session)

    output_messages = [m for m in base_messages if m.get("type") == "function_call_output"]
    assert len(output_messages) == 1
    assert output_messages[0]["call_id"] == "call_abc123"
    assert "latte" in output_messages[0]["output"]



# Max Iterations Safeguard

@patch("main.logger.warning")
@patch("main.execute_tool")
@patch("main.client.responses.create")
def test_run_finance_agent_max_iterations_cap(mock_responses_create, 
                                              mock_execute_tool, 
                                              mock_logger_warning, 
                                              base_messages, 
                                              finance_session):
    """Test agent loop stops when MAX_ITERATIONS is hit without concluding."""
    tool_call_item = MagicMock()
    tool_call_item.type = "function_call"
    tool_call_item.name = "get_transactions"
    tool_call_item.call_id = "call_loop_123"

    mock_infinite_tool_response = MagicMock()
    mock_infinite_tool_response.output = [tool_call_item]

    mock_execute_tool.return_value = json.dumps([])

    mock_stream_event = MagicMock()
    mock_stream_event.type = "response.output_text.delta"
    mock_stream_event.delta = "Iteration cap reached."

    mock_responses_create.side_effect = [mock_infinite_tool_response] * MAX_ITERATIONS + [[mock_stream_event]]

    run_finance_agent(base_messages, finance_session)

    assert mock_responses_create.call_count == MAX_ITERATIONS + 1
    assert mock_execute_tool.call_count == MAX_ITERATIONS
    mock_logger_warning.assert_called_once_with("Reached MAX_ITERATIONS without concluding tool execution.")



# OpenAI Error Handling (Rate Limit & Streaming Connection Errors)

@patch("main.logger.error")
@patch("main.client.responses.create")
def test_run_finance_agent_rate_limit_error(mock_responses_create, 
                                            mock_logger_error, 
                                            base_messages, 
                                            finance_session):
    """Test RateLimitError during iteration loop logs cleanly with exact logger string."""
    mock_response_obj = MagicMock()
    mock_response_obj.status_code = 429

    err_instance = RateLimitError(
        message="Rate limit exceeded",
        response=mock_response_obj,
        body=None
    )
    mock_responses_create.side_effect = err_instance

    run_finance_agent(base_messages, finance_session)

    mock_logger_error.assert_called_once_with("Rate Limit Error: %s", err_instance)


@patch("main.logger.error")
@patch("main.client.responses.create")
def test_run_finance_agent_streaming_exception(mock_responses_create, 
                                               mock_logger_error, 
                                               base_messages, 
                                               finance_session):
    """Test API exception occurring during final streaming phase matches exact logger string."""
    mock_loop_response = MagicMock()
    mock_loop_response.output = []

    err_instance = Exception("Stream network dropped")

    mock_responses_create.side_effect = [
        mock_loop_response,  # Loop succeeds
        err_instance         # Stream raises
    ]

    run_finance_agent(base_messages, finance_session)

    mock_logger_error.assert_called_once_with("Unexpected Error during streaming: %s", err_instance)



# User Session Loop (CLI Interaction)

@patch("main.run_finance_agent")
@patch("builtins.input")
def test_start_finance_session_exit_flow(mock_input, mock_run_agent):
    """Test user session loop accepts user prompt, passes to run_finance_agent, and exits on 'exit'."""
    mock_input.side_effect = [
        "How much did I spend on groceries?",
        "exit"
    ]

    start_finance_session()

    assert mock_run_agent.call_count == 1
    passed_messages = mock_run_agent.call_args[0][0]
    assert passed_messages[-1] == {"role": "user", "content": "How much did I spend on groceries?"}