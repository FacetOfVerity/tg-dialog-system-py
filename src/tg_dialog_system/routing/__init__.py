"""Routing: decorators, registry, discovery, dispatcher."""

from __future__ import annotations

from tg_dialog_system.routing.decorators import callback_route, command_route
from tg_dialog_system.routing.discovery import discover_handlers
from tg_dialog_system.routing.dispatcher import BotDispatcher
from tg_dialog_system.routing.registry import (
    HandlerEntry,
    HandlerRegistry,
    default_registry,
)

__all__ = [
    "command_route",
    "callback_route",
    "discover_handlers",
    "BotDispatcher",
    "HandlerEntry",
    "HandlerRegistry",
    "default_registry",
]
