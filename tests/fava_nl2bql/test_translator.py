from fava_nl2bql.translator import translate_to_bql


def test_translate_returns_a_query_for_a_question() -> None:
    bql = translate_to_bql("how much did I spend on groceries last month?")

    assert "SELECT" in bql


def test_translate_returns_a_query_for_an_empty_question() -> None:
    bql = translate_to_bql("")

    assert "SELECT" in bql
