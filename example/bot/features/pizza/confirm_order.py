"""Order confirmation with price (port ConfirmOrderCallback)."""

from __future__ import annotations

from expression import Error as Err
from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import (
    CallbackContext,
    CallbackData,
    EditMenuMessageReply,
    MenuGrid,
    Version,
    callback_route,
    errors,
)
from tg_dialog_system.models.replies import ReplyResult

_BASE_PRICE = {"Small": 8.99, "Medium": 12.99, "Large": 16.99}


@callback_route(Version.V1, "pizza", "confirm")
async def confirm_order(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    order = order_state.get_or_create(ctx.user_id)
    if order.size is None:
        return Err([errors.validation("Order.Invalid", "No size selected")])

    lang = ctx.language_code
    total = _BASE_PRICE[order.size] + len(order.toppings) * 1.5
    toppings_text = (
        ", ".join(order.toppings) if order.toppings else localization.get(MessageKey.NO_TOPPINGS, lang)  # noqa: E501
    )
    text = localization.get(
        MessageKey.ORDER_CONFIRMATION, lang, order.size, toppings_text, f"{total:.2f}"
    )

    def build(b: MenuGrid.Builder) -> MenuGrid.Builder:
        return (
            b.button(localization.get(MessageKey.CONFIRM_BUTTON, lang),
                     CallbackData(Version.V1, "pizza", "place_order", ""))
            .new_row()
            .button(localization.get(MessageKey.BACK_BUTTON, lang),
                    CallbackData(Version.V1, "pizza", "size_selected", order.size))
        )

    return Ok(EditMenuMessageReply(ctx.message_id, text, MenuGrid.build(build)))
