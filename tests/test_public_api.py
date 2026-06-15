import tg_dialog_system as tg


def test_public_exports_present():
    names = [
        "TgDialogBot", "TelegramSettings", "BotMode",
        "command_route", "callback_route", "discover_handlers",
        "CallbackData", "Version", "MessageContext", "CallbackContext",
        "TextMessageReply", "EditTextMessageReply",
        "MenuMessageReply", "EditMenuMessageReply", "MenuGrid",
        "ReplyKeyboardBuilder", "ReplyKeyboardOptions",
        "ReplyKeyboardMessageReply", "ReplyKeyboardRemoveMessageReply",
        "errors",
    ]
    for name in names:
        assert hasattr(tg, name), f"missing public export: {name}"
