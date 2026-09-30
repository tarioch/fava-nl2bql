"""The FavaNl2Bql extension: ask a question, see the BQL, see the result."""

from __future__ import annotations

from fava.context import g
from fava.core.query import QueryResultTable, QueryResultText
from fava.ext import FavaExtensionBase
from fava.helpers import FavaAPIError

from fava_nl2bql.translator import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    Translation,
    translate_to_bql,
)


class FavaNl2Bql(FavaExtensionBase):
    """Translate a natural-language question into BQL and run it."""

    report_title = "Ask"

    has_js_module = True

    def translate(self, question: str) -> Translation:
        """Translate a natural-language question into a BQL query."""
        config = self.config if isinstance(self.config, dict) else {}
        return translate_to_bql(
            question,
            base_url=config.get("base_url", DEFAULT_BASE_URL),
            model=config.get("model", DEFAULT_MODEL),
            api_key=config.get("api_key"),
            temperature=float(config.get("temperature", DEFAULT_TEMPERATURE)),
        )

    def run_query(self, bql: str) -> QueryResultTable | QueryResultText:
        """Run a BQL query against the currently filtered ledger."""
        try:
            return self.ledger.query_shell.execute_query_serialised(
                g.filtered.entries_with_all_prices, bql
            )
        except FavaAPIError as error:
            return QueryResultText(contents=str(error))
