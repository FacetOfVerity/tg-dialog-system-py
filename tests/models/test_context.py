from tg_dialog_system.models.context import CallbackContext, MessageContext


def test_message_context_fields():
    ctx = MessageContext(user_id=1, chat_id=2, message_id=3, language_code="ru")
    assert (ctx.user_id, ctx.chat_id, ctx.message_id, ctx.language_code) == (1, 2, 3, "ru")


def test_callback_context_carries_payload():
    ctx = CallbackContext(user_id=1, chat_id=2, message_id=3, language_code=None, payload="Large")
    assert ctx.payload == "Large"
