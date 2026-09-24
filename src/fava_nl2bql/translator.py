"""Natural language to BQL translation via a local Ollama model."""

from __future__ import annotations

from dataclasses import dataclass

from ollama import Client, RequestError, ResponseError

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "tarioch/qwen2.5-coder-bql"
_TIMEOUT = 30.0  # seconds; a stalled server must not block the request forever


@dataclass(frozen=True)
class Translation:
    """Result of translating a question into BQL, or why it failed."""

    bql: str | None
    error: str | None


def translate_to_bql(
    question: str,
    *,
    host: str = DEFAULT_HOST,
    model: str = DEFAULT_MODEL,
) -> Translation:
    """Translate a natural-language question into a BQL query via Ollama.

    Args:
        question: The user's question, as typed into the extension's report page.
        host: Base URL of the Ollama server.
        model: Name of the Ollama model to use.

    Returns:
        The translation, or the reason it failed. Never executed without being
        shown to the user first.
    """
    question = question.strip()
    if not question:
        return Translation(bql=None, error=None)

    try:
        with Client(host=host, timeout=_TIMEOUT) as client:
            response = client.generate(model=model, prompt=question, stream=False)
    except (ConnectionError, RequestError, ResponseError) as error:
        return Translation(bql=None, error=f"Could not translate with Ollama: {error}")

    bql = _strip_markdown_fence(response.response or "").strip()
    if not bql:
        return Translation(bql=None, error="Ollama returned an empty response.")
    return Translation(bql=bql, error=None)


def _strip_markdown_fence(text: str) -> str:
    """Strip a leading/trailing ```...``` fence (with or without a language tag), if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[-1].strip() == "```":
        lines = lines[1:-1]
    else:
        lines = lines[1:]
    return "\n".join(lines).strip()
