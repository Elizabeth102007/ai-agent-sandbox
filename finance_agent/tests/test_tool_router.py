import json
from unittest.mock import MagicMock
from tools import FinanceSession
from tool_router import execute_tool


def test_execute_tool_success():
    """Test executing a valid tool with correct arguments updates session and returns success."""
    session = FinanceSession()
    
    # Construct mock tool call using MagicMock
    tool_call = MagicMock()
    tool_call.name = "add_transaction"
    tool_call.arguments = json.dumps({
        "amount": 50.0,
        "category": "groceries",
        "date": "2026-09-17",
        "description": "Weekly grocery shopping"
    })

    response_str = execute_tool(tool_call, session)
    response_data = json.loads(response_str)

    # Assertions
    assert response_data["amount"] == 50.0
    assert response_data["category"] == "groceries"
    assert len(session.transactions) == 1

def test_execute_tool_unknown_name():
    """Test executing a tool with an unmapped name returns an unknown tool error."""
    session = FinanceSession()
    
    tool_call = MagicMock()
    tool_call.name = "non_existent_tool"
    tool_call.arguments = json.dumps({"param": "value"})

    response_str = execute_tool(tool_call, session)
    response_data = json.loads(response_str)

    # Assertions
    assert "error" in response_data
    assert "Unknown tool requested:" in response_data["error"]

def test_execute_tool_malformed_json():
    """Test passing invalid JSON syntax for arguments returns a JSON decode error."""
    session = FinanceSession()
    
    tool_call = MagicMock()
    tool_call.name = "calculate_savings_projection"
    # Malformed JSON missing closing quote and brace
    tool_call.arguments = '{"monthly_savings": 50.0, "is_saving": true'

    response_str = execute_tool(tool_call, session)
    response_data = json.loads(response_str)

    # Assertions
    assert "error" in response_data
    assert "Invalid tool arguments:" in response_data["error"]

def test_execute_tool_type_error_missing_args():
    """Test passing arguments that violate the function signature catches TypeError cleanly."""
    session = FinanceSession()
    
    tool_call = MagicMock()
    tool_call.name = "check_budget_status"

    # Missing required positional parameter (limit)
    tool_call.arguments = json.dumps({"category": "entertainment"})

    response_str = execute_tool(tool_call, session)
    response_data = json.loads(response_str)

    # Assertions
    assert "error" in response_data
    assert "Invalid arguments for check_budget_status:" in response_data["error"]