"""/hide — remove the reply keyboard (port HideContactKeyboardCommand)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import MessageContext, ReplyKeyboardRemoveMessageReply, command_route
from tg_dialog_system.models.replies import ReplyResult


@command_route("/hide")
async def hide_contact_keyboard(
    ctx: MessageContext, localization: LocalizationService
) -> ReplyResult:
    return Ok(ReplyKeyboardRemoveMessageReply(
        localization.get(MessageKey.KEYBOARD_REMOVED, ctx.language_code)
    ))
