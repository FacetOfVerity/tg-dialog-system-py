import pytest
from expression import Ok

from tg_dialog_system.models.context import CallbackContext, MessageContext
from tg_dialog_system.models.replies import ReplyResult, TextMessageReply
from tg_dialog_system.models.version import Version
from tg_dialog_system.routing.decorators import callback_route, command_route
from tg_dialog_system.routing.registry import HandlerRegistry


def test_command_route_registers_handler():
    reg = HandlerRegistry()

    @command_route("/start", registry=reg)
    async def handle_start(ctx: MessageContext) -> ReplyResult:
        return Ok(TextMessageReply("hi"))

    lookup = reg.get_command("/start")
    assert lookup.is_ok()
    assert lookup.ok.func is handle_start


def test_callback_route_builds_route_key():
    reg = HandlerRegistry()

    @callback_route(Version.V1, "pizza", "select_size", registry=reg)
    async def select_size(ctx: CallbackContext) -> ReplyResult:
        return Ok(TextMessageReply("ok"))

    lookup = reg.get_callback("V1:pizza:select_size")
    assert lookup.is_ok()


def test_duplicate_command_raises():
    reg = HandlerRegistry()

    @command_route("/dup", registry=reg)
    async def a(ctx: MessageContext) -> ReplyResult:
        return Ok(TextMessageReply("a"))

    with pytest.raises(ValueError):

        @command_route("/dup", registry=reg)
        async def b(ctx: MessageContext) -> ReplyResult:
            return Ok(TextMessageReply("b"))


def test_unknown_command_is_error():
    reg = HandlerRegistry()
    assert reg.get_command("/nope").is_error()


def test_unknown_callback_is_error():
    reg = HandlerRegistry()
    assert reg.get_callback("V1:x:y").is_error()
