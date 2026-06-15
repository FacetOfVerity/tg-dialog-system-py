"""/start — entry point (port HandleStartCommand)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import (
    CallbackData,
    MenuGrid,
    MenuMessageReply,
    MessageContext,
    Version,
    command_route,
)
from tg_dialog_system.models.replies import ReplyResult


@command_route("/start")
async def handle_start(ctx: MessageContext, localization: LocalizationService) -> ReplyResult:
    lang = ctx.language_code
    menu = MenuGrid.build(
        lambda b: b.button(
            localization.get(MessageKey.ORDER_BUTTON, lang),
            CallbackData(Version.V1, "pizza", "select_size", ""),
        )
    )
    return Ok(MenuMessageReply(localization.get(MessageKey.WELCOME, lang), menu))
