from fava_nl2bql.extension import FavaNl2Bql


def test_extension_declares_a_report_with_a_js_module() -> None:
    assert FavaNl2Bql.report_title == "Ask"
    assert FavaNl2Bql.has_js_module is True
