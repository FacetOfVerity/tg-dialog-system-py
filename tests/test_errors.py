from tg_dialog_system import errors
from tg_dialog_system.errors import Error, ErrorType


def test_validation_factory_sets_type():
    e = errors.validation("Order.Invalid", "No size selected")
    assert e == Error("Order.Invalid", "No size selected", ErrorType.VALIDATION)
    assert errors.is_validation(e)
    assert not errors.is_unexpected(e)


def test_telegram_api_carries_retry_after():
    e = errors.telegram_api("Telegram.Api.429", "Too many requests", retry_after=7)
    assert e.type is ErrorType.TELEGRAM_API
    assert e.metadata == {"retry_after": 7}
    assert errors.is_telegram_api(e)
