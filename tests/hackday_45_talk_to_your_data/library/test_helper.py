from hackday_45_talk_to_your_data.library.helper import float_value, int_value, json_text, text


def test_text_returns_default_for_none() -> None:
    assert text(None, "fallback") == "fallback"
    assert text(42) == "42"


def test_json_text_passes_through_strings_and_encodes_other_values() -> None:
    assert json_text("already json") == "already json"
    assert json_text(None, "[]") == "[]"
    assert json_text({"b": 1, "a": 2}) == '{"a": 2, "b": 1}'


def test_int_value_falls_back_on_invalid_input() -> None:
    assert int_value("12") == 12
    assert int_value("not a number", default=-1) == -1


def test_float_value_falls_back_on_invalid_input() -> None:
    assert float_value("1.5") == 1.5
    assert float_value(None, default=2.0) == 2.0
