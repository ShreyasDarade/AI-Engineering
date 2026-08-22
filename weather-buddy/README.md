# ☀️ Sunny — the weather gremlin

A small LangChain chatbot with a personality problem. Ask it about the weather
anywhere in the world and it will tell you the numbers, rate the vibe out of 10,
tell you what to wear, suggest what to do with your day, and — if you name two
cities — pit them against each other in a **weather showdown**.

Powered by [Claude](https://www.anthropic.com/claude) via LangChain, with live data from
[Open-Meteo](https://open-meteo.com) (free, no API key, no signup).

```
you  ▸ pittsburgh or cairo, which one wins today?

sunny ▸ Oh, this one isn't close. Cairo is out here running a furnace and
        Pittsburgh is drizzling on itself. Bring water to one and an umbrella
        to the other.

🥊  WEATHER SHOWDOWN
    Pittsburgh     ███░░░░░░░ 2.8/10  🌦️ light rain, 8.4°C
    Cairo          █████░░░░░ 4.9/10  ☀️ clear sky, 38.9°C
    🏆 Cairo takes it comfortably (+2.1 vibe points).
```

*The showdown block above is real output; the gremlin's commentary line is an
illustration of the persona.*

## What it can do

| Tool | What the bot does with it |
| --- | --- |
| `get_weather` | Current conditions + vibe score + outfit + an activity idea |
| `get_multi_day_forecast` | 1–7 day daily forecast table |
| `weather_showdown` | Two cities head-to-head, one winner |
| `what_should_i_wear` | Packing/outfit advice for right now |

The model decides which to call. It's told, firmly, never to invent a temperature.

## Quickstart

```bash
cd weather-buddy
pip install -r requirements.txt

cp .env.example .env      # then add your ANTHROPIC_API_KEY
python -m weather_buddy
```

No API key handy? Take the tour — this runs the tools directly, no LLM:

```bash
python -m weather_buddy --demo                    # Pittsburgh vs Cairo
python -m weather_buddy --demo Tokyo Reykjavik    # pick your own
python -m weather_buddy --offline --demo          # built-in data, no network either
```

### Sample output

```
🌦️  Pittsburgh, United States -- light rain, daytime (08:15 local)
    Temp:  8.4°C / 47.1°F (feels like 5.1°C / 41.2°F)
    Wind:  17.0 km/h    Humidity: 71%    Precip: 0.3 mm
    Vibe:  ███░░░░░░░  2.8/10 😱  The sky has personally wronged you today.
    Wear:  Jacket over a long sleeve; Umbrella -- and I mean a real one, not the one that inverts
    Plan:  Strong day to stay in and start the movie trilogy you keep threatening to rewatch.

📅  Pittsburgh, United States -- next 5 day(s)
    Sat 2026-08-22  🌦️  light rain              11.9°C /   3.9°C   rain  20%
    Sun 2026-08-23  ⛅  partly cloudy           13.7°C /   5.7°C   rain  15%
    Mon 2026-08-24  🌦️  light showers            9.5°C /   1.5°C   rain  55%
    Tue 2026-08-25  ☀️  clear sky               15.0°C /   7.0°C   rain   5%
    Wed 2026-08-26  ☁️  overcast                11.2°C /   3.2°C   rain  35%
```

## Things to say to it

```
what's it like in Tokyo?
should I bring a jacket in London?
Pittsburgh vs Cairo
give me 5 days for Sydney
and tomorrow?                 ← it remembers the city you were talking about
```

In-chat commands: `/help`, `/cities`, `/reset`, `/quit`.

## How it fits together

```
cli.py          REPL + the no-LLM --demo tour
  └── agent.py      ChatAnthropic + create_tool_calling_agent + AgentExecutor
        │           WeatherChat adds conversation memory (last 12 exchanges)
        └── tools.py      four @tool functions the model can call
              ├── weather_api.py   Open-Meteo client, WMO code table, dataclasses
              └── fun.py           vibe scoring, outfit rules, showdown formatting
```

Two deliberate choices:

- **The tools return finished, formatted text, not JSON.** The model adds
  commentary on top instead of re-reading numbers back to you, and the output
  looks good even on a turn where the model is being lazy.
- **`fun.py` is pure and deterministic.** The same weather always yields the
  same vibe score, so the bot's opinions are consistent and the whole scoring
  engine is testable without an LLM in the loop.

### The vibe score

Starts at 10 and loses points for deviation from a perfect 21 °C (by *feels
like*, not the raw temperature), whatever is falling out of the sky, wind, and
active precipitation. Clamped to 0–10.

## Offline mode

`WEATHER_BUDDY_OFFLINE=1` (or `--offline`) swaps the live API for six built-in
cities — Pittsburgh, Tokyo, Reykjavik, Cairo, London, Sydney — with fixed data.
It exists for firewalled networks, planes, and the test suite.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Required for chat mode. Not needed for `--demo`. |
| `WEATHER_BUDDY_MODEL` | `claude-sonnet-5` | Which model answers |
| `WEATHER_BUDDY_OFFLINE` | unset | `1` to use built-in demo cities |

## Tests

```bash
python -m pytest -q      # 30 tests, no network, no API key
```

`tests/test_agent.py` drives the real `AgentExecutor` with a fake chat model
that emits a tool call and then an answer, so the agent loop is covered without
ever calling the API.
