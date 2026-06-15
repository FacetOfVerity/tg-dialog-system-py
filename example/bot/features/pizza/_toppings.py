"""Shared toppings-menu builder for the pizza feature."""

from __future__ import annotations

from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import PizzaOrder
from tg_dialog_system import CallbackData, MenuGrid, Version

_TOPPINGS = [
    ("Cheese", MessageKey.TOPPING_CHEESE),
    ("Pepperoni", MessageKey.TOPPING_PEPPERONI),
    ("Mushrooms", MessageKey.TOPPING_MUSHROOMS),
    ("Olives", MessageKey.TOPPING_OLIVES),
]


def build_toppings_menu(
    version: Version, order: PizzaOrder, localization: LocalizationService, lang: str | None
) -> MenuGrid:
    # The active flow passes Version.V1 (no topping limit).  The Version.V2
    # toggle_topping handler (max-3 toppings) is registered in the same
    # registry to demonstrate coexistence of multiple callback API versions:
    # it is reachable by emitting a "V2:pizza:toggle_topping" callback.
    def label(value: str, key: MessageKey) -> str:
        text = localization.get(key, lang)
        return f"✅ {text}" if value in order.toppings else text

    def build(b: MenuGrid.Builder) -> MenuGrid.Builder:
        b.button(label(*_TOPPINGS[0]), CallbackData(version, "pizza", "toggle_topping", "Cheese"))
        b.button(label(*_TOPPINGS[1]), CallbackData(version, "pizza", "toggle_topping", "Pepperoni"))  # noqa: E501
        b.new_row()
        b.button(label(*_TOPPINGS[2]), CallbackData(version, "pizza", "toggle_topping", "Mushrooms"))  # noqa: E501
        b.button(label(*_TOPPINGS[3]), CallbackData(version, "pizza", "toggle_topping", "Olives"))
        b.new_row()
        b.button(localization.get(MessageKey.CONFIRM_BUTTON, lang),
                 CallbackData(Version.V1, "pizza", "confirm", ""))
        b.new_row()
        b.button(localization.get(MessageKey.BACK_BUTTON, lang),
                 CallbackData(Version.V1, "pizza", "select_size", ""))
        return b

    return MenuGrid.build(build)
