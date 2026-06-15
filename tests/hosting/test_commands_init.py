from aiogram.types import BotCommand

from tg_dialog_system.hosting.commands_init import set_bot_commands


class FakeBot:
    def __init__(self):
        self.menu_button_set = False
        self.commands = []

    async def set_chat_menu_button(self, **kwargs):
        self.menu_button_set = True

    async def set_my_commands(self, commands, **kwargs):
        self.commands.append((kwargs.get("language_code"), [c.command for c in commands]))


class FakeProvider:
    def get_chat_menu_buttons_by_language_code(self):
        return {
            "en": [BotCommand(command="start", description="Start")],
            "ru": [BotCommand(command="start", description="Старт")],
        }


async def test_sets_menu_button_and_per_language_commands():
    bot = FakeBot()
    await set_bot_commands(bot, FakeProvider())
    assert bot.menu_button_set
    langs = [lang for lang, _ in bot.commands]
    assert "en" in langs and "ru" in langs
    # default (language_code=None) uses the English set
    assert (None, ["start"]) in bot.commands


async def test_falls_back_when_no_english():
    """Provider omitting 'en' must not raise; default falls back to the first available language."""

    class DeProvider:
        def get_chat_menu_buttons_by_language_code(self):
            return {"de": [BotCommand(command="start", description="Start")]}

    bot = FakeBot()
    await set_bot_commands(bot, DeProvider())
    assert bot.menu_button_set
    langs = [lang for lang, _ in bot.commands]
    assert "de" in langs
    # default (language_code=None) must be set to something (the only available set)
    assert (None, ["start"]) in bot.commands
