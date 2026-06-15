from expression import Ok

from tg_dialog_system.models.context import MessageContext
from tg_dialog_system.models.replies import ReplyResult, TextMessageReply
from tg_dialog_system.protocols import (
    ArbitraryTextMessageHandler,
    BotErrorsProcessor,
    ChatMenuButtonProvider,
)


class _Arb:
    async def handle(self, ctx: MessageContext, payload: str) -> ReplyResult:
        return Ok(TextMessageReply(payload))


class _Errs:
    async def send_errors(self, chat_id, errors):
        return None

    async def send_unexpected_error(self, chat_id):
        return None


class _Menu:
    def get_chat_menu_buttons_by_language_code(self):
        return {}


def test_structural_conformance():
    assert isinstance(_Arb(), ArbitraryTextMessageHandler)
    assert isinstance(_Errs(), BotErrorsProcessor)
    assert isinstance(_Menu(), ChatMenuButtonProvider)
