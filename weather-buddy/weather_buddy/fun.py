"""The fun half of the bot.

Everything here is deterministic: the same weather always produces the same
vibe score and the same verdict. That keeps the bot's opinions consistent
(nothing worse than a weather gremlin that changes its mind) and makes the
whole thing testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from .weather_api import CurrentWeather, DayForecast, Place

# The temperature the gremlin considers objectively perfect.
IDEAL_C = 21.0

# How many vibe points each family of weather codes costs.
_SEVERITY: list[tuple[set[int], float]] = [
    ({0, 1}, 0.0),
    ({2}, 0.3),
    ({3}, 1.0),
    ({45, 48}, 1.8),
    ({51, 53, 55, 56, 57}, 1.5),
    ({61, 63, 80, 81}, 2.5),
    ({65, 66, 67, 82}, 3.5),
    ({71, 73, 77, 85}, 2.0),
    ({75, 86}, 3.0),
    ({95, 96, 99}, 4.0),
]


@dataclass(frozen=True)
class Vibe:
    score: float
    badge: str
    verdict: str

    @property
    def bar(self) -> str:
        """A ten-cell meter, because numbers are boring."""
        filled = int(round(self.score))
        return "█" * filled + "░" * (10 - filled)


def _code_penalty(code: int) -> float:
    for codes, penalty in _SEVERITY:
        if code in codes:
            return penalty
    return 2.0


_VERDICTS: list[tuple[float, str, str]] = [
    (9.0, "\U0001f451", "Weather this good should be illegal. Go outside immediately."),
    (7.5, "\U0001f60e", "Genuinely lovely. No notes."),
    (6.0, "\U0001f642", "Perfectly fine. The weather is doing its job quietly."),
    (4.5, "\U0001f610", "Mediocre. The meteorological equivalent of beige."),
    (3.0, "\U0001f612", "Rude. I'd stay in and blame the sky."),
    (1.5, "\U0001f631", "The sky has personally wronged you today."),
    (0.0, "\U0001f480", "Absolutely feral out there. Cancel everything."),
]


def vibe_check(current: CurrentWeather) -> Vibe:
    """Score the weather out of 10 and pass judgement."""
    score = 10.0
    score -= abs(current.feels_like_c - IDEAL_C) * 0.22   # too hot or too cold
    score -= _code_penalty(current.code)                   # what's falling out of the sky
    score -= min(current.wind_kph / 18.0, 2.5)             # wind is the silent vibe killer
    score -= min(current.precipitation_mm * 0.8, 2.0)      # actively raining right now
    if current.humidity > 85:
        score -= 0.5
    score = round(max(0.0, min(10.0, score)), 1)

    for threshold, badge, verdict in _VERDICTS:
        if score >= threshold:
            return Vibe(score=score, badge=badge, verdict=verdict)
    return Vibe(score=score, badge="\U0001f480", verdict=_VERDICTS[-1][2])


def outfit_call(current: CurrentWeather) -> list[str]:
    """What to actually put on your body."""
    feels = current.feels_like_c
    items: list[str] = []

    if feels <= -10:
        items.append("Every layer you own. Yes, that one too.")
        items.append("Hat, gloves, scarf -- this is not negotiable")
    elif feels <= 0:
        items.append("Proper winter coat")
        items.append("Gloves, and something over your ears")
    elif feels <= 10:
        items.append("Jacket over a long sleeve")
    elif feels <= 18:
        items.append("Light jacket or a hoodie you can take off")
    elif feels <= 26:
        items.append("T-shirt weather. Live your life.")
    elif feels <= 33:
        items.append("Shorts, lightest fabric available")
        items.append("Water bottle, genuinely")
    else:
        items.append("Minimal clothing and maximal shade")
        items.append("Hydrate like it's your job")

    if current.code in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}:
        items.append("Umbrella -- and I mean a real one, not the one that inverts")
    if current.code in {71, 73, 75, 77, 85, 86}:
        items.append("Boots with actual grip")
    if current.wind_kph >= 35:
        items.append("Skip the hairstyle. The wind has other plans.")
    if current.code in {0, 1} and current.is_day and feels > 15:
        items.append("Sunglasses")
    if current.humidity > 85 and feels > 22:
        items.append("A second shirt for later. Trust me.")

    return items


_INDOOR = [
    "build an elaborate blanket fort and defend it",
    "start the movie trilogy you keep threatening to rewatch",
    "bake something that makes the whole place smell good",
    "finally sort out that one drawer",
]

_OUTDOOR = [
    "take the long way somewhere on foot",
    "find a park bench and do absolutely nothing in it",
    "get a coffee and walk with no destination",
    "sit outside and pretend you're in a montage",
]


def activity_pick(current: CurrentWeather) -> str:
    """Suggest something to do, matched to the conditions."""
    vibe = vibe_check(current)
    pool = _OUTDOOR if vibe.score >= 5.5 else _INDOOR
    # Deterministic pick: same weather, same suggestion.
    index = (int(vibe.score * 10) + current.code) % len(pool)
    verb = "Perfect day to" if pool is _OUTDOOR else "Strong day to stay in and"
    return f"{verb} {pool[index]}."


def report_card(current: CurrentWeather) -> str:
    """The full formatted read-out for one city."""
    vibe = vibe_check(current)
    part_of_day = "daytime" if current.is_day else "nighttime"
    lines = [
        f"{current.emoji}  {current.place.label} -- {current.description}, {part_of_day} ({current.local_time} local)",
        f"    Temp:  {current.temperature_c}°C / {current.temperature_f}°F "
        f"(feels like {current.feels_like_c}°C / {current.feels_like_f}°F)",
        f"    Wind:  {current.wind_kph} km/h    Humidity: {current.humidity}%    "
        f"Precip: {current.precipitation_mm} mm",
        f"    Vibe:  {vibe.bar}  {vibe.score}/10 {vibe.badge}  {vibe.verdict}",
        f"    Wear:  {'; '.join(outfit_call(current))}",
        f"    Plan:  {activity_pick(current)}",
    ]
    return "\n".join(lines)


def forecast_card(place: Place, days: list[DayForecast]) -> str:
    """A compact multi-day table."""
    lines = [f"\U0001f4c5  {place.label} -- next {len(days)} day(s)"]
    for day in days:
        lines.append(
            f"    {day.weekday} {day.date}  {day.emoji}  {day.description:<22}"
            f" {day.high_c:>5.1f}°C / {day.low_c:>5.1f}°C   rain {day.precip_chance:>3}%"
        )
    return "\n".join(lines)


def showdown(left: CurrentWeather, right: CurrentWeather) -> str:
    """Two cities enter, one city leaves."""
    left_vibe, right_vibe = vibe_check(left), vibe_check(right)
    gap = round(abs(left_vibe.score - right_vibe.score), 1)

    if gap < 0.3:
        headline = "It's a dead heat. Both skies are equally committed to mediocrity."
    else:
        winner = left if left_vibe.score > right_vibe.score else right
        margin = (
            "in a landslide" if gap >= 4 else
            "comfortably" if gap >= 2 else
            "by a nose"
        )
        headline = f"\U0001f3c6 {winner.place.name} takes it {margin} (+{gap} vibe points)."

    return "\n".join([
        "\U0001f94a  WEATHER SHOWDOWN",
        f"    {left.place.name:<14} {left_vibe.bar} {left_vibe.score}/10  "
        f"{left.emoji} {left.description}, {left.temperature_c}°C",
        f"    {right.place.name:<14} {right_vibe.bar} {right_vibe.score}/10  "
        f"{right.emoji} {right.description}, {right.temperature_c}°C",
        f"    {headline}",
    ])
