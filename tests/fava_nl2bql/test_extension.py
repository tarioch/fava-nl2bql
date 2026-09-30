from unittest.mock import MagicMock, patch

from fava.core.query import QueryResultTable, QueryResultText
from fava.helpers import FavaAPIError

from fava_nl2bql.extension import FavaNl2Bql
from fava_nl2bql.translator import Translation

QUESTION = "How much did I spend on groceries per month this year?"
TRANSLATION = Translation(
    bql="SELECT year, month, sum(position) AS total\n"
    "WHERE year = year(today()) AND account ~ 'Groceries'\n"
    "GROUP BY year, month\n"
    "ORDER BY year, month",
    error=None,
)


def _make_extension(config: str | None = None) -> tuple[FavaNl2Bql, MagicMock]:
    ledger = MagicMock()
    return FavaNl2Bql(ledger, config), ledger


def test_extension_declares_a_report_with_a_js_module() -> None:
    assert FavaNl2Bql.report_title == "Ask"
    assert FavaNl2Bql.has_js_module is True


@patch("fava_nl2bql.extension.translate_to_bql")
def test_translate_uses_config_overrides(mock_translate: MagicMock) -> None:
    mock_translate.return_value = TRANSLATION
    extension, _ = _make_extension(
        "{'base_url': 'http://model-server.example/v1', 'model': 'custom-model',"
        " 'api_key': 'test-api-key', 'temperature': 0.7}"
    )

    assert extension.translate(QUESTION) == TRANSLATION

    mock_translate.assert_called_once_with(
        QUESTION,
        base_url="http://model-server.example/v1",
        model="custom-model",
        api_key="test-api-key",
        temperature=0.7,
    )


@patch("fava_nl2bql.extension.translate_to_bql")
def test_translate_uses_defaults_without_config(mock_translate: MagicMock) -> None:
    mock_translate.return_value = TRANSLATION
    extension, _ = _make_extension(None)

    assert extension.translate(QUESTION) == TRANSLATION

    mock_translate.assert_called_once_with(
        QUESTION,
        base_url="http://localhost:11434/v1",
        model="tarioch/qwen2.5-coder-bql",
        api_key=None,
        temperature=0.0,
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
