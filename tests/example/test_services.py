from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState


def test_localization_falls_back_to_english():
    loc = LocalizationService()
    assert loc.get(MessageKey.ORDER_BUTTON, "fr") == loc.get(MessageKey.ORDER_BUTTON, "en")


def test_localization_formats_args():
    loc = LocalizationService()
    text = loc.get(MessageKey.SELECT_TOPPINGS, "en", "large")
    assert "large" in text


def test_order_state_roundtrip():
    state = OrderState()
    order = state.get_or_create(7)
    order.size = "Large"
    order.toppings.append("Cheese")
    assert state.get_or_create(7).toppings == ["Cheese"]
    state.clear(7)
    assert state.get_or_create(7).size is None
