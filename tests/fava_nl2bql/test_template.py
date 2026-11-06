from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from fava.application import create_app
from flask.testing import FlaskClient

from fava_nl2bql.translator import Translation

BQL = "SELECT account, sum(position)\nWHERE account ~ 'Groceries'\nGROUP BY account"

LEDGER = """\
option "title" "Example"

2026-01-01 open Assets:Bank:Checking EUR
2026-01-01 open Expenses:Food:Groceries EUR

2026-01-05 * "Corner Shop" "Weekly groceries"
  Expenses:Food:Groceries  42.00 EUR
  Assets:Bank:Checking

2026-01-01 custom "fava-extension" "fava_nl2bql.extension"
"""


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: dict[str, str] = {}
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")

    def handle_data(self, data: str) -> None:
        if self._href is not None and data.strip():
            self.links[data.strip()] = self._href
            self._href = None


@pytest.fixture
def client(tmp_path: Path) -> FlaskClient:
    ledger = tmp_path / "example.beancount"
    ledger.write_text(LEDGER, encoding="utf-8")
    app = create_app([str(ledger)], load=True)
    app.testing = True
    return app.test_client()


@patch("fava_nl2bql.extension.translate_to_bql")
def test_page_links_generated_query_to_query_editor(
    mock_translate: MagicMock, client: FlaskClient
) -> None:
    mock_translate.return_value = Translation(bql=BQL, error=None)

    response = client.get("/example/extension/FavaNl2Bql/?question=groceries")

    assert response.status_code == 200
    parser = _Links()
    parser.feed(response.get_data(as_text=True))
    url = urlsplit(parser.links["Edit in query editor"])
    assert url.path == "/example/query/"
    assert parse_qs(url.query) == {"query_string": [BQL]}


@patch("fava_nl2bql.extension.translate_to_bql")
def test_page_has_no_editor_link_without_a_query(
    mock_translate: MagicMock, client: FlaskClient
) -> None:
    mock_translate.return_value = Translation(bql=None, error="model unreachable")

    response = client.get("/example/extension/FavaNl2Bql/?question=groceries")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "model unreachable" in body
    assert "Edit in query editor" not in body
