"""Routes free text and reply-keyboard button presses (port ArbitraryTextMessageHandler)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system.models.context import MessageContext
from tg_dialog_system.models.replies import (
    ReplyKeyboardRemoveMessageReply,
    ReplyResult,
    TextMessageReply,
)

_PHONE_KEYS = {"en", "ru"}


class ArbitraryTextMessageHandler:
    def __init__(self, localization: LocalizationService) -> None:
        self._loc = localization
        self._phone_texts = {self._loc.get(MessageKey.PHONE_BUTTON, lang) for lang in _PHONE_KEYS}
        self._email_texts = {self._loc.get(MessageKey.EMAIL_BUTTON, lang) for lang in _PHONE_KEYS}
        self._cancel_texts = {self._loc.get(MessageKey.CANCEL_BUTTON, lang) for lang in _PHONE_KEYS}

    async def handle(self, ctx: MessageContext, payload: str) -> ReplyResult:
        lang = ctx.language_code
        if payload in self._phone_texts:
            return Ok(ReplyKeyboardRemoveMessageReply(
                self._loc.get(MessageKey.PHONE_CONTACT_RESPONSE, lang)
            ))
        if payload in self._email_texts:
            return Ok(ReplyKeyboardRemoveMessageReply(
                self._loc.get(MessageKey.EMAIL_CONTACT_RESPONSE, lang)
            ))
        if payload in self._cancel_texts:
            return Ok(ReplyKeyboardRemoveMessageReply(
                self._loc.get(MessageKey.KEYBOARD_REMOVED, lang)
            ))
        fallback = (
            "Извините, я не понимаю это сообщение. Используйте команды меню или /start"
            if lang == "ru"
            else "Sorry, I don't understand. Please use the menu commands or /start"
        )
        return Ok(TextMessageReply(fallback))
