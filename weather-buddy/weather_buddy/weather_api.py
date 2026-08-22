"""Open-Meteo client.

Open-Meteo needs no API key and no signup, so anyone who clones this repo can
run the bot immediately. Set WEATHER_BUDDY_OFFLINE=1 to skip the network and
serve a handful of built-in demo cities instead -- useful behind a firewall
and what the test-suite runs against.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 10


class WeatherError(RuntimeError):
    """Something went wrong looking up a city or its weather."""


# --------------------------------------------------------------------------
# WMO weather interpretation codes
# https://open-meteo.com/en/docs -> "Weather variable documentation"
# --------------------------------------------------------------------------

WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("clear sky", "☀️"),
    1: ("mainly clear", "\U0001f324️"),
    2: ("partly cloudy", "⛅"),
    3: ("overcast", "☁️"),
    45: ("fog", "\U0001f32b️"),
    48: ("freezing fog", "\U0001f32b️"),
    51: ("light drizzle", "\U0001f327️"),
    53: ("drizzle", "\U0001f327️"),
    55: ("heavy drizzle", "\U0001f327️"),
    56: ("freezing drizzle", "\U0001f9ca"),
    57: ("heavy freezing drizzle", "\U0001f9ca"),
    61: ("light rain", "\U0001f326️"),
    63: ("rain", "\U0001f327️"),
    65: ("heavy rain", "\U0001f4a7"),
    66: ("freezing rain", "\U0001f9ca"),
    67: ("heavy freezing rain", "\U0001f9ca"),
    71: ("light snow", "\U0001f328️"),
    73: ("snow", "❄️"),
    75: ("heavy snow", "☃️"),
    77: ("snow grains", "❄️"),
    80: ("light showers", "\U0001f326️"),
    81: ("showers", "\U0001f327️"),
    82: ("violent showers", "⛈️"),
    85: ("snow showers", "\U0001f328️"),
    86: ("heavy snow showers", "☃️"),
    95: ("thunderstorm", "⛈️"),
    96: ("thunderstorm with hail", "⛈️"),
    99: ("thunderstorm with heavy hail", "⚡"),
}


def describe(code: int) -> str:
    """Human-readable name for a WMO weather code."""
    return WMO_CODES.get(code, ("mystery weather", "\U0001f52e"))[0]


def emoji_for(code: int) -> str:
    """Emoji for a WMO weather code."""
    return WMO_CODES.get(code, ("mystery weather", "\U0001f52e"))[1]


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------


def _c_to_f(celsius: float) -> float:
    return round(celsius * 9 / 5 + 32, 1)


@dataclass(frozen=True)
class Place:
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str = "auto"

    @property
    def label(self) -> str:
        return f"{self.name}, {self.country}"


@dataclass(frozen=True)
class CurrentWeather:
    place: Place
    temperature_c: float
    feels_like_c: float
    humidity: int
    precipitation_mm: float
    wind_kph: float
    code: int
    is_day: bool
    local_time: str

    @property
    def description(self) -> str:
        return describe(self.code)

    @property
    def emoji(self) -> str:
        return emoji_for(self.code)

    @property
    def temperature_f(self) -> float:
        return _c_to_f(self.temperature_c)

    @property
    def feels_like_f(self) -> float:
        return _c_to_f(self.feels_like_c)


@dataclass(frozen=True)
class DayForecast:
    date: str
    code: int
    high_c: float
    low_c: float
    precip_chance: int

    @property
    def description(self) -> str:
        return describe(self.code)

    @property
    def emoji(self) -> str:
        return emoji_for(self.code)

    @property
    def high_f(self) -> float:
        return _c_to_f(self.high_c)

    @property
    def low_f(self) -> float:
        return _c_to_f(self.low_c)

    @property
    def weekday(self) -> str:
        return dt.date.fromisoformat(self.date).strftime("%a")


# --------------------------------------------------------------------------
# Offline demo data -- deterministic, so tests and `--demo` never flake
# --------------------------------------------------------------------------

_OFFLINE_PLACES: dict[str, tuple[Place, dict]] = {
    "pittsburgh": (
        Place("Pittsburgh", "United States", 40.44, -79.99, "America/New_York"),
        {"temp": 8.4, "feels": 5.1, "humidity": 71, "precip": 0.3,
         "wind": 17.0, "code": 61, "is_day": True, "time": "08:15"},
    ),
    "tokyo": (
        Place("Tokyo", "Japan", 35.69, 139.69, "Asia/Tokyo"),
        {"temp": 22.7, "feels": 23.4, "humidity": 58, "precip": 0.0,
         "wind": 9.0, "code": 1, "is_day": False, "time": "21:15"},
    ),
    "reykjavik": (
        Place("Reykjavik", "Iceland", 64.15, -21.94, "Atlantic/Reykjavik"),
        {"temp": -3.2, "feels": -11.0, "humidity": 84, "precip": 1.4,
         "wind": 47.0, "code": 73, "is_day": True, "time": "12:15"},
    ),
    "cairo": (
        Place("Cairo", "Egypt", 30.04, 31.24, "Africa/Cairo"),
        {"temp": 38.9, "feels": 41.2, "humidity": 19, "precip": 0.0,
         "wind": 12.0, "code": 0, "is_day": True, "time": "14:15"},
    ),
    "london": (
        Place("London", "United Kingdom", 51.51, -0.13, "Europe/London"),
        {"temp": 12.1, "feels": 10.8, "humidity": 88, "precip": 0.6,
         "wind": 21.0, "code": 3, "is_day": True, "time": "13:15"},
    ),
    "sydney": (
        Place("Sydney", "Australia", -33.87, 151.21, "Australia/Sydney"),
        {"temp": 26.3, "feels": 27.9, "humidity": 62, "precip": 0.0,
         "wind": 14.0, "code": 2, "is_day": True, "time": "23:15"},
    ),
}

# Day-over-day drift applied to the offline current temperature, plus the
# code each day gets. Index 0 is today.
_OFFLINE_DRIFT = [
    (0.0, None, 20),
    (1.8, 2, 15),
    (-2.4, 80, 55),
    (3.1, 0, 5),
    (-0.7, 3, 35),
    (2.2, 61, 70),
    (0.9, 1, 10),
]


def offline_enabled() -> bool:
    """True when WEATHER_BUDDY_OFFLINE asks us to skip the network."""
    return os.getenv("WEATHER_BUDDY_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}


def offline_cities() -> list[str]:
    """Names of the cities available in offline mode."""
    return sorted(place.name for place, _ in _OFFLINE_PLACES.values())


def _offline_entry(city: str) -> tuple[Place, dict]:
    entry = _OFFLINE_PLACES.get(city.strip().lower().split(",")[0])
    if entry is None:
        raise WeatherError(
            f"Offline mode only knows these cities: {', '.join(offline_cities())}. "
            f"Unset WEATHER_BUDDY_OFFLINE to look up '{city}' for real."
        )
    return entry


# --------------------------------------------------------------------------
# Live API
# --------------------------------------------------------------------------


def _get_json(url: str, params: dict) -> dict:
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT_S)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise WeatherError(f"Could not reach the weather service: {exc}") from exc


def geocode(city: str) -> Place:
    """Resolve a city name to coordinates."""
    if offline_enabled():
        return _offline_entry(city)[0]

    payload = _get_json(GEOCODE_URL, {"name": city, "count": 1, "language": "en", "format": "json"})
    results = payload.get("results") or []
    if not results:
        raise WeatherError(f"I couldn't find a city called '{city}'. Try adding a country, e.g. 'Springfield, US'.")

    hit = results[0]
    return Place(
        name=hit["name"],
        country=hit.get("country", "somewhere"),
        latitude=hit["latitude"],
        longitude=hit["longitude"],
        timezone=hit.get("timezone", "auto"),
    )


def get_current(city: str) -> CurrentWeather:
    """Current conditions for a city."""
    if offline_enabled():
        place, data = _offline_entry(city)
        return CurrentWeather(
            place=place,
            temperature_c=data["temp"],
            feels_like_c=data["feels"],
            humidity=data["humidity"],
            precipitation_mm=data["precip"],
            wind_kph=data["wind"],
            code=data["code"],
            is_day=data["is_day"],
            local_time=data["time"],
        )

    place = geocode(city)
    payload = _get_json(
        FORECAST_URL,
        {
            "latitude": place.latitude,
            "longitude": place.longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "precipitation,weather_code,wind_speed_10m,is_day",
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        },
    )
    current = payload.get("current") or {}
    return CurrentWeather(
        place=place,
        temperature_c=round(float(current.get("temperature_2m", 0.0)), 1),
        feels_like_c=round(float(current.get("apparent_temperature", 0.0)), 1),
        humidity=int(current.get("relative_humidity_2m", 0)),
        precipitation_mm=float(current.get("precipitation", 0.0)),
        wind_kph=round(float(current.get("wind_speed_10m", 0.0)), 1),
        code=int(current.get("weather_code", 0)),
        is_day=bool(current.get("is_day", 1)),
        local_time=str(current.get("time", "")).replace("T", " ")[-5:],
    )


def get_forecast(city: str, days: int = 3) -> tuple[Place, list[DayForecast]]:
    """Daily forecast for a city, today first."""
    days = max(1, min(int(days), 7))

    if offline_enabled():
        place, data = _offline_entry(city)
        today = dt.date.today()
        forecast = []
        for index in range(days):
            drift, code, precip_chance = _OFFLINE_DRIFT[index]
            base = data["temp"] + drift
            forecast.append(
                DayForecast(
                    date=(today + dt.timedelta(days=index)).isoformat(),
                    code=data["code"] if code is None else code,
                    high_c=round(base + 3.5, 1),
                    low_c=round(base - 4.5, 1),
                    precip_chance=precip_chance,
                )
            )
        return place, forecast

    place = geocode(city)
    payload = _get_json(
        FORECAST_URL,
        {
            "latitude": place.latitude,
            "longitude": place.longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": days,
            "timezone": "auto",
        },
    )
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    forecast = [
        DayForecast(
            date=dates[i],
            code=int(daily["weather_code"][i]),
            high_c=round(float(daily["temperature_2m_max"][i]), 1),
            low_c=round(float(daily["temperature_2m_min"][i]), 1),
            precip_chance=int(daily.get("precipitation_probability_max", [0] * len(dates))[i] or 0),
        )
        for i in range(len(dates))
    ]
    if not forecast:
        raise WeatherError(f"The weather service returned no forecast for {place.label}.")
    return place, forecast
