"""Tests for the vibe engine."""

import pytest

from weather_buddy import fun
from weather_buddy import weather_api as api


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WEATHER_BUDDY_OFFLINE", "1")


def test_pleasant_weather_scores_higher_than_a_blizzard():
    tokyo = fun.vibe_check(api.get_current("Tokyo"))
    reykjavik = fun.vibe_check(api.get_current("Reykjavik"))
    assert tokyo.score > reykjavik.score


def test_score_stays_inside_zero_to_ten():
    for city in api.offline_cities():
        score = fun.vibe_check(api.get_current(city)).score
        assert 0.0 <= score <= 10.0


def test_vibe_bar_is_always_ten_cells():
    for city in api.offline_cities():
        assert len(fun.vibe_check(api.get_current(city)).bar) == 10


def test_vibe_is_deterministic():
    current = api.get_current("London")
    assert fun.vibe_check(current) == fun.vibe_check(current)


def test_cold_city_gets_a_winter_coat():
    advice = " ".join(fun.outfit_call(api.get_current("Reykjavik"))).lower()
    assert "coat" in advice or "layer" in advice


def test_rain_gets_an_umbrella():
    advice = " ".join(fun.outfit_call(api.get_current("Pittsburgh"))).lower()
    assert "umbrella" in advice


def test_hot_city_gets_a_hydration_reminder():
    advice = " ".join(fun.outfit_call(api.get_current("Cairo"))).lower()
    assert "hydrate" in advice or "water" in advice


def test_bad_weather_suggests_staying_in():
    assert "stay in" in fun.activity_pick(api.get_current("Reykjavik"))


def test_report_card_mentions_the_city_and_a_score():
    card = fun.report_card(api.get_current("Tokyo"))
    assert "Tokyo" in card
    assert "/10" in card


def test_showdown_picks_the_nicer_city():
    result = fun.showdown(api.get_current("Tokyo"), api.get_current("Reykjavik"))
    assert "Tokyo takes it" in result


def test_showdown_is_order_independent_about_the_winner():
    result = fun.showdown(api.get_current("Reykjavik"), api.get_current("Tokyo"))
    assert "Tokyo takes it" in result


def test_forecast_card_has_a_row_per_day():
    place, forecast = api.get_forecast("Sydney", days=3)
    card = fun.forecast_card(place, forecast)
    assert card.count("rain") == 3
