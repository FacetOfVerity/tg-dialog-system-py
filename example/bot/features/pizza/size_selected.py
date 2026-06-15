"""Process size selection, show toppings (port SizeSelectedCallback)."""

from __future__ import annotations

from expression import Error as Err
from expression import Ok

from example.bot.features.pizza._toppings import build_toppings_menu
from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import CallbackContext, EditMenuMessageReply, Version, callback_route, errors
from tg_dialog_system.models.replies import ReplyResult

_VALID_SIZES = {"Small", "Medium", "Large"}


@callback_route(Version.V1, "pizza", "size_selected")
async def size_selected(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    if not ctx.payload or ctx.payload not in _VALID_SIZES:
        return Err([errors.validation("Size.Invalid", "Invalid pizza size selected")])

    order = order_state.get_or_create(ctx.user_id)
    order.size = ctx.payload
    order.toppings.clear()

    lang = ctx.language_code
    menu = build_toppings_menu(Version.V1, order, localization, lang)
    text = localization.get(MessageKey.SELECT_TOPPINGS, lang, ctx.payload.lower())
    return Ok(EditMenuMessageReply(ctx.message_id, text, menu))
