import json
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from fava_nl2bql.translator import Translation, translate_to_bql

Handler = Callable[[httpx.Request], httpx.Response]


def _completion(content: str | None) -> dict[str, Any]:
    return {
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]
    }


def _answer(content: str | None) -> Handler:
    return lambda request: httpx.Response(200, json=_completion(content))


def _raise(error: Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return handler


def _translate(
    handler: Handler, question: str = "question", **kwargs: Any
) -> Translation:
    """Run translate_to_bql against an in-process transport instead of the network."""

    def client(**client_kwargs: Any) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(handler), **client_kwargs)

    with patch("fava_nl2bql.translator.Client", side_effect=client):
        return translate_to_bql(question, **kwargs)


def test_translate_success() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_completion("SELECT account FROM entries"))

    result = _translate(handler, "how much did I spend on groceries?")

    assert result == Translation(bql="SELECT account FROM entries", error=None)
    (request,) = requests
    assert request.method == "POST"
    assert str(request.url) == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in request.headers
    assert json.loads(request.content) == {
        "model": "tarioch/qwen2.5-coder-bql",
        "messages": [{"role": "user", "content": "how much did I spend on groceries?"}],
        "stream": False,
    }


def test_translate_uses_base_url_model_and_api_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_completion("SELECT 1"))

    _translate(
        handler,
        base_url="http://example:4000/v1/",
        model="bql",
        api_key="sk-test",
    )

    (request,) = requests
    assert str(request.url) == "http://example:4000/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer sk-test"
    assert json.loads(request.content)["model"] == "bql"


def test_translate_takes_api_key_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FAVA_NL2BQL_API_KEY", "sk-env")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_completion("SELECT 1"))

    _translate(handler)

    assert requests[0].headers["Authorization"] == "Bearer sk-env"


def test_translate_strips_markdown_code_fence() -> None:
    result = _translate(_answer("```sql\nSELECT account FROM entries\n```"))

    assert result == Translation(bql="SELECT account FROM entries", error=None)


def test_translate_drops_trailing_fence_and_explanation() -> None:
    # The model's actual (observed) behavior: no opening fence, just the query
    # followed by a lone closing fence and a one-line explanation.
    result = _translate(
        _answer(
            "SELECT sum(position) WHERE account ~ 'Groceries'\n```\n\n"
            "Sums the postings for Expenses:Groceries."
        )
    )

    assert result == Translation(
        bql="SELECT sum(position) WHERE account ~ 'Groceries'", error=None
    )


def test_translate_timeout() -> None:
    result = _translate(_raise(httpx.ReadTimeout("timed out")))

    assert result == Translation(
        bql=None, error="The model server did not respond within 30 seconds."
    )


def test_translate_connection_failure() -> None:
    result = _translate(
        _raise(httpx.ConnectError("[Errno 111] Connection refused")),
        base_url="http://localhost:11434/v1",
    )

    assert result == Translation(
        bql=None,
        error="Could not reach the model server at http://localhost:11434/v1: "
        "[Errno 111] Connection refused",
    )


def test_translate_connection_dropped() -> None:
    result = _translate(
        _raise(httpx.RemoteProtocolError("Server disconnected without response."))
    )

    assert result.bql is None
    assert result.error is not None
    assert "Server disconnected without response." in result.error


def test_translate_error_status() -> None:
    result = _translate(
        lambda request: httpx.Response(404, json={"error": "model not found"})
    )

    assert result == Translation(
        bql=None,
        error='The model server answered with HTTP 404: {"error":"model not found"}',
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"response": "SELECT 1"}),
        httpx.Response(200, json=_completion(None) | {"choices": [None]}),
    ],
)
def test_translate_unexpected_response(response: httpx.Response) -> None:
    result = _translate(lambda request: response)

    assert result == Translation(
        bql=None, error="The model server returned an unexpected response."
    )


def test_translate_empty_question_short_circuits() -> None:
    with patch("fava_nl2bql.translator.Client") as mock_client_cls:
        result = translate_to_bql("   ")

    assert result == Translation(bql=None, error=None)
    mock_client_cls.assert_not_called()


@pytest.mark.parametrize("content", ["", None])
def test_translate_empty_model_response(content: str | None) -> None:
    result = _translate(_answer(content))

    assert result == Translation(
        bql=None, error="The model returned an empty response."
    )
