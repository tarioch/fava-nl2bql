from unittest.mock import MagicMock, patch

from ollama import GenerateResponse, ResponseError

from fava_nl2bql.translator import Translation, translate_to_bql


def _mock_client(mock_client_cls: MagicMock) -> MagicMock:
    return mock_client_cls.return_value.__enter__.return_value


@patch("fava_nl2bql.translator.Client")
def test_translate_success(mock_client_cls: MagicMock) -> None:
    _mock_client(mock_client_cls).generate.return_value = GenerateResponse(
        response="SELECT account FROM entries"
    )

    result = translate_to_bql("how much did I spend on groceries?")

    assert result == Translation(bql="SELECT account FROM entries", error=None)
    call = _mock_client(mock_client_cls).generate.call_args
    assert call.kwargs["prompt"] == "how much did I spend on groceries?"
    assert call.kwargs["model"] == "tarioch/qwen2.5-coder-bql"


@patch("fava_nl2bql.translator.Client")
def test_translate_strips_markdown_code_fence(mock_client_cls: MagicMock) -> None:
    _mock_client(mock_client_cls).generate.return_value = GenerateResponse(
        response="```sql\nSELECT account FROM entries\n```"
    )

    result = translate_to_bql("question")

    assert result.bql == "SELECT account FROM entries"
    assert result.error is None


@patch("fava_nl2bql.translator.Client")
def test_translate_connection_failure(mock_client_cls: MagicMock) -> None:
    _mock_client(mock_client_cls).generate.side_effect = ConnectionError(
        "Failed to connect to Ollama."
    )

    result = translate_to_bql("question", host="http://localhost:11434")

    assert result.bql is None
    assert (
        result.error == "Could not translate with Ollama: Failed to connect to Ollama."
    )


@patch("fava_nl2bql.translator.Client")
def test_translate_ollama_error_response(mock_client_cls: MagicMock) -> None:
    _mock_client(mock_client_cls).generate.side_effect = ResponseError(
        "model not found", 404
    )

    result = translate_to_bql("question")

    assert result.bql is None
    assert result.error is not None


@patch("fava_nl2bql.translator.Client")
def test_translate_empty_question_short_circuits(mock_client_cls: MagicMock) -> None:
    result = translate_to_bql("   ")

    assert result == Translation(bql=None, error=None)
    mock_client_cls.assert_not_called()


@patch("fava_nl2bql.translator.Client")
def test_translate_empty_model_response(mock_client_cls: MagicMock) -> None:
    _mock_client(mock_client_cls).generate.return_value = GenerateResponse(response="")

    result = translate_to_bql("question")

    assert result.bql is None
    assert result.error is not None
