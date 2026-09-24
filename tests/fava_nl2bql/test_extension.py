from unittest.mock import MagicMock, patch

from fava.core.query import QueryResultTable, QueryResultText
from fava.helpers import FavaAPIError

from fava_nl2bql.extension import FavaNl2Bql
from fava_nl2bql.translator import Translation


def _make_extension(config: str | None = None) -> tuple[FavaNl2Bql, MagicMock]:
    ledger = MagicMock()
    return FavaNl2Bql(ledger, config), ledger


def test_extension_declares_a_report_with_a_js_module() -> None:
    assert FavaNl2Bql.report_title == "Ask"
    assert FavaNl2Bql.has_js_module is True


@patch("fava_nl2bql.extension.translate_to_bql")
def test_translate_uses_config_overrides(mock_translate: MagicMock) -> None:
    mock_translate.return_value = Translation(bql="SELECT 1", error=None)
    extension, _ = _make_extension(
        "{'ollama_host': 'http://example:1234', 'model': 'custom-model'}"
    )

    extension.translate("question")

    mock_translate.assert_called_once_with(
        "question", host="http://example:1234", model="custom-model"
    )


@patch("fava_nl2bql.extension.translate_to_bql")
def test_translate_uses_defaults_without_config(mock_translate: MagicMock) -> None:
    mock_translate.return_value = Translation(bql="SELECT 1", error=None)
    extension, _ = _make_extension(None)

    extension.translate("question")

    mock_translate.assert_called_once_with(
        "question", host="http://localhost:11434", model="tarioch/qwen2.5-coder-bql"
    )


def test_run_query_returns_table_result() -> None:
    extension, ledger = _make_extension(None)
    expected = QueryResultTable(types=[], rows=[])
    ledger.query_shell.execute_query_serialised.return_value = expected

    # `fava.context.g` is a Werkzeug LocalProxy: touching it outside a real Flask
    # request raises RuntimeError, and even `unittest.mock.patch`'s own internal
    # async-detection does that unless an explicit replacement is given via `new=`.
    with patch("fava_nl2bql.extension.g", new=MagicMock()):
        result = extension.run_query("SELECT account")

    assert result is expected


def test_run_query_wraps_fava_api_error_as_text_result() -> None:
    extension, ledger = _make_extension(None)
    ledger.query_shell.execute_query_serialised.side_effect = FavaAPIError(
        "syntax error near 'SELCT'"
    )

    with patch("fava_nl2bql.extension.g", new=MagicMock()):
        result = extension.run_query("SELCT nonsense")

    assert isinstance(result, QueryResultText)
    assert result.contents == "syntax error near 'SELCT'"
