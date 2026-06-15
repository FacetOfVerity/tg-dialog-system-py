"""Hosting: the TgDialogBot entry point and startup helpers."""

from __future__ import annotations

from tg_dialog_system.hosting.bot import TgDialogBot
from tg_dialog_system.hosting.commands_init import set_bot_commands
from tg_dialog_system.hosting.startup import start_with_retry

__all__ = ["TgDialogBot", "set_bot_commands", "start_with_retry"]
