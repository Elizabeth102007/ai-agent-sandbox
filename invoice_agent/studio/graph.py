
from functools import lru_cache
from typing import Annotated, Optional
from typing_extensions import TypedDict
from operator import add


from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from studio.schemas import ExtractedInvoice, InvoiceResult
from studio.validation import validate_invoice, route

from openai import APIConnectionError, APITimeoutError, APIStatusError
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError




class State(TypedDict):
    raw_text: str
    invoice: Optional[ExtractedInvoice]
    errors: list[str]
    attempts: int
    path: Annotated[list[str], add]
    result: Optional[InvoiceResult]


EXTRACTION_RULES = """
You extract structured data from invoice text.

Rules:
1. Extract exactly what the invoice document states.
2. Never calculate, correct, or adjust monetary amounts.
3. Return null for any field whose value is not stated in the document.
4. Never invent invoice numbers, dates, amounts, vendors, or other values.
5. Format dates as YYYY-MM-DD when the date is unambiguous.
6. Preserve the supplier's stated subtotal, tax, line amounts, and total,
   even when the arithmetic is inconsistent.
7. Do not treat a supplier's arithmetic error as an extraction mistake.
8. If previous validation errors are supplied, correct extraction mistakes
   only. If the document itself contains the mismatch, keep its values
   exactly as written.
9. Return only data that conforms to the requested ExtractedInvoice schema.
"""


@lru_cache(maxsize=1)
def get_structured_model():
    """Create and cache the structured invoice extraction model."""
    model = ChatOpenAI(
        model="gpt-5-nano",
        max_retries=0,
    )

    structured_model = model.with_structured_output(
        ExtractedInvoice,
        method="json_schema",
        strict=False,
    )
    return structured_model


async def extract_invoice(
    raw_text: str,
    previous_errors: list[str],
) -> ExtractedInvoice:
    """Extract invoice fields without correcting the supplier's figures."""
    retry_feedback = ""

    if previous_errors:
        retry_feedback = (
            "\n\nPrevious validation errors:\n"
            + "\n".join(f"- {error}" for error in previous_errors)
            + "\nCorrect extraction mistakes only; if the document itself "
            "contains the mismatch, keep the values as written."
        )

    messages = [
        SystemMessage(content=EXTRACTION_RULES),
        HumanMessage(
            content=(
                "Extract the invoice fields from the following document.\n\n"
                f"INVOICE TEXT:\n{raw_text}"
                f"{retry_feedback}"
            )
        ),
    ]
    structured_model = get_structured_model()
    result = await structured_model.ainvoke(messages)
    
    if not isinstance(result, ExtractedInvoice):
        raise TypeError(
            "Structured extraction did not return an ExtractedInvoice; "
            f"received {type(result).__name__}."
        )

    return result


async def extract_fields(state: State) -> dict:
    """Extract invoice data, recording failures for the retry loop."""
    try:
       invoice = await extract_invoice(
          raw_text=state["raw_text"],
          previous_errors=state["errors"],
            )

    except (APITimeoutError, APIConnectionError) as exc:
           error = f"Temporary API failure ({type(exc).__name__}): {exc}"

    except APIStatusError as exc:
        if exc.status_code not in (408, 409, 429) and exc.status_code < 500:
              raise

        error = f"API request failed (HTTP {exc.status_code}): {exc}"

    except (OutputParserException, ValidationError) as exc:
        error = f"Could not parse structured invoice output: {exc}"

   
    else:
       return {
        "invoice": invoice,
        "errors": [],
        "attempts": state["attempts"] + 1,
        "path": ["extract_fields"],
              }

    return {
    "invoice": None,
    "errors": [error],
    "attempts": state["attempts"] + 1,
    "path": ["extract_fields"],
}


async def validate(state: State) -> dict:
    """Run the invoice validation rules."""
    if state["invoice"] is None:
        # Preserve the extraction error so routing can retry or escalate.
        errors = state["errors"]
    else:
        errors = validate_invoice(state["invoice"])

    return {
        "errors": errors,
        "path": ["validate"],
    }


async def format_output(state: State) -> dict:
    """Build the successful result."""
    result = InvoiceResult(
        invoice=state["invoice"],
        errors=[],
        attempts=state["attempts"],
        status="validated",
    )

    return {
        "result": result,
        "path": ["format_output"],
    }


async def flag_for_human(state: State) -> dict:
    """Build a review result after retries are exhausted."""
    result = InvoiceResult(
        invoice=state["invoice"],
        errors=state["errors"],
        attempts=state["attempts"],
        status="needs_review",
    )

    return {
        "result": result,
        "path": ["flag_for_human"],
    }


def build_graph():
    builder = StateGraph(State)

    builder.add_node("extract_fields", extract_fields)
    builder.add_node("validate", validate)
    builder.add_node("format_output", format_output)
    builder.add_node("flag_for_human", flag_for_human)

    builder.add_edge(START, "extract_fields")
    builder.add_edge("extract_fields", "validate")
    builder.add_conditional_edges("validate", route)

    builder.add_edge("format_output", END)
    builder.add_edge("flag_for_human", END)

    return builder.compile()
