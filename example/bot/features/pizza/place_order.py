"""Place the order and reset state (port PlaceOrderCallback)."""

from __future__ import annotations

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
)
from tg_dialog_system.models.replies import ReplyResult


@callback_route(Version.V1, "pizza", "place_order")
async def place_order(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    order_state.clear(ctx.user_id)
    lang = ctx.language_code
    menu = MenuGrid.build(
        lambda b: b.button(
            localization.get(MessageKey.NEW_ORDER_BUTTON, lang),
            CallbackData(Version.V1, "pizza", "select_size", ""),
        )
    )
    return Ok(EditMenuMessageReply(
        ctx.message_id, localization.get(MessageKey.ORDER_SUCCESS, lang), menu
    ))
