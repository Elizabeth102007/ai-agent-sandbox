
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# weather tools using the Open-Meteo API

def get_city_coordinates(city: str):

    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1
            },
            timeout=10
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Could not reach geocoding service: {e}"
        }

    try:
        data = response.json()
        result = data["results"][0]

        return {
            "name": result["name"],
            "country": result.get("country"),
            "latitude": result["latitude"],
            "longitude": result["longitude"]
        }

    except (KeyError, IndexError) as e:
        return {
            "error": f"No city found matching '{city}': {e}"
        }

    except ValueError as e:
        return {
            "error": f"Invalid data received from geocoding service: {e}"
        }


def get_weather(latitude: float, longitude: float):


    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "dew_point_2m",
                    "wind_speed_10m"
                ]
            },
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Could not reach weather service: {e}"
        }

    except ValueError as e:
        return {
            "error": f"Invalid data received from weather service: {e}"
        }

# currency conversion tool using the FastForex API

def convert_currency(amount: float,base_currency: str, target_currency: str):

    api_key = os.getenv("FAST_FOREX_KEY")

    headers = {
        "X-API-Key": api_key
    }

    try:
        response = requests.get(
            "https://api.fastforex.io/fetch-all",
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Could not reach currency conversion service: {e}"
        }

    try:
        data = response.json()
        results = data["results"]

        base_currency = base_currency.upper()
        target_currency = target_currency.upper()

        if base_currency != "USD" and base_currency not in results:
            return {
                "error": f"Base currency '{base_currency}' was not found."
            }

        if target_currency not in results:
            return {
                "error": f"Target currency '{target_currency}' was not found."
            }

        if base_currency == "USD":
            converted_amount = amount * results[target_currency]

        else:
            amount_in_usd = amount / results[base_currency]
            converted_amount = amount_in_usd * results[target_currency]

        return {
            "amount": amount,
            "base_currency": base_currency,
            "target_currency": target_currency,
            "converted_amount": round(converted_amount, 2),
            "updated": data.get("updated")
        }

    except KeyError as e:
        return {
            "error": f"Currency or data field not found: {e}"
        }

    except ValueError as e:
        return {
            "error": f"Invalid data received from currency service: {e}"
        }

    except Exception as e:
        return {
            "error": f"An unexpected error occurred: {e}"
        }

# budget tool to calculate total budget based on daily spend and number of days

def make_budget(daily_spend: float, number_of_days: int):

    total_budget = daily_spend * number_of_days

    return {
        "daily_spend": daily_spend,
        "number_of_days": number_of_days,
        "total_budget": round(total_budget, 2)
    }

# country info tool using the REST Countries API
def country_info(country: str):

    api_key = os.getenv("REST_COUNTRIES_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get(
            f"https://api.restcountries.com/countries/v5/names.common/{country}",
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Could not reach country info service: {e}"
        }

    try:
        data = response.json()

        country_data = data["data"]["objects"][0]

        return {
            "name": country_data.get("names", {}).get("common"),
            "capital": (country_data.get("capital") or [None])[0],
            "region": country_data.get("region"),
            "subregion": country_data.get("subregion"),
            "population": country_data.get("population"),
            "area": country_data.get("area"),
            "languages": list(
                country_data.get("languages", {}).values()
            ),
            "currencies": list(
                country_data.get("currencies", {}).keys()
            )
        }

    except (KeyError, IndexError) as e:
        return {
            "error": f"No country found matching '{country}': {e}"
        }

    except ValueError as e:
        return {
            "error": f"Invalid data received from country info service: {e}"
        }