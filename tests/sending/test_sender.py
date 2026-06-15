from types import SimpleNamespace

from aiogram.exceptions import TelegramRetryAfter
from expression import Ok

from tg_dialog_system.errors import ErrorType
from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.replies.menu import MenuGrid
from tg_dialog_system.models.version import Version
from tg_dialog_system.sending.sender import BotMessageSender


class FakeBot:
    def __init__(self, *, raise_exc=None):
        self.raise_exc = raise_exc
        self.calls = []

    async def send_message(self, **kwargs):
        self.calls.append(("send_message", kwargs))
        if self.raise_exc:
            raise self.raise_exc
        return SimpleNamespace(message_id=42)

    async def edit_message_text(self, **kwargs):
        self.calls.append(("edit_message_text", kwargs))
        return SimpleNamespace(message_id=7)


async def test_send_message_returns_message_id():
    sender = BotMessageSender(FakeBot())
    result = await sender.send_message(100, "hello")
    assert result.is_ok()
    assert result.ok == 42


async def test_send_menu_encodes_inline_keyboard():
    bot = FakeBot()
    sender = BotMessageSender(bot)
    grid = MenuGrid.build(
        lambda b: b.button("A", CallbackData(Version.V1, "m", "a"))
    )
    await sender.send_menu(100, "pick", grid)
    _, kwargs = bot.calls[-1]
    markup = kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].callback_data == "V1:m:a:"


async def test_retry_after_becomes_telegram_api_error():
    bot = FakeBot(raise_exc=TelegramRetryAfter(method=None, message="flood", retry_after=5))
    sender = BotMessageSender(bot)
    result = await sender.send_message(100, "x")
    assert result.is_error()
    err = result.error[0]
    assert err.type is ErrorType.TELEGRAM_API
    assert err.code == "Telegram.Api.429"
    assert err.metadata == {"retry_after": 5}


async def test_edit_message_text_path():
    sender = BotMessageSender(FakeBot())
    result = await sender.edit_message_text(100, 7, "new")
    assert result == Ok(7)
