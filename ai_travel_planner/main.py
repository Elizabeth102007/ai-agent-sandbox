
import os
from dotenv import load_dotenv
from logger import setup_logging, logger
import json
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    OpenAI
)
from typing import Optional
from pydantic import BaseModel

from tools_router import tools, execute_tool

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class TripDetails(BaseModel):
    destination: Optional[str] = None
    duration: Optional[int] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# plan trip
def plan_trip():
    user_request = input("Tell me about the trip you want to plan: ")

    messages = [{
        "role": "system",
        "content": """
        You are an AI travel planner.
        Extract the following information from the user's request:

        - destination
        - duration
        - budget
        - currency
        - start_date
        - end_date

        If information is not provided, return null for that field.
        """
    },
    {
        "role": "user",
        "content": user_request
    }]

    try:
        response = client.responses.parse(
            model="gpt-5-nano",
            input=messages,
            text_format=TripDetails
        )

        trip = response.output_parsed

    except APIConnectionError as e:
        print(f"Error connecting to the API: {e}")
        return None, None

    except APITimeoutError as e:
        print(f"API request timed out: {e}")
        return None, None

    except AuthenticationError as e:
        print(f"Authentication error: {e}")
        return None, None

    except RateLimitError as e:
        print(f"Rate limit exceeded: {e}")
        return None, None

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None

    messages += response.output

    if not trip.destination:
        print("Destination is required to plan a trip.")

        destination = input("Where would you like to go? ")

        trip.destination = destination

        messages.append({
            "role": "user",
            "content": f"My destination is {destination}."
        })

    return trip, messages


# travel agent flow

def build_planning_context(trip):
    return [{
        "role": "system",
        "content": """
        You are a travel planning assistant.

        Create a practical and useful trip plan based on the user's trip details.

       Use the available tools when factual information or calculations are needed. 
       Do not invent information that can be obtained through the available tools.

       When information from one tool is needed as input to another tool, use the tools in the appropriate order.

       For example, obtain the destination coordinates before requesting weather for that destination.

       Use reliable tool results when discussing:
       - weather
       - budget calculations
       - currency conversions
       - country information

       After gathering the necessary information, provide a clear and concise travel plan tailored to the user's trip details.

    """
    },
    {
        "role": "user",
        "content": f"""
                    Plan my trip using these details:

                    Destination: {trip.destination}
                    Duration: {trip.duration}
                    Budget: {trip.budget}
                    Currency: {trip.currency}
                    Start date: {trip.start_date}
                    End date: {trip.end_date}
                   """
    }
    ]
    

def run_travel_agent(messages):
    MAX_ITERATIONS = 8

    for _ in range(MAX_ITERATIONS):
        try: 
            response = client.responses.create(model="gpt-5-nano", 
                                               input=messages, 
                                               tools=tools)
        except APIConnectionError as e:
              print(f"Error connecting to the API: {e}")
              return
        
        except APITimeoutError as e:
              print(f"API request timed out: {e}")
              return
        
        except AuthenticationError as e:
              print(f"Authentication error: {e}")
              return
        
        except RateLimitError as e:
              print(f"Rate limit exceeded: {e}")
              return
        
        except Exception as e:
              print(f"An unexpected error occurred: {e}")
              return

        messages += response.output

        tool_calls = [item for item in response.output if item.type == "function_call"]

        if not tool_calls:
           break

        for tool_call in tool_calls:
            logger.info("Using tool: %s", tool_call.name)
            result = execute_tool(tool_call)
            messages.append({
                    "type": "function_call_output",
                   "call_id": tool_call.call_id,
                   "output": json.dumps(result)
        })
    else:
       print("Trip planning is taking longer than expected — stopping here.")
    

    print("\n" + "=" * 50)
    print("YOUR TRIP PLAN")
    print("=" * 50 + "\n")

    full_text = ""
    try:
       stream = client.responses.create(model="gpt-5-nano", input=messages, stream=True)
       for event in stream:
          if event.type == "response.output_text.delta":
             full_text += event.delta
             print(event.delta, end="", flush=True)

    except APIConnectionError as e:
        print(f"\nError connecting to the API: {e}")
    except APITimeoutError as e:
       print(f"\nAPI request timed out: {e}")
    except AuthenticationError as e:
       print(f"\nAuthentication error: {e}")
    except RateLimitError as e:
       print(f"\nRate limit exceeded: {e}")
    except Exception as e:
       print(f"\nAn unexpected error occurred: {e}")

    finally:
       if full_text:
          messages.append({"role": "assistant", "content": full_text})
# conversation memory
def start_trip_session():

    logger.info("Starting new trip session")

    trip, messages = plan_trip()

    if trip is None or messages is None:
        logger.warning("Trip session could not be started")
        return

    messages += build_planning_context(trip)
    run_travel_agent(messages)

    while True:

        question = input(
            "\nAsk a question (or type 'exit'): "
        ).strip()

        if question.lower() == "exit":
            logger.info("User ended trip session")
            print("\nReturning to main menu...")
            break

        if not question:
            continue

        logger.info("User asked follow-up question")

        messages.append({
            "role": "user",
            "content": question
        })

        run_travel_agent(messages)

def main():

    setup_logging()

    logger.info("Travel planner started")

    print("=" * 50)
    print("WELCOME TO THE AI TRAVEL PLANNER")
    print("=" * 50)

    while True:

        print("\n1. Plan a trip")
        print("2. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            start_trip_session()

        elif choice == "2":
            logger.info("Travel planner exited")
            print("\nGoodbye!")
            break

        else:
            print("\nInvalid option. Please choose 1 or 2.")

if __name__ == "__main__":
    main()