"""Tests for the Open-Meteo layer. These run entirely offline."""

import datetime as dt

import pytest

from weather_buddy import weather_api as api


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WEATHER_BUDDY_OFFLINE", "1")


def test_describe_and_emoji_known_code():
    assert api.describe(0) == "clear sky"
    assert api.emoji_for(0) == "☀️"


def test_describe_unknown_code_falls_back():
    assert api.describe(1234) == "mystery weather"


def test_geocode_is_case_and_country_insensitive():
    assert api.geocode("TOKYO").name == "Tokyo"
    assert api.geocode("tokyo, japan").name == "Tokyo"


def test_unknown_city_raises_with_a_helpful_message():
    with pytest.raises(api.WeatherError, match="Offline mode only knows"):
        api.geocode("Atlantis")


def test_current_weather_converts_to_fahrenheit():
    current = api.get_current("Cairo")
    assert current.temperature_c == 38.9
    assert current.temperature_f == 102.0
    assert current.description == "clear sky"


def test_forecast_length_is_clamped_to_seven():
    _, forecast = api.get_forecast("Tokyo", days=99)
    assert len(forecast) == 7


def test_forecast_length_is_clamped_to_one():
    _, forecast = api.get_forecast("Tokyo", days=0)
    assert len(forecast) == 1


def test_forecast_starts_today_and_is_consecutive():
    _, forecast = api.get_forecast("London", days=4)
    dates = [dt.date.fromisoformat(day.date) for day in forecast]
    assert dates[0] == dt.date.today()
    assert all((b - a).days == 1 for a, b in zip(dates, dates[1:]))


def test_forecast_high_is_above_low():
    _, forecast = api.get_forecast("Sydney", days=5)
    assert all(day.high_c > day.low_c for day in forecast)


def test_offline_cities_are_listed():
    assert "Reykjavik" in api.offline_cities()
