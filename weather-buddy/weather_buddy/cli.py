"""Terminal front-end for Sunny the weather gremlin."""

from __future__ import annotations

import argparse
import os
import sys

from . import fun
from .local_brain import HELP, LocalBrain
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

SIGN_OFF = "\nsunny ▸ Go outside. Or don't. I'm a gremlin, not a cop. \U0001f44b"

BILLING_NOTICE = """\
\u26a0\ufe0f  --llm mode sends your messages to the Anthropic API using your own
    ANTHROPIC_API_KEY, which is billed to your account. Ctrl-C to back out.
    The default mode (no --llm) costs nothing.
"""


def _handle_command(command: str, bot) -> bool:
    """Handle a /command. Returns False when the user wants to leave."""
    if command in {"/quit", "/exit", "/q"}:
        return False
    if command == "/help":
        print(f"\n{HELP}\n")
    elif command == "/cities":
        print(f"\nOffline cities: {', '.join(offline_cities())}\n")
    elif command == "/reset":
        bot.reset()
        print("\nsunny ▸ Memory wiped. Who are you again?\n")
    else:
        print(f"\nUnknown command {command}. Try /help.\n")
    return True


def _repl(bot, answer, subtitle: str) -> int:
    """Shared chat loop. `answer` turns a message into a reply string."""
    print(BANNER)
    print(subtitle + "\n")

    while True:
        try:
            user_input = input("you  ▸ ").strip()
        except (EOFError, KeyboardInterrupt):
            print(SIGN_OFF)
            return 0

        if not user_input:
            continue
        if user_input.startswith("/"):
            if not _handle_command(user_input, bot):
                print(SIGN_OFF)
                return 0
            continue

        try:
            print(f"\nsunny ▸ {answer(user_input)}\n")
        except Exception as exc:  # noqa: BLE001 - never kill the REPL on one bad turn
            print(f"\nsunny ▸ Something went sideways: {exc}\n", file=sys.stderr)


def run_local() -> int:
    """Default mode: rule-based chat. No LLM, no API key, no charges."""
    bot = LocalBrain()
    return _repl(bot, bot.respond, "Free mode -- no LLM, no API key. /help for ideas, /quit to leave.")


def run_demo(cities: list[str]) -> int:
    """The no-API-key tour: runs the tools directly, no LLM involved."""
    print(BANNER)
    print("DEMO MODE -- a scripted tour of the tools. No LLM, no API key, no charges.\n")

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

    print("That's the tour. Run without --demo to chat (still free).")
    return 0


def run_chat(model: str | None, verbose: bool) -> int:
    """Opt-in mode: a LangChain agent driven by Claude. Uses your API credits."""
    # Imported lazily so the free modes work without the LangChain stack installed.
    from .agent import WeatherChat

    print(BILLING_NOTICE)
    try:
        chat = WeatherChat(model=model, verbose=verbose)
    except RuntimeError as exc:
        print(f"\U0001f6ab  {exc}", file=sys.stderr)
        return 1

    return _repl(chat, chat.ask, "LLM mode -- powered by Claude. /help for ideas, /quit to leave.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="weather_buddy",
        description="Sunny: a LangChain weather chatbot with opinions.",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use the Claude-powered LangChain agent. Requires ANTHROPIC_API_KEY and bills your account.",
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

    if args.llm:
        return run_chat(model=args.model, verbose=args.verbose)

    return run_local()
