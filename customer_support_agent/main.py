import asyncio
from dotenv import load_dotenv
from openai import APIConnectionError, RateLimitError
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.exceptions import UnexpectedModelBehavior, AgentRunError

from logger import setup_logging, logger
from tools import (
    CustomerSession,
    SupportResponse,
    get_default_seed_orders,
    get_order_status,
    create_support_ticket,
    get_ticket_status,
    escalate_to_human,
)

load_dotenv()

# system Instructions
SYSTEM_INSTRUCTIONS = """
You are an intelligent SaaS customer support agent.

POLICY & GUIDELINES:
- Returns/Refunds: Customers can request refunds within 30 days of purchase.
- Support Hours: Human agents are available Mon-Fri, 9 AM - 5 PM EST.
- Order Queries: Always check order status using `get_order_status` before answering shipping questions.
- Escalation: Execute `escalate_to_human` if an issue is unresolvable or human help is explicitly requested.

ACTION TRACKING INSTRUCTIONS:
- You MUST populate the `actions_taken` array in your output schema using ONLY the following standard identifiers:
  - "LOOKUP_ORDER": Added whenever you call `get_order_status`.
  - "TICKET_CREATED": Added whenever you call `create_support_ticket`.
  - "LOOKUP_TICKET": Added whenever you call `get_ticket_status`.
  - "ESCALATED": Added whenever you call `escalate_to_human`.
- Do not invent custom action strings. If no tool actions were taken, leave `actions_taken` as an empty list `[]`.

Answer general policy inquiries directly using these instructions.
Use available tools whenever managing orders, support tickets, or escalations.
"""

# Agent Setup
support_agent = Agent(
    'openai:gpt-5-nano',
    deps_type=CustomerSession,
    output_type=SupportResponse,
    instructions=SYSTEM_INSTRUCTIONS,
    tools=[
        get_order_status,
        create_support_ticket,
        get_ticket_status,
        escalate_to_human,
    ],
    retries = 3
)


# Output validation
@support_agent.output_validator
async def validate_support_response(
    ctx: RunContext[CustomerSession],
    response: SupportResponse
) -> SupportResponse:
    if ctx.deps.escalated and response.resolved:
        logger.warning("Validation mismatch: Escalated is True but response marked resolved=True.")
        raise ModelRetry("Issue was escalated to a human; 'resolved' MUST be set to False.")
    
    if "TICKET_CREATED" in response.actions_taken and len(ctx.deps.tickets) == 0:
       logger.warning("Validation mismatch: claimed TICKET_CREATED action without a ticket existing.")
       raise ModelRetry("You reported creating a ticket, but no ticket exists in session state. Do not claim this action unless create_support_ticket was actually called.")
    return response


# Interactive application loop
async def main() -> None:
    # Route technical logs to file
    setup_logging()
    logger.info("Application starting up.")

    print("\n=============================================")
    print("      SaaS Customer Support Assistant        ")
    print("=============================================\n")
    
    user_cust_id = input("Please enter your Customer ID [Press Enter for default 'CUST-1001']: ").strip()
    final_customer_id = user_cust_id if user_cust_id else "CUST-1001"

    # Initialize in-memory session state
    session = CustomerSession(
        customer_id=final_customer_id,
        orders=get_default_seed_orders()
    )

    logger.info(f"Initialized CustomerSession for ID: {session.customer_id}")
    
    print(f"\nWelcome! Active Session: [{session.customer_id}]")
    print("Type your question below (or type 'exit' to quit).\n")

    while True:
        try:
            # Custom prompt label
            user_input = input(f"{session.customer_id} > ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ("exit", "quit"):
                print("\nThank you for contacting customer support. Have a great day!")
                logger.info("Session gracefully closed by user.")
                break

            logger.info(f"User Query: {user_input}")
            print("\nSupport Agent > ", end="", flush=True)
            # Stream LLM output directly to console
            async with support_agent.run_stream(user_input, deps=session) as result:
                printed_text = ""
                async for snapshot in result.stream_output():
                    if snapshot.message:
                  # Extract only the newly arrived character slice
                       new_chunk = snapshot.message.removeprefix(printed_text)
                       print(new_chunk, end="", flush=True)
                       printed_text = snapshot.message
            
                print("\n")
    
                # Complete validation execution
                validated_data: SupportResponse = await result.get_output()
                logger.info(f"Response successfully validated: {validated_data.model_dump()}")

        except (UnexpectedModelBehavior, AgentRunError) as e:
            logger.error(f"PydanticAI Framework Error: {e}")
            print("\n[Notice]: Something went wrong while processing your request. Please try again.")

        except (APIConnectionError, RateLimitError) as e:
            logger.critical(f"OpenAI API Connection Error: {e}")
            print("\n[Connection Error]: Unable to reach support servers. Please check your network connection.")

        except Exception as e:
            logger.exception(f"Unhandled Exception: {e}")
            print("\n[Error]: An unexpected system error occurred. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())