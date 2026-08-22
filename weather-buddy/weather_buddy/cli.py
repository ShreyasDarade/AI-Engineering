"""Terminal front-end for Sunny the weather gremlin."""

from __future__ import annotations

import argparse
import os
import sys

from . import fun
from .weather_api import WeatherError, get_current, get_forecast, offline_cities

BANNER = r"""
   _____                          
  / ____|                         
 | (___  _   _ _ __  _ __  _   _  
  \___ \| | | | '_ \| '_ \| | | | 
  ____) | |_| | | | | | | | |_| | 
 |_____/ \__,_|_| |_|_| |_|\__, | 
                            __/ | 
   your local weather      |___/  gremlin
"""

HELP_TEXT = """
Try things like:
    what's it like in Tokyo?
    should I bring a jacket in London?
    Pittsburgh vs Cairo
    give me 5 days for Sydney

Commands:
    /help     this message
    /cities   cities available in offline mode
    /reset    forget the conversation so far
    /quit     leave (or Ctrl-D)
"""


def _print_help() -> None:
    print(HELP_TEXT)


def run_demo(cities: list[str]) -> int:
    """The no-API-key tour: runs the tools directly, no LLM involved."""
    print(BANNER)
    print("DEMO MODE -- tools only, no LLM. Add an ANTHROPIC_API_KEY for the chatty version.\n")

    try:
        for city in cities:
            print(fun.report_card(get_current(city)))
            print()

        place, forecast = get_forecast(cities[0], 5)
        print(fun.forecast_card(place, forecast))
        print()

        if len(cities) >= 2:
            print(fun.showdown(get_current(cities[0]), get_current(cities[1])))
            print()
    except WeatherError as exc:
        print(f"\U0001f622  {exc}", file=sys.stderr)
        return 1

    print("That's the tour. Run without --demo to actually talk to Sunny.")
    return 0


def run_chat(model: str | None, verbose: bool) -> int:
    """The real thing: a LangChain agent loop with memory."""
    # Imported lazily so --demo works without the LangChain stack installed.
    from .agent import WeatherChat

    try:
        chat = WeatherChat(model=model, verbose=verbose)
    except RuntimeError as exc:
        print(f"\U0001f6ab  {exc}", file=sys.stderr)
        return 1

    print(BANNER)
    print("Ask me about the weather anywhere. /help for ideas, /quit to leave.\n")

    while True:
        try:
            user_input = input("you  ▸ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nsunny ▸ Go outside. Or don't. I'm a gremlin, not a cop. \U0001f44b")
            return 0

        if not user_input:
            continue
        if user_input in {"/quit", "/exit", "/q"}:
            print("\nsunny ▸ Go outside. Or don't. I'm a gremlin, not a cop. \U0001f44b")
            return 0
        if user_input == "/help":
            _print_help()
            continue
        if user_input == "/cities":
            print(f"\nOffline cities: {', '.join(offline_cities())}\n")
            continue
        if user_input == "/reset":
            chat.reset()
            print("\nsunny ▸ Memory wiped. Who are you again?\n")
            continue

        try:
            print(f"\nsunny ▸ {chat.ask(user_input)}\n")
        except Exception as exc:  # noqa: BLE001 - never kill the REPL on one bad turn
            print(f"\nsunny ▸ Something went sideways: {exc}\n", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="weather_buddy",
        description="Sunny: a LangChain weather chatbot with opinions.",
    )
    parser.add_argument(
        "--demo",
        nargs="*",
        metavar="CITY",
        help="Run the tools directly on some cities and exit. No API key needed.",
    )
    parser.add_argument("--offline", action="store_true", help="Use built-in demo cities, no network.")
    parser.add_argument("--model", default=None, help="Override the model (default: env or claude-sonnet-5).")
    parser.add_argument("--verbose", action="store_true", help="Show the agent's tool calls.")
    args = parser.parse_args(argv)

    if args.offline:
        os.environ["WEATHER_BUDDY_OFFLINE"] = "1"

    if args.demo is not None:
        cities = args.demo or ["Pittsburgh", "Cairo"]
        return run_demo(cities)

    return run_chat(model=args.model, verbose=args.verbose)
