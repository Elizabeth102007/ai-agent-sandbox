# AI Personal Finance Agent

A command-line personal finance agent built with **Python and the OpenAI Responses API**. It uses function calling to track transactions, analyze spending, check budgets, and calculate savings projections while maintaining financial data within the current session.

The project focuses on building a **custom agent loop** and demonstrates tool routing, state management, defensive tool execution, API error handling, logging, streaming, and automated testing.

## What It Does

The agent can:

* Add and retrieve financial transactions.
* Filter transactions by category or date.
* Summarize spending by category.
* Check spending against a category budget.
* Calculate savings projections.
* Maintain transaction state throughout a finance session.
* Decide which tool to call based on the user's request.
* Execute tool calls and return their results to the model.
* Stream the final response to the terminal.

> **Note:** Transaction data is stored only in memory and is lost when the session ends. No database or persistent storage is used.

## Architecture

```text
                    ┌──────────────────────┐
                    │      User Input      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Finance Agent     │
                    │  OpenAI Responses API│
                    └──────────┬───────────┘
                               │
                         Function Call
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Tool Router      │
                    │ Registry + Executor  │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
       Transactions      Spending/Budget   Savings Projection
          Tools             Analysis            Tool
             │                 │                 │
             └─────────────────┴─────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   FinanceSession     │
                    │    In-Memory State    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Agent Final Reply  │
                    │       (streamed)      │
                    └──────────────────────┘
```

## Custom Agent Loop

The project implements the agent loop directly instead of using an agent framework.

The model receives the conversation and available tool definitions. When it requests a tool, the application:

1. Receives the function call.
2. Parses the model-generated arguments.
3. Resolves the requested function through the tool registry.
4. Executes the function against the current `FinanceSession`.
5. Sends the result back to the model.
6. Repeats until the model produces a final response.

A `MAX_ITERATIONS` limit prevents the agent from remaining in an uncontrolled tool-calling loop.

This creates a clear separation between **LLM decision-making** and **application-controlled execution**.

## Tool Calling & Tool Routing

The agent uses function calling because financial operations need to interact with application state and perform deterministic calculations.

Available tools include:

* `add_transaction`
* `get_transactions`
* `categorize_spending`
* `check_budget_status`
* `calculate_savings_projection`

Each tool has a strict schema, and the `TOOL_REGISTRY` provides an explicit allowlist of functions that the agent is permitted to execute.

The router also handles malformed JSON arguments, unknown tools, invalid function arguments, and unexpected execution errors without crashing the application.

## Error Handling & Logging

OpenAI API calls explicitly handle:

* Connection errors
* Timeouts
* Authentication errors
* Rate-limit errors
* Unexpected exceptions

Tool execution separately handles malformed arguments, unknown tool names, invalid arguments, and unexpected tool failures.

The application also uses Python's `logging` module to record important events and errors while filtering unnecessary HTTP and SDK noise.

## Testing

The project uses **pytest** and tests the system at three levels:

### 1. Finance Tools

Tests verify the deterministic business logic, including:

* Adding transactions and optional descriptions.
* Required argument behavior.
* Filtering by category and date.
* Spending categorization.
* Empty-session behavior.
* Budget status when under, over, or at zero spending.
* Positive and negative savings projections.

### 2. Tool Router

The router tests verify that:

* Valid tool calls are executed correctly.
* Unknown tools are rejected.
* Malformed JSON arguments are handled.
* Missing or invalid function arguments are caught.

### 3. Agent Loop

OpenAI API calls are **mocked**, so agent behavior can be tested without making real API requests.

Tests cover:

* Direct responses without tool calls.
* Successful tool-call execution and result propagation.
* The `MAX_ITERATIONS` safeguard.
* Rate-limit handling.
* Streaming errors.
* The interactive finance-session exit flow.

Run the test suite with:

```bash
pytest
```

## Project Structure

```text
ai-agent-sandbox/
└── finance_agent/
    ├── main.py             # CLI and custom agent loop
    ├── tools.py            # Finance logic and session state
    ├── tool_router.py      # Tool schemas, registry, execution
    ├── logger.py           # Logging configuration
    ├── tests/
    │   ├── test_tools.py
    │   ├── test_tool_router.py
    │   └── test_main.py
    ├── .env                # Local API credentials
    ├── .env.example        # Environment variable template
    └── pyproject.toml      # Project/test configuration
```

## Technologies

* Python
* OpenAI Responses API
* Function Calling
* pytest
* unittest.mock
* python-dotenv
* Python logging

## Key Concepts Demonstrated

**Custom Agent Loop · Function Calling · Tool Routing · Stateful Sessions · Mocking · Automated Testing · Error Handling · Logging · Streaming · API Integration**
