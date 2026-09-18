import json
from tools import (FinanceSession,
                    add_transaction, 
                    get_transactions, 
                    categorize_spending, 
                    check_budget_status, 
                    calculate_savings_projection)

tools = [
    {
        "type": "function",
        "name": "add_transaction",
        "description": "Add a new financial transaction to the current session.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "The numeric monetary value of the transaction."
                },
                "category": {
                    "type": "string",
                    "description": "The category of the transaction (e.g., groceries, entertainment)."
                },
                "date": {
                    "type": "string",
                    "description": "The date of the transaction in YYYY-MM-DD format."
                },
                "description": {
                    "type": ["string", "null"],
                    "description": "An optional description or note for the transaction."
                }
            },
            "required": ["amount", "category", "date", "description"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_transactions",
        "description": "Retrieve transactions from the session, optionally filtered by category or date.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": ["string", "null"],
                    "description": "Filter transactions by a specific category. Pass null for all categories."
                },
                "date": {
                    "type": ["string", "null"],
                    "description": "Filter transactions by a specific date (YYYY-MM-DD). Pass null for all dates."
                }
            },
            "required": ["category", "date"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "categorize_spending",
        "description": "Calculate total spending grouped by category across all transactions in the session.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "check_budget_status",
        "description": "Check total spending for a category against a budget limit and see if it is over budget.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "The spending category to evaluate against the budget."
                },
                "limit": {
                    "type": "number",
                    "description": "The maximum budget limit set for the category."
                }
            },
            "required": ["category", "limit"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "calculate_savings_projection",
        "description": "Project total savings over a specified number of months based on income and expenses.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "monthly_income": {
                    "type": "number",
                    "description": "Total expected monthly income."
                },
                "monthly_expenses": {
                    "type": "number",
                    "description": "Total expected monthly expenses."
                },
                "months": {
                    "type": "integer",
                    "description": "The duration in months to project savings for."
                }
            },
            "required": ["monthly_income", "monthly_expenses", "months"],
            "additionalProperties": False
        }
    }
]


TOOL_REGISTRY = {
                 "add_transaction": add_transaction,
                 "get_transactions": get_transactions,
                 "categorize_spending": categorize_spending,
                 "check_budget_status": check_budget_status,
                 "calculate_savings_projection": calculate_savings_projection
                 }

def execute_tool(tool_call, session):
    tool_name = tool_call.name
    
    try:
        arguments = json.loads(tool_call.arguments)
    except json.JSONDecodeError as e:
        return json.dumps({
            "error": f"Invalid tool arguments: {e}"
        })
    
    tool_function = TOOL_REGISTRY.get(tool_name)
    if tool_function is None:
        return json.dumps({
            "error": f"Unknown tool requested: {tool_name}"
        })
    
    try:
        result = tool_function(session, **arguments)
        return json.dumps(result)  # Convert dict result from tool to JSON string
    
    except TypeError as e:
        return json.dumps({
            "error": f"Invalid arguments for {tool_name}: {e}"
        })
    except Exception as e:
        return json.dumps({
            "error": f"Error executing {tool_name}: {e}"
        })