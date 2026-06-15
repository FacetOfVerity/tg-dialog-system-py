import pytest

import tests.routing.sample_handlers as sample
from tg_dialog_system.config import BotMode, TelegramSettings
from tg_dialog_system.hosting.bot import TgDialogBot
from tg_dialog_system.routing.registry import HandlerRegistry

VALID_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz0123456789"


class Arb:
    async def handle(self, ctx, payload):
        from expression import Ok

        from tg_dialog_system.models.replies import TextMessageReply

        return Ok(TextMessageReply(payload))


class Errs:
    async def send_errors(self, chat_id, errors):
        pass

    async def send_unexpected_error(self, chat_id):
        pass


class Menu:
    def get_chat_menu_buttons_by_language_code(self):
        return {"en": []}


def _bot(**kwargs):
    registry = HandlerRegistry()
    return TgDialogBot(
        settings=TelegramSettings(bot_token=VALID_TOKEN, **kwargs),
        chat_menu_button_provider=Menu(),
        arbitrary_text_message_handler=Arb(),
        errors_processor=Errs(),
        dependencies={"greeting": "hi"},
        registry=registry,
    )


def test_construction_wires_aiogram_handlers():
    bot = _bot()
    # both a message and a callback handler are registered on the dispatcher
    assert bot.aiogram_dispatcher.message.handlers
    assert bot.aiogram_dispatcher.callback_query.handlers


def test_discovery_runs_for_handler_packages():
    registry = HandlerRegistry()
    TgDialogBot(
        settings=TelegramSettings(bot_token=VALID_TOKEN),
        chat_menu_button_provider=Menu(),
        arbitrary_text_message_handler=Arb(),
        errors_processor=Errs(),
        handler_packages=[sample],
        registry=registry,
    )
    # sample.feature registers into its own REGISTRY at import time
    assert sample.feature.REGISTRY.get_command("/from_discovery").is_ok()


async def test_run_rejects_webhook_mode():
    bot = _bot(mode=BotMode.WEBHOOK)
    with pytest.raises(NotImplementedError):
        await bot.run()
