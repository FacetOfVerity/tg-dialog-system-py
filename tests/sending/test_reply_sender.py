from expression import Ok

from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuMessageReply,
    ReplyKeyboardBuilder,
    ReplyKeyboardMessageReply,
    ReplyKeyboardRemoveMessageReply,
    TextMessageReply,
)
from tg_dialog_system.models.replies.menu import MenuGrid
from tg_dialog_system.models.version import Version
from tg_dialog_system.sending.reply_sender import ReplyMessageSender


class RecordingSender:
    def __init__(self):
        self.method = None

    async def send_message(self, chat_id, message):
        self.method = "send_message"
        return Ok(1)

    async def send_menu(self, chat_id, text, buttons):
        self.method = "send_menu"
        return Ok(1)

    async def send_reply_keyboard(self, chat_id, text, keyboard, options=None):
        self.method = "send_reply_keyboard"
        return Ok(1)

    async def remove_reply_keyboard(self, chat_id, text="", selective=False):
        self.method = "remove_reply_keyboard"
        return Ok(1)

    async def edit_message_text(self, chat_id, message_id, text):
        self.method = "edit_message_text"
        return Ok(1)

    async def edit_message_menu(self, chat_id, message_id, text, buttons):
        self.method = "edit_message_menu"
        return Ok(1)


def _grid():
    return MenuGrid.build(lambda b: b.button("A", CallbackData(Version.V1, "m", "a")))


async def test_dispatch_each_reply_type():
    cases = [
        (TextMessageReply("hi"), "send_message"),
        (MenuMessageReply("t", _grid()), "send_menu"),
        (EditTextMessageReply(5, "e"), "edit_message_text"),
        (EditMenuMessageReply(5, "t", _grid()), "edit_message_menu"),
        (ReplyKeyboardMessageReply("t", ReplyKeyboardBuilder()), "send_reply_keyboard"),
        (ReplyKeyboardRemoveMessageReply("bye"), "remove_reply_keyboard"),
    ]
    for reply, expected in cases:
        sender = RecordingSender()
        await ReplyMessageSender(sender).send(100, reply)
        assert sender.method == expected
