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

    bql = _extract_query(response.response or "").strip()
    if not bql:
        return Translation(bql=None, error="Ollama returned an empty response.")
    return Translation(bql=bql, error=None)


def _extract_query(text: str) -> str:
    """Pull the query out of the model's raw response.

    The model wraps the query in a ```` ``` ```` fence when asked for one, but more often
    emits the query bare and follows it with a lone closing fence and a one-line
    explanation (a training artifact, not something we asked for) - e.g.
    ``"SELECT ...\\n```\\n\\nSums the postings for ..."``. Both shapes are handled by
    stopping at the first bare fence line, and unwrapping one if the response opens
    with one too.
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
