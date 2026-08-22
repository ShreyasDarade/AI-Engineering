# ☀️ Sunny — the weather gremlin

A small LangChain chatbot with a personality problem. Ask it about the weather
anywhere in the world and it will tell you the numbers, rate the vibe out of 10,
tell you what to wear, suggest what to do with your day, and — if you name two
cities — pit them against each other in a **weather showdown**.

**Runs free by default** — no API key, no account, nothing billable. Weather comes
from [Open-Meteo](https://open-meteo.com), which is keyless and accountless. An
optional `--llm` flag swaps the rule-based brain for a Claude-powered LangChain
agent, if you want that and are happy to spend your own API credits.

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
python -m weather_buddy          # free mode. No key, no account, no charges.
```

Other ways to run it:

```bash
python -m weather_buddy --demo                 # scripted tour of the tools, then exit
python -m weather_buddy --demo Tokyo Cairo     # tour your own cities
python -m weather_buddy --offline              # built-in city data, zero network calls
python -m weather_buddy --llm                  # opt in to the Claude agent (see below)
```

## Cost, and what talks to what

| Mode | Reaches out to | Can it bill you? |
| --- | --- | --- |
| default | Open-Meteo (keyless, accountless) | **No** — there is no account to charge |
| `--offline` | nothing at all | **No** |
| `--demo` | Open-Meteo, unless combined with `--offline` | **No** |
| `--llm` | Open-Meteo **+ the Anthropic API** | **Yes** — your `ANTHROPIC_API_KEY`, your credits |

Only `--llm` can cost money, and only if you set `ANTHROPIC_API_KEY` yourself.
With no key set, that mode refuses to start rather than connecting to anything.
No key is stored in this repo; `.env` is gitignored and `.env.example` holds a
placeholder. LangSmith tracing is not enabled.

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

The free brain understands all of the above. It falls back to asking which city
you meant when it can't parse one; `--llm` handles fuzzier phrasing.

## How it fits together

```
cli.py            one REPL, two interchangeable brains
  ├── local_brain.py   DEFAULT: keyword routing. Free, offline-capable, no LLM.
  └── agent.py         --llm ONLY: ChatAnthropic + create_tool_calling_agent
        │              WeatherChat adds memory (last 12 exchanges)
        └── tools.py      four @tool functions the model can call
              ├── weather_api.py   Open-Meteo client, WMO code table, dataclasses
              └── fun.py           vibe scoring, outfit rules, showdown formatting
```

Both brains sit behind the same REPL and drive the same underlying functions, so
the bot behaves the same either way — the LLM just phrases things better and
handles messages the keyword router doesn't understand.

Three deliberate choices:

- **The tools return finished, formatted text, not JSON.** The model adds
  commentary on top instead of re-reading numbers back to you, and the output
  looks good even on a turn where the model is being lazy.
- **The LLM is a swappable upgrade, not a dependency.** All the weather logic
  lives below the tool layer, so the free brain and the Claude agent share it.
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
| `ANTHROPIC_API_KEY` | unset | **Only** used by `--llm`. Leave unset and nothing is billable. |
| `WEATHER_BUDDY_MODEL` | `claude-sonnet-5` | Which model `--llm` uses |
| `WEATHER_BUDDY_OFFLINE` | unset | `1` to use built-in demo cities |

## Tests

```bash
python -m pytest -q      # 44 tests, no network, no API key
```

`tests/test_agent.py` drives the real `AgentExecutor` with a fake chat model
that emits a tool call and then an answer, so the agent loop is covered without
ever calling the API.
