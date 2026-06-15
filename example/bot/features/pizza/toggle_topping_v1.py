"""Toggle topping, no limit (port v1 ToggleToppingCallback)."""

from __future__ import annotations

from expression import Error as Err
from expression import Ok

from example.bot.features.pizza._toppings import build_toppings_menu
from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import CallbackContext, EditMenuMessageReply, Version, callback_route, errors
from tg_dialog_system.models.replies import ReplyResult


@callback_route(Version.V1, "pizza", "toggle_topping")
async def toggle_topping_v1(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    if not ctx.payload:
        return Err([errors.validation("Topping.Invalid", "Invalid topping")])

    order = order_state.get_or_create(ctx.user_id)
    if ctx.payload in order.toppings:
        order.toppings.remove(ctx.payload)
    else:
        order.toppings.append(ctx.payload)

    lang = ctx.language_code
    size_text = order.size.lower() if order.size else "unknown"
    text = localization.get(MessageKey.SELECT_TOPPINGS, lang, size_text)
    menu = build_toppings_menu(Version.V1, order, localization, lang)
    return Ok(EditMenuMessageReply(ctx.message_id, text, menu))
