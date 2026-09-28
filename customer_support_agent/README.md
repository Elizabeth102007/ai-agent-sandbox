# SaaS Customer Support Agent

An AI-powered SaaS customer support agent built with **Python, PydanticAI, and OpenAI**.

The project demonstrates how an agent can use tools, maintain per-customer session state, perform actions, return structured responses, validate its own output against application state, and handle model/API failures.

> **Note:** This is a learning/portfolio project. Customer data and orders are stored in memory and are not connected to a production database or real customer-support platform.

## Features

* Customer-specific session state using dependency injection
* Order status lookup
* Support ticket creation and status lookup
* Human escalation
* Structured responses using Pydantic models
* Tool calling with PydanticAI
* Output validation with `ModelRetry`
* Streaming agent responses
* Model/tool retry handling
* OpenAI API error handling
* Application logging
* Automated tests using `pytest` and `FunctionModel`

## Architecture

```text
                         ┌─────────────────────┐
                         │    Customer Input    │
                         │       (CLI)          │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   PydanticAI Agent  │
                         │    GPT-5-nano       │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
             get_order_status  create_ticket   get_ticket_status
                    │               │                │
                    └───────────────┼────────────────┘
                                    ▼
                          CustomerSession
                         ┌──────────────────┐
                         │ customer_id      │
                         │ orders           │
                         │ tickets          │
                         │ escalation state │
                         └────────┬─────────┘
                                  │
                                  ▼
                       Output Validator
                                  │
                                  ▼
                         SupportResponse
```

## Agent Architecture

The agent is defined with PydanticAI:

```python
support_agent = Agent(
    "openai:gpt-5-nano",
    deps_type=CustomerSession,
    output_type=SupportResponse,
    instructions=SYSTEM_INSTRUCTIONS,
    tools=[
        get_order_status,
        create_support_ticket,
        get_ticket_status,
        escalate_to_human,
    ],
    retries=3,
)
```

This demonstrates several important agent concepts:

* **`deps_type`** — provides the agent and its tools with access to the current customer session.
* **Tools** — allow the model to perform application-level operations rather than only generating text.
* **`output_type`** — requires the agent to produce a structured `SupportResponse`.
* **Retries** — allows recoverable model/tool validation failures to be retried.

## Dependency Injection & Session State

Each conversation receives a `CustomerSession`:

```python
@dataclass
class CustomerSession:
    customer_id: str
    orders: dict[str, Order]
    tickets: list[Ticket]
    escalated: bool
    escalated_reason: Optional[str]
```

The session is passed into the agent:

```python
result = await support_agent.run(
    user_input,
    deps=session,
)
```

Tools then access that state through `RunContext`:

```python
async def get_order_status(
    ctx: RunContext[CustomerSession],
    order_id: str,
) -> str:
    ...
```

This demonstrates how agent tools can operate on application state instead of being isolated functions.

## Tool Calling

The agent has four tools:

| Tool                    | Purpose                              | State Effect    |
| ----------------------- | ------------------------------------ | --------------- |
| `get_order_status`      | Looks up an order                    | Read            |
| `create_support_ticket` | Creates a support ticket             | Mutates session |
| `get_ticket_status`     | Looks up a ticket                    | Read            |
| `escalate_to_human`     | Flags conversation for human support | Mutates session |

For example, when a customer asks about an order, the agent can call:

```text
get_order_status(order_id="ORD-101")
```

The tool retrieves the actual order from the current `CustomerSession`, and the result is returned to the model before it produces the final response.

## Structured Output

The final agent response is represented by:

```python
class SupportResponse(BaseModel):
    message: str
    resolved: bool
    actions_taken: list[str]
```

This makes the agent's output predictable and machine-readable instead of relying on unstructured text.

`actions_taken` records important operations performed during the interaction:

```text
LOOKUP_ORDER
TICKET_CREATED
LOOKUP_TICKET
ESCALATED
```

## Output Validation

The project goes beyond schema validation by checking whether the model's response is consistent with actual application state.

For example, if the agent escalates a conversation, the response cannot claim that the issue was resolved:

```python
if ctx.deps.escalated and response.resolved:
    raise ModelRetry(...)
```

Similarly, the agent cannot claim that it created a ticket when no ticket exists in the session.

This uses PydanticAI's `ModelRetry` mechanism to send the validation failure back into the agent's retry process.

## Error Handling

The application separates different classes of failures:

```text
PydanticAI framework errors
        ↓
OpenAI connection/rate-limit errors
        ↓
Unexpected application errors
```

The CLI catches:

* `UnexpectedModelBehavior`
* `AgentRunError`
* `APIConnectionError`
* `RateLimitError`
* Unexpected exceptions

Application events and failures are written to:

```text
logs/support_agent.log
```

The logger also suppresses noisy HTTP/OpenAI logs so application-level events remain easier to inspect.

## Testing

The project uses `pytest` and tests the system at several levels.

### Tool Tests — `test_tools.py`

Tests the deterministic behavior of individual tools, including:

* Existing and missing orders
* Ticket creation
* Ticket state mutation
* Unique ticket IDs
* Ticket priorities
* Existing and missing tickets
* Multiple ticket lookups
* Human escalation
* Updating escalation reasons

### Agent Tests — `test_agent.py`

Uses PydanticAI's `FunctionModel` to test agent behavior without making real OpenAI API calls.

Tests include:

* Agent tool availability
* Order lookup through the agent
* Dependency/session state reaching tools
* Structured `SupportResponse` output
* Invalid tool arguments and retry exhaustion
* Output-validator retry exhaustion
* Agent message history containing tool results

### Output Validator Tests — `test_output_validator.py`

Tests the application's custom validation rules:

* Escalated conversation cannot be marked resolved
* Correctly escalated responses pass
* Normal resolved responses pass
* Claiming `TICKET_CREATED` without a ticket raises `ModelRetry`
* A real ticket allows the response to pass validation

### Error Handling Tests — `test_error_handling.py`

Tests propagation of important OpenAI exceptions, including:

* `RateLimitError`
* `APIConnectionError`
* `AuthenticationError`

These tests verify that API-level failures remain identifiable as their original exception types.

## Project Structure

```text
saas-customer-support-agent/
│
├── main.py
├── tools.py
├── logger.py
├── requirements.txt
├── .env
│
├── logs/
│   └── support_agent.log
│
└── tests/
    ├── test_tools.py
    ├── test_agent.py
    ├── test_output_validator.py
    └── test_error_handling.py
```

## Running the Project

### 1. Clone the repository

```bash
git clone <repository-url>
cd saas-customer-support-agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the OpenAI API key

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

### 5. Run the application

```bash
python main.py
```

### 6. Run the tests

```bash
pytest
```

## Technologies

* **Python**
* **PydanticAI**
* **OpenAI API**
* **Pydantic**
* **pytest**
* **asyncio**
* **python-dotenv**

## Key Concepts Demonstrated

This project focuses on practical AI-agent engineering concepts:

* Agent/tool architecture
* Function/tool calling
* Dependency injection
* Stateful agent interactions
* Structured outputs
* Output validation
* `ModelRetry`
* Retry exhaustion
* Async execution
* Streaming responses
* API exception handling
* Application logging
* Agent testing with `FunctionModel`
* Testing deterministic tools independently from the LLM

## Project Scope

The current implementation uses an **in-memory session** and seeded demonstration orders.

A production implementation could replace these components with:

```text
CLI / Webhook / Frontend
        ↓
FastAPI
        ↓
Customer Support Agent
        ↓
Tools / Business Logic
        ↓
PostgreSQL + External SaaS APIs
```

Possible future integrations include a persistent customer/order database, authentication, a web frontend, CRM/ticketing systems, and messaging channels such as WhatsApp.
