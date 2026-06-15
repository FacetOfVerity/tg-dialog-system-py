"""Selects the sender method based on the reply type (port ReplyMessageSender)."""

from __future__ import annotations

from tg_dialog_system.models.context import ChatId
from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuMessageReply,
    ReplyKeyboardMessageReply,
    ReplyKeyboardRemoveMessageReply,
    ReplyMessage,
    TextMessageReply,
)
from tg_dialog_system.sending.sender import MessageSender, SendResult


class ReplyMessageSender:
    def __init__(self, sender: MessageSender) -> None:
        self._sender = sender

    async def send(self, chat_id: ChatId, reply: ReplyMessage) -> SendResult:
        match reply:
            case EditTextMessageReply():
                return await self._sender.edit_message_text(
                    chat_id, reply.message_id, reply.value
                )
            case EditMenuMessageReply():
                return await self._sender.edit_message_menu(
                    chat_id, reply.message_id, reply.text, reply.buttons
                )
            case TextMessageReply():
                return await self._sender.send_message(chat_id, reply.value)
            case MenuMessageReply():
                return await self._sender.send_menu(chat_id, reply.text, reply.buttons)
            case ReplyKeyboardMessageReply():
                return await self._sender.send_reply_keyboard(
                    chat_id, reply.text, reply.keyboard, reply.options
                )
            case ReplyKeyboardRemoveMessageReply():
                return await self._sender.remove_reply_keyboard(
                    chat_id, reply.text, reply.selective
                )
            case _:
                raise TypeError(f"Unsupported reply type: {type(reply)!r}")
