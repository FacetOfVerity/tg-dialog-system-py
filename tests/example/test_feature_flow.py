from types import SimpleNamespace

import example.bot.features as features
from example.bot.services.localization import LocalizationService
from example.bot.services.order_state import OrderState
from expression import Ok

from tg_dialog_system.models.replies import EditMenuMessageReply, MenuMessageReply
from tg_dialog_system.routing.discovery import discover_handlers
from tg_dialog_system.routing.dispatcher import BotDispatcher
from tg_dialog_system.routing.registry import default_registry


class ReplySink:
    def __init__(self):
        self.last = None

    async def send(self, chat_id, reply):
        self.last = reply
        return Ok(1)


class NoErrors:
    async def send_errors(self, chat_id, errors):
        raise AssertionError(f"unexpected errors: {errors}")

    async def send_unexpected_error(self, chat_id):
        raise AssertionError("unexpected error")


class NoArb:
    async def handle(self, ctx, payload):
        raise AssertionError("arbitrary handler should not be called")


def _message(text):
    return SimpleNamespace(
        text=text, chat=SimpleNamespace(id=1),
        message_id=10, from_user=SimpleNamespace(id=99, language_code="en"),
    )


def _query(data):
    return SimpleNamespace(
        data=data, from_user=SimpleNamespace(id=99, language_code="en"),
        message=SimpleNamespace(chat=SimpleNamespace(id=1), message_id=10),
    )


def _dispatcher():
    discover_handlers(features)
    return BotDispatcher(
        registry=default_registry,
        reply_sender=(sink := ReplySink()),
        errors_processor=NoErrors(),
        arbitrary_text_handler=NoArb(),
        dependencies={"localization": LocalizationService(), "order_state": OrderState()},
    ), sink


async def test_start_shows_menu():
    dispatcher, sink = _dispatcher()
    await dispatcher.handle_message(_message("/start"))
    assert isinstance(sink.last, MenuMessageReply)


async def test_select_size_then_size_selected():
    dispatcher, sink = _dispatcher()
    await dispatcher.handle_callback(_query("V1:pizza:select_size:"))
    assert isinstance(sink.last, EditMenuMessageReply)
    await dispatcher.handle_callback(_query("V1:pizza:size_selected:Large"))
    assert isinstance(sink.last, EditMenuMessageReply)
