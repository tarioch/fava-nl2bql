import json
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import httpx2
import pytest
from openai import OpenAI

from fava_nl2bql.translator import Translation, translate_to_bql

Handler = Callable[[httpx2.Request], httpx2.Response]

# A question and the BQL the tuned model answered for it (see scripts/readme_captures.py).
QUESTION = "How much did I spend on groceries per month this year?"
BQL = """SELECT year, month, sum(position) AS total
WHERE year = year(today()) AND account ~ 'Groceries'
GROUP BY year, month
ORDER BY year, month"""


def _completion(content: str | None) -> dict[str, Any]:
    return {
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]
    }


def _answer(content: str | None) -> Handler:
    return lambda request: httpx2.Response(200, json=_completion(content))


def _raise(error: Exception) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error

    return handler


def _translate(
    handler: Handler, question: str = QUESTION, **kwargs: Any
) -> Translation:
    """Run translate_to_bql against an in-process transport instead of the network."""

    def client(**client_kwargs: Any) -> OpenAI:
        http_client = httpx2.Client(transport=httpx2.MockTransport(handler))
        return OpenAI(http_client=http_client, **client_kwargs)

    with patch("fava_nl2bql.translator.OpenAI", side_effect=client):
        return translate_to_bql(question, **kwargs)


def test_translate_success() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json=_completion(BQL))

    result = _translate(handler)

    assert result == Translation(bql=BQL, error=None)
    (request,) = requests
    assert request.method == "POST"
    assert str(request.url) == "http://localhost:11434/v1/chat/completions"
    assert json.loads(request.content) == {
        "model": "tarioch/qwen2.5-coder-bql",
        "messages": [{"role": "user", "content": QUESTION}],
        "temperature": 0,
    }


def test_translate_uses_base_url_model_and_api_key() -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json=_completion(BQL))

    _translate(
        handler,
        base_url="http://model-server.example/v1/",
        model="custom-model",
        api_key="test-api-key",
    )

    (request,) = requests
    assert str(request.url) == "http://model-server.example/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-api-key"
    assert json.loads(request.content)["model"] == "custom-model"


def test_translate_takes_api_key_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json=_completion(BQL))

    _translate(handler)

    assert requests[0].headers["Authorization"] == "Bearer env-api-key"


def test_translate_works_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = _translate(_answer(BQL))

    assert result == Translation(bql=BQL, error=None)


def test_translate_strips_markdown_code_fence() -> None:
    result = _translate(
        _answer(
            f"```sql\n{BQL}\n```\n\n"
            "Sums the postings for Expenses:Food:Groceries this year, per month."
        )
    )

    assert result == Translation(bql=BQL, error=None)


def test_translate_drops_trailing_fence_and_explanation() -> None:
    # Also observed from the model: no opening fence, just the query followed by
    # a lone closing fence and a one-line explanation.
    result = _translate(
        _answer(
            f"{BQL}\n```\n\n"
            "Sums the postings for Expenses:Food:Groceries this year, per month."
        )
    )

    assert result == Translation(bql=BQL, error=None)


def test_translate_timeout() -> None:
    result = _translate(_raise(httpx2.ReadTimeout("timed out")))

    assert result == Translation(
        bql=None, error="The model server did not respond within 30 seconds."
    )


def test_translate_connection_failure() -> None:
    result = _translate(
        _raise(httpx2.ConnectError("[Errno 111] Connection refused")),
        base_url="http://localhost:11434/v1",
    )

    assert result == Translation(
        bql=None,
        error="Could not reach the model server at http://localhost:11434/v1: "
        "[Errno 111] Connection refused",
    )


def test_translate_connection_dropped() -> None:
    result = _translate(
        _raise(httpx2.RemoteProtocolError("Server disconnected without response."))
    )

    assert result.bql is None
    assert result.error is not None
    assert "Server disconnected without response." in result.error


def test_translate_error_status() -> None:
    # What Ollama answers for a model that has not been pulled.
    body = {
        "error": {
            "message": 'model "custom-model" not found, try pulling it first',
            "type": "api_error",
            "param": None,
            "code": None,
        }
    }

    result = _translate(
        lambda request: httpx2.Response(404, json=body), model="custom-model"
    )

    assert result.bql is None
    assert result.error is not None
    assert result.error.startswith("The model server returned an error: ")
    assert 'model "custom-model" not found, try pulling it first' in result.error


def test_translate_empty_question_short_circuits() -> None:
    with patch("fava_nl2bql.translator.OpenAI") as mock_client_cls:
        result = translate_to_bql("   ")

    assert result == Translation(bql=None, error=None)
    mock_client_cls.assert_not_called()


@pytest.mark.parametrize("content", ["", None])
def test_translate_empty_model_response(content: str | None) -> None:
    result = _translate(_answer(content))

    assert result == Translation(
        bql=None, error="The model returned an empty response."
    )
