"""The FavaNl2Bql extension: ask a question, see the BQL, see the result."""

from __future__ import annotations

from fava.context import g
from fava.core.query import QueryResultTable, QueryResultText
from fava.ext import FavaExtensionBase

from fava_nl2bql.translator import translate_to_bql


class FavaNl2Bql(FavaExtensionBase):
    """Translate a natural-language question into BQL and run it."""

    report_title = "Ask"

    has_js_module = True

    def translate(self, question: str) -> str:
        """Translate a natural-language question into a BQL query."""
        return translate_to_bql(question)

    def run_query(self, bql: str) -> QueryResultTable | QueryResultText:
        """Run a BQL query against the currently filtered ledger."""
        return self.ledger.query_shell.execute_query_serialised(
            g.filtered.entries_with_all_prices, bql
        )
