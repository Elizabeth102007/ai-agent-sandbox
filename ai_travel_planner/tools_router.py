
import json

from tools import (
    get_city_coordinates,
    get_weather,
    convert_currency,
    make_budget,
    country_info
)


tools = [
    {
        "type": "function",
        "name": "get_city_coordinates",
        "description": (
            "Get the latitude and longitude of a city. "
            "Use this when coordinates are needed for a location."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the city."
                }
            },
            "required": ["city"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_weather",
        "description": (
            "Get the current weather for a location using "
            "latitude and longitude."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "The latitude of the location."
                },
                "longitude": {
                    "type": "number",
                    "description": "The longitude of the location."
                }
            },
            "required": [
                "latitude",
                "longitude"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "convert_currency",
        "description": (
            "Convert an amount from one currency to another "
            "using current exchange rate data."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "The amount of money to convert."
                },
                "base_currency": {
                    "type": "string",
                    "description": (
                        "The three-letter currency code to convert from. "
                        "For example: USD, EUR, GBP, or EGP."
                    )
                },
                "target_currency": {
                    "type": "string",
                    "description": (
                        "The three-letter currency code to convert to. "
                        "For example: USD, EUR, GBP, or EGP."
                    )
                }
            },
            "required": [
                "amount",
                "base_currency",
                "target_currency"
            ],
            "additionalProperties": False
        }
    },
    {
    "type": "function",
    "name": "make_budget",
    "description": "Calculate the total trip budget from a daily spending amount and the number of days.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "daily_spend": {
                "type": "number",
                "description": "The amount of money planned to spend per day."
            },
            "number_of_days": {
                "type": "integer",
                "description": "The total number of days for the trip."
            }
        },
        "required": ["daily_spend", "number_of_days"],
        "additionalProperties": False
        }
   },
   {
    "type": "function",
    "name": "country_info",
    "description": "Get general information about a country, including its capital, region, population, area, languages, and currencies.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "country": {
                "type": "string",
                "description": "The common name of the country to look up."
            }
        },
        "required": ["country"],
        "additionalProperties": False
        }
    }

]


# tool registry mapping tool names to their corresponding functions

TOOL_REGISTRY = {
    "get_city_coordinates": get_city_coordinates,
    "get_weather": get_weather,
    "convert_currency": convert_currency,
    "make_budget": make_budget,
    "country_info": country_info
}


# tool router to execute the appropriate tool based on the model's request

def execute_tool(tool_call):

    tool_name = tool_call.name

    try:
        arguments = json.loads(tool_call.arguments)

    except json.JSONDecodeError as e:
        return {
            "error": f"Invalid tool arguments: {e}"
        }

    tool_function = TOOL_REGISTRY.get(tool_name)

    if tool_function is None:
        return {
            "error": f"Unknown tool requested: {tool_name}"
        }

    try:
        return tool_function(**arguments)

    except TypeError as e:
        return {
            "error": f"Invalid arguments for {tool_name}: {e}"
        }

    except Exception as e:
        return {
            "error": f"Error executing {tool_name}: {e}"
        }

