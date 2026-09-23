"""Natural language to BQL translation.

This is currently a placeholder that returns a fixed query regardless of the
question, so the extension is usable end to end while the real translator is
wired up. Replace :func:`translate_to_bql` with a call to the tuned model.
"""

from __future__ import annotations

_PLACEHOLDER_BQL = "SELECT account, sum(position) GROUP BY account ORDER BY account"


def translate_to_bql(question: str) -> str:
    """Translate a natural-language question into a BQL query.

    Args:
        question: The user's question, as typed into the extension's report page.

    Returns:
        A BQL query string. Never executed without being shown to the user first.
    """
    if not question.strip():
        return _PLACEHOLDER_BQL
    # TODO: call the tuned NL -> BQL model here instead of the placeholder.
    return _PLACEHOLDER_BQL
