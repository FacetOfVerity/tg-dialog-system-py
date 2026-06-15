from types import SimpleNamespace

from expression import Error as Err
from expression import Ok

from tg_dialog_system import errors
from tg_dialog_system.models.context import CallbackContext, MessageContext
from tg_dialog_system.models.replies import TextMessageReply
from tg_dialog_system.models.version import Version
from tg_dialog_system.routing.decorators import callback_route, command_route
from tg_dialog_system.routing.dispatcher import BotDispatcher
from tg_dialog_system.routing.registry import HandlerRegistry


class RecordingReplySender:
    def __init__(self):
        self.sent = []

    async def send(self, chat_id, reply):
        self.sent.append((chat_id, reply))
        return Ok(1)


class RecordingErrors:
    def __init__(self):
        self.errors = []
        self.unexpected = []

    async def send_errors(self, chat_id, errs):
        self.errors.append((chat_id, errs))

    async def send_unexpected_error(self, chat_id):
        self.unexpected.append(chat_id)


class EchoArbitrary:
    async def handle(self, ctx, payload):
        return Ok(TextMessageReply(f"echo:{payload}"))


def _message(text):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=500),
        message_id=9,
        from_user=SimpleNamespace(id=1, language_code="en"),
    )


def _query(data):
    return SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=1, language_code="en"),
        message=SimpleNamespace(chat=SimpleNamespace(id=500), message_id=9),
    )


def _make(registry):
    reply_sender = RecordingReplySender()
    errs = RecordingErrors()
    dispatcher = BotDispatcher(
        registry=registry,
        reply_sender=reply_sender,
        errors_processor=errs,
        arbitrary_text_handler=EchoArbitrary(),
        dependencies={"greeting": "hello"},
    )
    return dispatcher, reply_sender, errs


async def test_command_handler_with_injected_dependency():
    reg = HandlerRegistry()

    @command_route("/start", registry=reg)
    async def start(ctx: MessageContext, greeting: str):
        return Ok(TextMessageReply(greeting))

    dispatcher, reply_sender, _ = _make(reg)
    await dispatcher.handle_message(_message("/start"))
    assert reply_sender.sent[0][1] == TextMessageReply("hello")


async def test_arbitrary_text_routed_to_handler():
    reg = HandlerRegistry()
    dispatcher, reply_sender, _ = _make(reg)
    await dispatcher.handle_message(_message("free text"))
    assert reply_sender.sent[0][1] == TextMessageReply("echo:free text")


async def test_empty_message_sends_errors():
    reg = HandlerRegistry()
    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("   "))
    assert errs.errors and errs.errors[0][0] == 500


async def test_unknown_command_sends_errors():
    reg = HandlerRegistry()
    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("/missing"))
    assert errs.errors


async def test_callback_handler_receives_payload():
    reg = HandlerRegistry()
    seen = {}

    @callback_route(Version.V1, "pizza", "size_selected", registry=reg)
    async def size_selected(ctx: CallbackContext):
        seen["payload"] = ctx.payload
        return Ok(TextMessageReply("ok"))

    dispatcher, reply_sender, _ = _make(reg)
    await dispatcher.handle_callback(_query("V1:pizza:size_selected:Large"))
    assert seen["payload"] == "Large"


async def test_unparseable_callback_sends_errors():
    reg = HandlerRegistry()
    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_callback(_query(""))
    assert errs.errors


async def test_handler_exception_sends_unexpected_error():
    reg = HandlerRegistry()

    @command_route("/boom", registry=reg)
    async def boom(ctx: MessageContext):
        raise RuntimeError("kaboom")

    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("/boom"))
    assert errs.unexpected == [500]


async def test_handler_error_result_sends_errors():
    reg = HandlerRegistry()

    @command_route("/bad", registry=reg)
    async def bad(ctx: MessageContext):
        return Err([errors.validation("X", "nope")])

    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("/bad"))
    assert errs.errors
