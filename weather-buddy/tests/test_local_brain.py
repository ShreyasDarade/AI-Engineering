"""Tests for the free, no-LLM brain."""

import pytest

from weather_buddy.local_brain import LocalBrain


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WEATHER_BUDDY_OFFLINE", "1")


@pytest.fixture
def bot():
    return LocalBrain()


def test_greeting_does_not_need_a_city(bot):
    assert "Name a city" in bot.respond("hey")


def test_help_lists_what_it_can_do(bot):
    assert "showdown" in bot.respond("help").lower()


def test_plain_city_name_returns_current_weather(bot):
    assert "Tokyo, Japan" in bot.respond("Tokyo")


def test_natural_question_returns_current_weather(bot):
    reply = bot.respond("what's it like in Tokyo right now?")
    assert "Tokyo, Japan" in reply
    assert "/10" in reply


def test_outfit_intent_is_detected(bot):
    reply = bot.respond("should I bring a jacket in Reykjavik?")
    assert "Dressing for Reykjavik" in reply


def test_forecast_intent_is_detected(bot):
    assert "next 5 day(s)" in bot.respond("give me 5 days for Sydney")


def test_week_means_seven_days(bot):
    assert "next 7 day(s)" in bot.respond("forecast for London this week")


def test_showdown_on_vs(bot):
    assert "WEATHER SHOWDOWN" in bot.respond("Pittsburgh vs Cairo")


def test_showdown_on_or(bot):
    assert "WEATHER SHOWDOWN" in bot.respond("Tokyo or London")


def test_follow_up_reuses_the_last_city(bot):
    bot.respond("how's Tokyo?")
    assert "Tokyo, Japan" in bot.respond("and tomorrow?")


def test_reset_forgets_the_last_city(bot):
    bot.respond("how's Tokyo?")
    bot.reset()
    assert "Which city" in bot.respond("and tomorrow?")


def test_no_city_asks_for_one(bot):
    assert "Which city" in bot.respond("what's the weather")


def test_unknown_city_is_reported_not_raised(bot):
    assert "Offline mode only knows" in bot.respond("weather in Atlantis")


def test_thanks_gets_a_quip(bot):
    assert "jet stream" in bot.respond("thanks!")
