"""
Shared LLM client + resilient call helper.

All LLM-backed services (resume parsing, question generation, answer evaluation,
report generation) go through `create_message` so that:
  - a single client is reused process-wide (connection pooling),
  - transient API failures (overloaded / rate-limit / timeout / connection) are
    retried with exponential backoff instead of surfacing as a 500 mid-interview,
  - non-transient errors (bad request, auth) fail fast without pointless retries.

Provider is selected via settings.LLM_PROVIDER ("anthropic" or "groq"). Callers
only ever use `call_tool()` with Anthropic-shaped tool dicts
({"name", "description", "input_schema"}) — the Groq path translates that shape
to OpenAI-style function-calling internally, so nothing outside this module
needs to know which provider is active.
"""

import json
import logging
import time

import anthropic
import groq

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None

# Errors worth retrying: the request was fine, the service was momentarily unavailable.
_ANTHROPIC_RETRYABLE = (
    anthropic.APIStatusError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
)
_GROQ_RETRYABLE = (
    groq.APIStatusError,
    groq.APIConnectionError,
    groq.APITimeoutError,
)

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0


def get_client():
    global _client
    if _client is None:
        if settings.LLM_PROVIDER == "groq":
            _client = groq.Groq(api_key=settings.GROQ_API_KEY)
        else:
            _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _is_retryable(exc: Exception) -> bool:
    # Only retry server-side/transient status codes; a 400/401/403 won't fix itself.
    if isinstance(exc, (anthropic.APIStatusError, groq.APIStatusError)):
        return exc.status_code in (408, 409, 425, 429, 500, 502, 503, 504, 529)
    return isinstance(
        exc, (anthropic.APIConnectionError, anthropic.APITimeoutError, groq.APIConnectionError, groq.APITimeoutError)
    )


def create_message(_retryable_errors, **kwargs):
    """Provider-agnostic retry wrapper. `_retryable_errors` is the exception tuple
    to catch for the active provider (Anthropic and Groq raise different classes)."""
    client = get_client()
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if settings.LLM_PROVIDER == "groq":
                return client.chat.completions.create(**kwargs)
            return client.messages.create(**kwargs)
        except _retryable_errors as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES:
                break
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "LLM call failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt,
                MAX_RETRIES,
                exc,
                delay,
            )
            time.sleep(delay)

    logger.error("LLM call failed after %d attempts: %s", MAX_RETRIES, last_exc)
    raise last_exc


def _anthropic_tool_to_openai_function(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool["input_schema"],
        },
    }


def call_tool(
    *,
    model: str,
    max_tokens: int,
    system: str,
    user_content: str,
    tool: dict,
    cache_system: bool = True,
) -> dict:
    """
    Calls the active LLM provider with a single tool forced, so the response is
    guaranteed to match `tool["input_schema"]` — no markdown fences, no prose,
    no hand-rolled JSON parsing/retry loop needed on our side.

    `system` is the fixed instructions/persona text. Under Anthropic it's marked
    cacheable by default (`cache_system`): each session calls
    generate_question/evaluate_answer ~8 times with identical system content, so
    caching cuts repeated input-token cost after the first call. Groq has no
    equivalent to Anthropic's prompt caching, so `cache_system` is ignored there.
    """
    start = time.perf_counter()

    if settings.LLM_PROVIDER == "groq":
        message = create_message(
            _GROQ_RETRYABLE,
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            tools=[_anthropic_tool_to_openai_function(tool)],
            tool_choice={"type": "function", "function": {"name": tool["name"]}},
        )
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info("LLM call (%s) took %sms", tool["name"], duration_ms)

        tool_calls = message.choices[0].message.tool_calls
        if not tool_calls:
            raise ValueError(f"Expected a tool call from Groq, got: {message.choices[0].message!r}")
        return json.loads(tool_calls[0].function.arguments)

    system_param = [
        {
            "type": "text",
            "text": system,
            **({"cache_control": {"type": "ephemeral"}} if cache_system else {}),
        }
    ]
    message = create_message(
        _ANTHROPIC_RETRYABLE,
        model=model,
        max_tokens=max_tokens,
        system=system_param,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user_content}],
    )
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info("LLM call (%s) took %sms", tool["name"], duration_ms)

    for block in message.content:
        if block.type == "tool_use":
            return block.input

    raise ValueError(f"Expected a tool_use block from Claude, got: {message.content!r}")
