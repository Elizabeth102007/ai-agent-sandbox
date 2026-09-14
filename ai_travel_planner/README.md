# AI Travel Planning Agent

A command-line AI travel planning agent built with **Python and the OpenAI Responses API**. It extracts a user's trip requirements, gathers real-world information through external APIs, performs calculations when needed, and generates a personalized travel plan.

The project demonstrates **structured outputs, function/tool calling, multi-step agent workflows, API integration, error handling, logging, and conversational memory**.

## What It Does

The agent can:

* Extract trip details such as destination, duration, budget, currency, and dates.
* Retrieve city coordinates and current weather.
* Look up country information.
* Convert currencies using live exchange-rate data.
* Calculate a total trip budget.
* Use multiple tools in sequence when one tool depends on another.
* Maintain conversation context for follow-up questions.
* Stream the final response to the terminal.

## Architecture

```text
                    ┌──────────────────────┐
                    │      User Input      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Structured Output    │
                    │   TripDetails        │
                    │   (Pydantic)         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Travel Agent      │
                    │  OpenAI Responses API│
                    └──────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
              Tool calling          Final response
                    │                     │
                    ▼                     ▼
          ┌─────────────────┐      ┌─────────────┐
          │   Tool Router   │      │   Streamed  │
          │  + Registry     │      │ Trip Plan   │
          └────────┬────────┘      └─────────────┘
                   │
          ┌────────┼────────┬──────────┐
          ▼        ▼        ▼          ▼
       Weather  Currency  Country   Budget
        APIs      API       API    Calculation
```

## Structured Outputs vs. Tool Calling

The project deliberately uses both for different purposes.

**Structured outputs** are used during the initial request because the goal is to reliably extract known fields from natural language. The `TripDetails` Pydantic model ensures the extracted data follows a predictable structure.

**Tool calling** is used during the planning stage because the model needs to decide **when a tool is necessary, which tool to use, and how tools should be chained together**. For example, the agent can first retrieve a city's coordinates and then use those coordinates to request its weather.

This separation keeps data extraction predictable while allowing the planning stage to behave dynamically.

## Error Handling

Error handling is implemented at both the **API integration** and **agent execution** levels.

* External API requests use timeouts and `raise_for_status()` to detect network and HTTP failures.
* JSON parsing and missing response fields are handled explicitly.
* Tool routing handles invalid JSON arguments, unknown tools, and invalid function arguments.
* OpenAI API calls handle connection errors, timeouts, authentication errors, and rate limits.
* The agent has a maximum iteration limit to prevent an uncontrolled tool-calling loop.
* Logging records important events such as tool usage, session starts, and user actions while filtering unnecessary HTTP-library noise.

The tools return structured error objects instead of crashing the application, allowing the agent to receive the failure and respond appropriately.

## Project Structure

```text
ai-travel-planner/
├── main.py            # Application flow and travel agent
├── tools.py           # External API integrations and calculations
├── tools_router.py    # Tool definitions, registry, and execution
├── logger.py          # Application logging configuration
├── .env               # API keys (not committed)
├── .gitignore
└── logs/              # Application logs
```

## APIs & Technologies

* Python
* OpenAI Responses API
* Pydantic
* Requests
* Open-Meteo API
* FastForex API
* REST Countries API
* python-dotenv
* Python logging

## Key Concepts Demonstrated

**Structured Outputs · Function Calling · Agent Loops · Tool Routing · API Integration · Pydantic Validation · Error Handling · Logging · Conversation Context · Streaming**
