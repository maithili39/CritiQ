"""
Unit tests for the LLM client wrapper: retry/backoff classification, the
Anthropic and Groq call paths, tool-schema translation, and — critically —
malformed provider responses (no tool call, bad JSON), which the rest of the
suite never exercises because its mocks are always well-formed.
"""

import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest

import app.services.llm as llm

_TOOL = {
    "name": "record_thing",
    "description": "records a thing",
    "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
}


def _status_error(status_code: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.test")
    response = httpx.Response(status_code, request=request)
    return anthropic.APIStatusError("boom", response=response, body=None)


def _connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.test"))


def _anthropic_message(blocks):
    return SimpleNamespace(content=blocks)


def _tool_use_block(payload: dict):
    return SimpleNamespace(type="tool_use", input=payload)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Backoff sleeps must not slow the suite down."""
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)


@pytest.fixture()
def fake_anthropic(monkeypatch):
    """Installs a fake Anthropic client; returns a mutable holder for its behavior."""
    holder = {"responses": [], "calls": []}

    def create(**kwargs):
        holder["calls"].append(kwargs)
        result = holder["responses"].pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(llm, "_client", client)
    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "anthropic")
    return holder


# --- retry classification ---


def test_retries_transient_error_then_succeeds(fake_anthropic):
    ok = _anthropic_message([_tool_use_block({"x": "hi"})])
    fake_anthropic["responses"] = [_connection_error(), _status_error(529), ok]
    result = llm.call_tool(model="m", max_tokens=64, system="s", user_content="u", tool=_TOOL)
    assert result == {"x": "hi"}
    assert len(fake_anthropic["calls"]) == 3  # two failures retried, third succeeded


def test_non_retryable_400_fails_fast(fake_anthropic):
    fake_anthropic["responses"] = [_status_error(400)]
    with pytest.raises(anthropic.APIStatusError):
        llm.call_tool(model="m", max_tokens=64, system="s", user_content="u", tool=_TOOL)
    assert len(fake_anthropic["calls"]) == 1  # no pointless retries of a bad request


def test_gives_up_after_max_retries(fake_anthropic):
    fake_anthropic["responses"] = [_connection_error()] * llm.MAX_RETRIES
    with pytest.raises(anthropic.APIConnectionError):
        llm.call_tool(model="m", max_tokens=64, system="s", user_content="u", tool=_TOOL)
    assert len(fake_anthropic["calls"]) == llm.MAX_RETRIES


# --- Anthropic call path ---


def test_anthropic_forces_tool_choice_and_caches_system(fake_anthropic):
    fake_anthropic["responses"] = [_anthropic_message([_tool_use_block({"x": "v"})])]
    llm.call_tool(model="m", max_tokens=64, system="persona text", user_content="u", tool=_TOOL)
    kwargs = fake_anthropic["calls"][0]
    assert kwargs["tool_choice"] == {"type": "tool", "name": "record_thing"}
    assert kwargs["system"][0]["text"] == "persona text"
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_anthropic_cache_system_false_omits_cache_control(fake_anthropic):
    fake_anthropic["responses"] = [_anthropic_message([_tool_use_block({"x": "v"})])]
    llm.call_tool(model="m", max_tokens=64, system="s", user_content="u", tool=_TOOL, cache_system=False)
    assert "cache_control" not in fake_anthropic["calls"][0]["system"][0]


def test_anthropic_malformed_response_without_tool_use_raises(fake_anthropic):
    # e.g. a truncated/refused response with only a text block
    fake_anthropic["responses"] = [_anthropic_message([SimpleNamespace(type="text", text="I cannot")])]
    with pytest.raises(ValueError, match="Expected a tool_use block"):
        llm.call_tool(model="m", max_tokens=64, system="s", user_content="u", tool=_TOOL)


# --- Groq call path ---


@pytest.fixture()
def fake_groq(monkeypatch):
    holder = {"responses": [], "calls": []}

    def create(**kwargs):
        holder["calls"].append(kwargs)
        result = holder["responses"].pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_client", client)
    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "groq")
    return holder


def _groq_message(tool_calls):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=tool_calls))])


def test_groq_translates_tool_schema_and_parses_arguments(fake_groq):
    call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps({"x": "from groq"})))
    fake_groq["responses"] = [_groq_message([call])]
    result = llm.call_tool(model="m", max_tokens=64, system="sys", user_content="u", tool=_TOOL)
    assert result == {"x": "from groq"}

    kwargs = fake_groq["calls"][0]
    # Anthropic tool dict translated to OpenAI function-calling shape, choice forced.
    assert kwargs["tools"] == [
        {
            "type": "function",
            "function": {"name": "record_thing", "description": "records a thing",
                         "parameters": _TOOL["input_schema"]},
        }
    ]
    assert kwargs["tool_choice"] == {"type": "function", "function": {"name": "record_thing"}}
    # system goes in as the first chat message, not a top-level param
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}


def test_groq_missing_tool_call_raises(fake_groq):
    fake_groq["responses"] = [_groq_message(None)]
    with pytest.raises(ValueError, match="Expected a tool call from Groq"):
        llm.call_tool(model="m", max_tokens=64, system="s", user_content="u", tool=_TOOL)


def test_groq_malformed_json_arguments_raises(fake_groq):
    call = SimpleNamespace(function=SimpleNamespace(arguments='{"x": "truncat'))
    fake_groq["responses"] = [_groq_message([call])]
    with pytest.raises(json.JSONDecodeError):
        llm.call_tool(model="m", max_tokens=64, system="s", user_content="u", tool=_TOOL)
