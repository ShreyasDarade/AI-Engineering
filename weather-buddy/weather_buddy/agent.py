"""The LangChain agent: an LLM with a personality and four weather tools."""

from __future__ import annotations

import os

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .tools import ALL_TOOLS

DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are Sunny, a weather gremlin who lives in a terminal and \
has extremely strong opinions about the sky.

Personality:
- Warm, funny, a little dramatic. Short sentences. Never corporate.
- You treat weather like a sport you commentate on.
- One emoji here and there is plenty. You are not a keyboard.

Rules:
- ALWAYS use your tools for anything about real conditions. Never guess a \
temperature, a forecast, or a vibe score -- you are chronically wrong when you improvise.
- Show the tool's formatted block to the user as-is, then add one or two lines \
of your own commentary on top. Don't restate the numbers you just showed.
- If the user names two cities, run the showdown.
- If a lookup fails, say so plainly and suggest a fix (add a country, check the spelling).
- Off-topic questions are fine -- answer briefly, then steer back to the sky.

Keep replies under about eight lines unless the user asks for more."""


def build_llm(model: str | None = None) -> ChatAnthropic:
    """Create the chat model. Reads ANTHROPIC_API_KEY from the environment."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set, so --llm can't start (nothing was sent anywhere). "
            "Run `python -m weather_buddy` for the free mode, or add a key to .env if you "
            "specifically want the Claude-powered version -- that one bills your account."
        )
    return ChatAnthropic(
        model=model or os.getenv("WEATHER_BUDDY_MODEL", DEFAULT_MODEL),
        temperature=0.7,
        max_tokens=1024,
    )


def build_agent(
    model: str | None = None,
    verbose: bool = False,
    llm: BaseChatModel | None = None,
) -> AgentExecutor:
    """Wire the prompt, the model and the tools into an executor.

    Pass `llm` to supply your own chat model (tests use this to avoid needing a key).
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm or build_llm(model), ALL_TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=ALL_TOOLS, verbose=verbose, handle_parsing_errors=True)


class WeatherChat:
    """The agent plus conversation memory, so follow-ups like "and tomorrow?" work.

    Memory lives in this process only -- close the CLI and Sunny forgets you.
    """

    def __init__(
        self,
        model: str | None = None,
        verbose: bool = False,
        max_turns: int = 12,
        llm: BaseChatModel | None = None,
    ):
        self.executor = build_agent(model=model, verbose=verbose, llm=llm)
        self.history: list[BaseMessage] = []
        self.max_turns = max_turns

    def ask(self, message: str) -> str:
        result = self.executor.invoke({"input": message, "chat_history": self.history})
        reply = result["output"]
        if isinstance(reply, list):  # content blocks -> plain text
            reply = "".join(block.get("text", "") for block in reply if isinstance(block, dict))

        self.history.extend([HumanMessage(content=message), AIMessage(content=reply)])
        del self.history[: -2 * self.max_turns or None]  # keep the last N exchanges
        return reply

    def reset(self) -> None:
        self.history.clear()
