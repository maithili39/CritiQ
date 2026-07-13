"""
Shared Claude client + resilient call helper.

All LLM-backed services (resume parsing, question generation, answer evaluation,
report generation) go through `create_message` so that:
  - a single Anthropic client is reused process-wide (connection pooling),
  - transient API failures (overloaded / rate-limit / timeout / connection) are
    retried with exponential backoff instead of surfacing as a 500 mid-interview,
  - non-transient errors (bad request, auth) fail fast without pointless retries.
"""

import logging
import time

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None

# Errors worth retrying: the request was fine, the service was momentarily unavailable.
_RETRYABLE = (
    anthropic.APIStatusError,      # includes 429 / 529 (overloaded); filtered by status below
    anthropic.APIConnectionError,  # network blip / DNS / connection reset
    anthropic.APITimeoutError,
)

MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _is_retryable(exc: Exception) -> bool:
    # Only retry server-side/transient status codes; a 400/401/403 won't fix itself.
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code in (408, 409, 425, 429, 500, 502, 503, 504, 529)
    return isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError))


def create_message(**kwargs):
    """Wrapper around client.messages.create with exponential-backoff retries."""
    client = get_client()
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.messages.create(**kwargs)
        except _RETRYABLE as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES:
                break
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "Claude call failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt, MAX_RETRIES, exc, delay,
            )
            time.sleep(delay)

    logger.error("Claude call failed after %d attempts: %s", MAX_RETRIES, last_exc)
    raise last_exc


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
    Calls Claude with a single tool forced via tool_choice, so the response is
    guaranteed to match `tool["input_schema"]` — no markdown fences, no prose,
    no hand-rolled JSON parsing/retry loop needed on our side.

    `system` is the fixed instructions/persona text, marked cacheable by default:
    each session calls generate_question/evaluate_answer ~8 times with identical
    system content, so caching it cuts repeated input-token cost after the first call.
    """
    system_param = [{
        "type": "text",
        "text": system,
        **({"cache_control": {"type": "ephemeral"}} if cache_system else {}),
    }]

    message = create_message(
        model=model,
        max_tokens=max_tokens,
        system=system_param,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user_content}],
    )

    for block in message.content:
        if block.type == "tool_use":
            return block.input

    raise ValueError(f"Expected a tool_use block from Claude, got: {message.content!r}")
