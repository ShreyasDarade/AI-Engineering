"""Tests for the agent loop, using a stand-in chat model.

No API key and no network: a fake model plays the part of Claude, emitting a
tool call and then a final answer, which is enough to prove the wiring works.
"""

from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from weather_buddy.agent import SYSTEM_PROMPT, WeatherChat, build_agent
from weather_buddy.tools import ALL_TOOLS


class FakeToolCaller(BaseChatModel):
    """Calls get_weather once, then answers."""

    calls: int = 0
    seen_history_lengths: list[int] = []

    @property
    def _llm_type(self) -> str:
        return "fake-tool-caller"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolCaller":
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.calls += 1
        if self.calls % 2 == 1:
            self.seen_history_lengths.append(len(messages))
            message = AIMessage(
                content="",
                tool_calls=[{"name": "get_weather", "args": {"city": "Tokyo"}, "id": f"call_{self.calls}"}],
            )
        else:
            message = AIMessage(content="Tokyo is showing off again. Go outside. \U0001f31e")
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WEATHER_BUDDY_OFFLINE", "1")


def test_system_prompt_forbids_guessing():
    assert "Never guess" in SYSTEM_PROMPT


def test_all_four_tools_are_registered():
    assert [t.name for t in ALL_TOOLS] == [
        "get_weather",
        "get_multi_day_forecast",
        "weather_showdown",
        "what_should_i_wear",
    ]


def test_every_tool_has_a_description_for_the_model():
    assert all(t.description.strip() for t in ALL_TOOLS)


def test_agent_calls_a_tool_and_returns_a_final_answer():
    executor = build_agent(llm=FakeToolCaller())
    executor.return_intermediate_steps = True
    result = executor.invoke({"input": "how's Tokyo?", "chat_history": []})
    assert "Go outside" in result["output"]
    # The tool actually ran, and its output made it into the scratchpad.
    assert any("Tokyo, Japan" in str(step[1]) for step in result["intermediate_steps"])


def test_chat_remembers_the_conversation():
    chat = WeatherChat(llm=FakeToolCaller())
    chat.ask("how's Tokyo?")
    chat.ask("and tomorrow?")
    assert len(chat.history) == 4  # two human turns, two AI turns
    assert chat.history[0].content == "how's Tokyo?"


def test_history_is_trimmed_to_max_turns():
    chat = WeatherChat(llm=FakeToolCaller(), max_turns=2)
    for _ in range(5):
        chat.ask("again")
    assert len(chat.history) == 4  # 2 turns == 4 messages


def test_reset_clears_memory():
    chat = WeatherChat(llm=FakeToolCaller())
    chat.ask("how's Tokyo?")
    chat.reset()
    assert chat.history == []


def test_tool_reports_a_bad_city_instead_of_raising():
    result = ALL_TOOLS[0].invoke({"city": "Narnia"})
    assert "failed" in result.lower()
