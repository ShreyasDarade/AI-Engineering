"""The free brain: keyword routing, no LLM, no API key, no billing.

This is what `python -m weather_buddy` runs by default. It reads the user's
message, works out which of the four tools they meant, and answers in the same
gremlin voice as the LLM version -- just with rules instead of a model.

Nothing in this module can incur a charge. The only network call it can cause
is to Open-Meteo, which is keyless and accountless (and can be switched off
entirely with --offline).
"""

from __future__ import annotations

import re

from . import fun
from .weather_api import WeatherError, get_current, get_forecast

# Words that signal intent -- never part of a city name.
_OUTFIT_WORDS = {"wear", "jacket", "coat", "dress", "pack", "packing", "umbrella", "outfit", "bring"}
_FORECAST_WORDS = {"forecast", "week", "days", "day", "tomorrow", "ahead", "upcoming"}
_GREETINGS = {"hi", "hey", "hello", "yo", "sup", "howdy"}
_THANKS = {"thanks", "thank", "ty", "cheers", "thx"}

# Filler that shows up around city names and must be stripped off.
_NOISE = {
    "what", "whats", "what's", "is", "it", "the", "like", "how", "hows", "how's", "about",
    "weather", "temperature", "temp", "today", "tonight", "now", "right", "currently",
    "please", "me", "give", "get", "tell", "show", "a", "an", "there", "outside", "doing",
    "should", "i", "do", "need", "to", "my", "you", "think", "of", "looking", "look",
    "next", "this", "and", "in", "for", "at", "on", "be", "will", "gonna", "going",
    "vs", "versus", "or", "than", "better", "worse", "which", "one", "wins", "win",
} | _OUTFIT_WORDS | _FORECAST_WORDS

_CITY_CHARS = re.compile(r"[^a-zA-Z\s'\-.]")
_DAYS_PATTERN = re.compile(r"(\d+)\s*(?:day|days)")
_SPLIT_PATTERN = re.compile(r"\s+(?:vs\.?|versus|or)\s+", re.IGNORECASE)

HELP = """I do four things:

    what's it like in Tokyo?          current conditions + vibe score
    should I bring a jacket in Oslo?  outfit advice
    5 days for Sydney                 the forecast
    Pittsburgh vs Cairo               a showdown

Commands: /help  /cities  /reset  /quit"""


def _clean_city(raw: str) -> str:
    """Strip filler words and punctuation down to something city-shaped."""
    words = _CITY_CHARS.sub(" ", raw).split()
    keep = [w for w in words if w.lower().strip(".'-") not in _NOISE]
    return " ".join(keep).strip()


def _looks_like_a_city(text: str) -> bool:
    return bool(text) and len(text) >= 2 and not text.isdigit()


def _requested_days(message: str) -> int:
    match = _DAYS_PATTERN.search(message)
    if match:
        return max(1, min(int(match.group(1)), 7))
    if "week" in message:
        return 7
    if "tomorrow" in message:
        return 2
    return 3


class LocalBrain:
    """Rule-based chat with a one-slot memory for the city you last mentioned."""

    def __init__(self) -> None:
        self.last_city: str | None = None

    def reset(self) -> None:
        self.last_city = None

    def respond(self, message: str) -> str:
        text = message.strip()
        lowered = text.lower()
        words = {w.strip("?!.,'") for w in lowered.split()}

        if words & _GREETINGS and len(words) <= 3:
            return "Hey. Name a city and I'll tell you how much the sky hates you today."
        if words & _THANKS:
            return "Don't thank me, thank the jet stream. \U0001f32c️"
        if words & {"help", "?"} and len(words) <= 3:
            return HELP

        # Two cities? That's a showdown.
        parts = _SPLIT_PATTERN.split(text)
        if len(parts) == 2:
            left, right = _clean_city(parts[0]), _clean_city(parts[1])
            if _looks_like_a_city(left) and _looks_like_a_city(right):
                return self._showdown(left, right)

        city = _clean_city(text) or self.last_city
        if not _looks_like_a_city(city or ""):
            return "Which city? I can't rate a vibe I can't locate."
        self.last_city = city

        if words & _OUTFIT_WORDS:
            return self._outfit(city)
        if words & _FORECAST_WORDS:
            return self._forecast(city, _requested_days(lowered))
        return self._current(city)

    # -- intent handlers -------------------------------------------------

    def _current(self, city: str) -> str:
        try:
            current = get_current(city)
        except WeatherError as exc:
            return self._oops(exc)
        self.last_city = current.place.name
        vibe = fun.vibe_check(current)
        opener = (
            "Okay, this is a good one." if vibe.score >= 7.5 else
            "It's fine. Aggressively fine." if vibe.score >= 5 else
            "Oof. Brace yourself."
        )
        return f"{opener}\n\n{fun.report_card(current)}"

    def _forecast(self, city: str, days: int) -> str:
        try:
            place, forecast = get_forecast(city, days)
        except WeatherError as exc:
            return self._oops(exc)
        self.last_city = place.name
        return f"Here's the week as the models see it -- they lie after day three.\n\n{fun.forecast_card(place, forecast)}"

    def _outfit(self, city: str) -> str:
        try:
            current = get_current(city)
        except WeatherError as exc:
            return self._oops(exc)
        self.last_city = current.place.name
        items = "\n".join(f"    - {item}" for item in fun.outfit_call(current))
        return (
            f"Dressing for {current.place.label} "
            f"({current.description}, feels like {current.feels_like_c}°C):\n{items}"
        )

    def _showdown(self, left: str, right: str) -> str:
        try:
            result = fun.showdown(get_current(left), get_current(right))
        except WeatherError as exc:
            return self._oops(exc)
        self.last_city = right
        return f"Ohh, a challenger approaches.\n\n{result}"

    @staticmethod
    def _oops(exc: WeatherError) -> str:
        return f"\U0001f615 {exc}"
