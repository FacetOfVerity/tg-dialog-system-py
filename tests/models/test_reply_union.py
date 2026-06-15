from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuMessageReply,
    ReplyKeyboardMessageReply,
    ReplyKeyboardRemoveMessageReply,
    ReplyMessage,
    TextMessageReply,
)


def test_text_reply_is_member_of_union():
    reply: ReplyMessage = TextMessageReply("hi")
    assert isinstance(reply, TextMessageReply)


def test_all_reply_types_importable():
    assert EditTextMessageReply and EditMenuMessageReply and MenuMessageReply
    assert ReplyKeyboardMessageReply and ReplyKeyboardRemoveMessageReply
