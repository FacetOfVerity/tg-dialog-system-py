"""/contact — show a reply keyboard (port ShowContactKeyboardCommand)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import (
    MessageContext,
    ReplyKeyboardBuilder,
    ReplyKeyboardMessageReply,
    ReplyKeyboardOptions,
    command_route,
)
from tg_dialog_system.models.replies import ReplyResult


@command_route("/contact")
async def show_contact_keyboard(
    ctx: MessageContext, localization: LocalizationService
) -> ReplyResult:
    lang = ctx.language_code
    keyboard = (
        ReplyKeyboardBuilder()
        .add_button(localization.get(MessageKey.PHONE_BUTTON, lang))
        .add_button(localization.get(MessageKey.EMAIL_BUTTON, lang))
        .new_row()
        .add_button(localization.get(MessageKey.CANCEL_BUTTON, lang))
    )
    options = ReplyKeyboardOptions(
        resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Choose..."
    )
    return Ok(ReplyKeyboardMessageReply(
        localization.get(MessageKey.CONTACT_MESSAGE, lang), keyboard, options
    ))
