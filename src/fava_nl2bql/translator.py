"""Natural language to BQL translation via an OpenAI-compatible chat completions API.

Ollama serves this API under ``/v1``, as do many other model servers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    OpenAIError,
)

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "tarioch/qwen2.5-coder-bql"
_TIMEOUT = 30.0  # seconds; a stalled server must not block the request forever
# Ollama ignores the key, but the client refuses to start without one.
_NO_API_KEY = "unused"


@dataclass(frozen=True)
class Translation:
    """Result of translating a question into BQL, or why it failed."""

    bql: str | None
    error: str | None


def translate_to_bql(
    question: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> Translation:
    """Translate a natural-language question into a BQL query.

    Args:
        question: The user's question, as typed into the extension's report page.
        base_url: Base URL of the OpenAI-compatible API, e.g. Ollama's
            ``http://localhost:11434/v1``.
        model: Name of the model to use, as the server knows it.
        api_key: API key for the server. Defaults to the ``OPENAI_API_KEY``
            environment variable, and to none at all if that is not set.

    Returns:
        The translation, or the reason it failed. Never executed without being
        shown to the user first.
    """
    question = question.strip()
    if not question:
        return Translation(bql=None, error=None)

    try:
        with OpenAI(
            base_url=base_url,
            api_key=api_key or os.environ.get("OPENAI_API_KEY") or _NO_API_KEY,
            timeout=_TIMEOUT,
            max_retries=0,
        ) as client:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": question}],
            )
        content = completion.choices[0].message.content
    except APITimeoutError:
        return Translation(
            bql=None,
            error=f"The model server did not respond within {_TIMEOUT:g} seconds.",
        )
    except APIConnectionError as error:
        return Translation(
            bql=None,
            error=f"Could not reach the model server at {base_url}: "
            f"{error.__cause__ or error}",
        )
    except APIStatusError as error:
        return Translation(
            bql=None,
            error=f"The model server returned an error: {error.message}",
        )
    except OpenAIError:
        return Translation(
            bql=None, error="The model server returned an unexpected response."
        )

    bql = _extract_query(content or "").strip()
    if not bql:
        return Translation(bql=None, error="The model returned an empty response.")
    return Translation(bql=bql, error=None)


def _extract_query(text: str) -> str:
    """Pull the query out of the model's raw response.

    The model wraps the query in a ```` ``` ```` fence when asked for one, but more often
    emits the query bare and follows it with a lone closing fence and a one-line
    explanation - e.g. ``"SELECT ...\\n```\\n\\nSums the postings for ..."``. Both shapes
    are handled by stopping at the first bare fence line, and unwrapping one if the
    response opens with one too.
    """
    stripped = text.strip()
    lines = stripped.splitlines()

    if stripped.startswith("```"):
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "```"), None)
        return "\n".join(lines[1:end]).strip()

    fence = next((i for i, line in enumerate(lines) if line.strip() == "```"), None)
    if fence is not None:
        return "\n".join(lines[:fence]).strip()

    return stripped
