"""Pizza size selection menu (port SelectSizeCallback)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import (
    CallbackContext,
    CallbackData,
    EditMenuMessageReply,
    MenuGrid,
    Version,
    callback_route,
)
from tg_dialog_system.models.replies import ReplyResult


@callback_route(Version.V1, "pizza", "select_size")
async def select_size(ctx: CallbackContext, localization: LocalizationService) -> ReplyResult:
    lang = ctx.language_code

    def build(b: MenuGrid.Builder) -> MenuGrid.Builder:
        return (
            b.button(localization.get(MessageKey.SIZE_SMALL, lang),
                     CallbackData(Version.V1, "pizza", "size_selected", "Small"))
            .button(localization.get(MessageKey.SIZE_MEDIUM, lang),
                    CallbackData(Version.V1, "pizza", "size_selected", "Medium"))
            .new_row()
            .button(localization.get(MessageKey.SIZE_LARGE, lang),
                    CallbackData(Version.V1, "pizza", "size_selected", "Large"))
        )

    return Ok(EditMenuMessageReply(
        ctx.message_id, localization.get(MessageKey.SELECT_SIZE, lang), MenuGrid.build(build)
    ))
