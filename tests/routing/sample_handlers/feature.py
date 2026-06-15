from expression import Ok

from tg_dialog_system.models.context import MessageContext
from tg_dialog_system.models.replies import ReplyResult, TextMessageReply
from tg_dialog_system.routing.decorators import command_route
from tg_dialog_system.routing.registry import HandlerRegistry

REGISTRY = HandlerRegistry()


@command_route("/from_discovery", registry=REGISTRY)
async def handle(ctx: MessageContext) -> ReplyResult:
    return Ok(TextMessageReply("discovered"))
