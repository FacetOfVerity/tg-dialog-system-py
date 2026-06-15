from expression import Ok

from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.version import Version


def test_route_key_and_encode():
    cb = CallbackData(Version.V1, "pizza", "size_selected", "Large")
    assert cb.route_key == "V1:pizza:size_selected"
    assert cb.encode() == "V1:pizza:size_selected:Large"


def test_encode_with_none_payload_has_trailing_separator():
    cb = CallbackData(Version.V1, "pizza", "select_size")
    assert cb.encode() == "V1:pizza:select_size:"


def test_parse_valid_with_payload():
    result = CallbackData.parse("V1:pizza:size_selected:Large")
    assert result == Ok(CallbackData(Version.V1, "pizza", "size_selected", "Large"))


def test_parse_without_payload_yields_none():
    result = CallbackData.parse("V2:pizza:confirm")
    assert result == Ok(CallbackData(Version.V2, "pizza", "confirm", None))


def test_parse_empty_is_error():
    assert CallbackData.parse("").is_error()
    assert CallbackData.parse(None).is_error()


def test_parse_too_few_parts_is_error():
    assert CallbackData.parse("V1:pizza").is_error()


def test_parse_bad_version_is_error():
    assert CallbackData.parse("V9:pizza:confirm").is_error()


def test_parse_payload_with_embedded_separator():
    """Payload containing ':' must not be truncated."""
    result = CallbackData.parse("V1:pizza:size:a:b")
    assert result.is_ok()
    assert result.ok.payload == "a:b"
