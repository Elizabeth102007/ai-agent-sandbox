# finance_agent/main.py
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError
)
from datetime import date
from logger import setup_logging, logger
from tools import FinanceSession
from tool_router import tools, execute_tool

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_ITERATIONS = 5

SYSTEM_PROMPT = f"""
You are a helpful personal finance AI assistant.
Help users track spending, view transactions, summarize budgets, and calculate projections.

Assumed Context: Today's date is {date.today().isoformat()}.
Use tools when requests involve tracking, searching, or calculating financial data.
"""

def run_finance_agent(messages: List[Dict[str, Any]], session: FinanceSession) -> None:
    for _ in range(MAX_ITERATIONS):
        try:
            
            response = client.responses.create(
                model="gpt-5-nano",
                input=messages,
                tools=tools
            )
        except APIConnectionError as e:
            logger.error("API Connection Error: %s", e)
            print(f"\nConnection error: {e}")
            return
        except APITimeoutError as e:
            logger.error("API Timeout Error: %s", e)
            print(f"\nTimeout error: {e}")
            return
        except AuthenticationError as e:
            logger.error("Authentication Error: %s", e)
            print(f"\nAuthentication error: {e}")
            return
        except RateLimitError as e:
            logger.error("Rate Limit Error: %s", e)
            print(f"\nRate limit exceeded: {e}")
            return
        except Exception as e:
            logger.error("Unexpected Error: %s", e)
            print(f"\nAn unexpected error occurred: {e}")
            return

        
        messages += response.output

        # Extract function call items from output
        tool_calls = [item for item in response.output if item.type == "function_call"]

        # If no tool calls were requested, exit the execution loop
        if not tool_calls:
            break

        # Execute requested tool calls
        for tool_call in tool_calls:
            logger.info("Executing tool: %s", tool_call.name)
            result = execute_tool(tool_call, session)
            
            # Append result formatted as function_call_output
            messages.append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": result
            })
    else:
        logger.warning("Reached MAX_ITERATIONS without concluding tool execution.")
        print("\nRequest took too many tool calls — stopping iteration loop.")

    print("\n" + "=" * 50)
    print("FINANCE ASSISTANT RESPONSE")
    print("=" * 50 + "\n")

    full_text = ""
    try:
        stream = client.responses.create(
            model="gpt-5-nano",
            input=messages,
            stream=True
        )
        for event in stream:
            if event.type == "response.output_text.delta":
                full_text += event.delta
                print(event.delta, end="", flush=True)
        print("\n")

    except APIConnectionError as e:
        logger.error("API Connection Error during streaming: %s", e)
        print(f"\nError connecting to the API: {e}")
    except APITimeoutError as e:
        logger.error("API Timeout Error during streaming: %s", e)
        print(f"\nAPI request timed out: {e}")
    except AuthenticationError as e:
        logger.error("Authentication Error during streaming: %s", e)
        print(f"\nAuthentication error: {e}")
    except RateLimitError as e:
        logger.error("Rate Limit Error during streaming: %s", e)
        print(f"\nRate limit exceeded: {e}")
    except Exception as e:
        logger.error("Unexpected Error during streaming: %s", e)
        print(f"\nAn unexpected error occurred: {e}")

    finally:
        if full_text:
            messages.append({"role": "assistant", "content": full_text})

def start_finance_session() -> None:
    logger.info("Starting new finance tracking session")
    session = FinanceSession()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    print("\nFinance Session Started! Ask a question or log a transaction.")

    while True:
        user_input = input("\nAsk a question (or type 'exit'): ").strip()

        if user_input.lower() == "exit":
            logger.info("User ended finance session")
            print("\nReturning to main menu...")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        run_finance_agent(messages, session)

def main() -> None:
    setup_logging()
    logger.info("Finance Agent started")

    print("=" * 50)
    print("WELCOME TO THE AI PERSONAL FINANCE AGENT")
    print("=" * 50)

    while True:
        print("\n1. Start Finance Session")
        print("2. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            start_finance_session()
        elif choice == "2":
            logger.info("Finance Agent exited cleanly")
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid option. Please enter 1 or 2.")

if __name__ == "__main__":
    main()