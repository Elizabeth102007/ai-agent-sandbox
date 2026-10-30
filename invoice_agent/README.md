# Invoice Agent

A LangGraph-based invoice extraction workflow that uses an LLM to extract structured invoice data, validates the extracted fields and arithmetic using deterministic Python logic, and retries extraction when validation fails.

If the retry limit is reached, the workflow flags the invoice for human review instead of guessing or silently correcting supplier-provided values.

## Workflow

```mermaid
flowchart TD
    A([Start]) --> B[Extract invoice fields]
    B --> C[Validate fields and arithmetic]
    C -->|No errors| D[Format validated result]
    C -->|Errors and attempts remain| B
    C -->|Retry limit reached| E[Flag for human review]
    D --> F([End])
    E --> F
```

## Project Structure

```text
invoice_agent/
├── .venv/
│
├── samples/
│   ├── 01_clean.txt
│   ├── 02_tax_exempt.txt
│   ├── 03_messy_layout.txt
│   ├── 04_wrong_total.txt
│   ├── 05_missing_invoice_number.txt
│   └── 06_multi_line.txt
│
├── tests/
│   ├── test_schemas.py
│   ├── test_validation.py
│   ├── test_routing.py
│   └── test_graph.py
│
├── studio/
│   ├── __init__.py
│   ├── agent.py
│   ├── graph.py
│   ├── schemas.py
│   ├── validation.py
│   ├── main.py
│   ├── langgraph.json
│   ├── .env
│   └── .env.example
│
├── .gitignore
├── pyproject.toml
├── uv.lock
├── README.md
└── LATER.md
```

## Main Components

- `studio/graph.py` — Defines the LangGraph state, extraction and validation nodes, conditional routing, and graph construction.
- `studio/schemas.py` — Defines the Pydantic models for extracted invoices and final results.
- `studio/validation.py` — Contains deterministic validation rules and routing decisions.
- `studio/main.py` — Application entry point for running invoice samples from the command line. Loads environment variables before graph execution.
- `studio/agent.py` — Exposes the graph for LangGraph development mode.
- `samples/` — Contains sample invoice documents.
- `tests/` — Contains automated tests for schemas, validation, routing, and graph execution.

## Model Initialization and Environment

The project uses `ChatOpenAI` with the `gpt-5-nano` model and structured output based on the `ExtractedInvoice` schema.

Model initialization is lazy and cached:

- Importing `studio/graph.py` does not load `.env` or construct an OpenAI client.
- `get_structured_model()` creates the model only when extraction first runs.
- `lru_cache` reuses the initialized structured model across subsequent extraction attempts.

Environment loading is handled by the application entry point, `studio/main.py`, using `load_dotenv()` before graph execution.

## Setup

Requirements:

- Python 3.12
- `uv`
- An OpenAI API key

Install dependencies from the project root:

```bash
uv sync
```

Create `studio/.env` using `studio/.env.example` as a template:

```dotenv
OPENAI_API_KEY=your_openai_api_key
```

Keep your actual `.env` file out of version control.

## Run an Invoice Sample

From the project root:

```bash
uv run python -m studio.main samples/01_clean.txt
```

The program prints the final invoice result and the graph execution path.

## Run Tests

```bash
uv run pytest
```

The tests cover:

- Pydantic schema validation.
- Required invoice fields and arithmetic checks.
- Conditional routing and retry limits.
- Graph execution, extraction failures, and review outcomes.

Tests should not require a real OpenAI API call when extraction is replaced with test doubles.

## Run LangGraph Development Mode

From the project root:

```bash
uv run langgraph dev --config studio/langgraph.json
```

The graph is exposed through the LangGraph Studio entry point defined in `studio/agent.py`.

## Current Scope

The workflow processes one invoice at a time. It supports structured extraction, deterministic validation, bounded retries, and escalation to `needs_review` when the retry limit is reached.

Supplier-provided monetary values are preserved, including values that contain arithmetic inconsistencies.

See [LATER.md](LATER.md) for deferred improvements.