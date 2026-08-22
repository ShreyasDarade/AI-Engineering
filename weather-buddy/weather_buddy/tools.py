"""LangChain tools the model can call.

Each tool returns a formatted string rather than raw JSON -- the model is
free to riff on it, but even a lazy pass-through reads well to a human.
"""

from __future__ import annotations

from langchain_core.tools import tool

from . import fun
from .weather_api import WeatherError, get_current, get_forecast


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city, with a vibe score, outfit advice and an activity idea.

    Args:
        city: City name, optionally with country, e.g. "Tokyo" or "Springfield, US".
    """
    try:
        return fun.report_card(get_current(city))
    except WeatherError as exc:
        return f"Weather lookup failed: {exc}"


@tool
def get_multi_day_forecast(city: str, days: int = 3) -> str:
    """Get the daily forecast for a city for the next 1-7 days.

    Args:
        city: City name, optionally with country.
        days: How many days ahead to report, 1 to 7. Defaults to 3.
    """
    try:
        place, forecast = get_forecast(city, days)
        return fun.forecast_card(place, forecast)
    except WeatherError as exc:
        return f"Forecast lookup failed: {exc}"


@tool
def weather_showdown(city_a: str, city_b: str) -> str:
    """Compare two cities' current weather head-to-head and declare a winner.

    Args:
        city_a: First city.
        city_b: Second city.
    """
    try:
        return fun.showdown(get_current(city_a), get_current(city_b))
    except WeatherError as exc:
        return f"Showdown cancelled: {exc}"


@tool
def what_should_i_wear(city: str) -> str:
    """Get outfit and packing advice for a city based on its current weather.

    Args:
        city: City name, optionally with country.
    """
    try:
        current = get_current(city)
        items = fun.outfit_call(current)
        bullets = "\n".join(f"    - {item}" for item in items)
        return (
            f"\U0001f9e5  Dressing for {current.place.label} "
            f"({current.description}, feels like {current.feels_like_c}°C):\n{bullets}"
        )
    except WeatherError as exc:
        return f"Outfit advice unavailable: {exc}"


ALL_TOOLS = [get_weather, get_multi_day_forecast, weather_showdown, what_should_i_wear]
