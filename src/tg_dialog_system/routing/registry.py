"""Handler registry populated by routing decorators (port RoutingTypesProvider)."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from expression import Error as Err
from expression import Ok, Result

from tg_dialog_system import errors
from tg_dialog_system.errors import Error

Handler = Callable[..., Awaitable]


@dataclass(frozen=True, slots=True)
class HandlerEntry:
    kind: str  # "command" | "callback"
    key: str
    func: Handler
    signature: inspect.Signature


class HandlerRegistry:
    def __init__(self) -> None:
        self.commands: dict[str, HandlerEntry] = {}
        self.callbacks: dict[str, HandlerEntry] = {}

    def register_command(self, command: str, func: Handler) -> None:
        if command in self.commands:
            raise ValueError(f"Duplicate command route: {command}")
        self.commands[command] = HandlerEntry(
            "command", command, func, inspect.signature(func)
        )

    def register_callback(self, route_key: str, func: Handler) -> None:
        if route_key in self.callbacks:
            raise ValueError(f"Duplicate callback route: {route_key}")
        self.callbacks[route_key] = HandlerEntry(
            "callback", route_key, func, inspect.signature(func)
        )

    def get_command(self, command: str) -> Result[HandlerEntry, list[Error]]:
        entry = self.commands.get(command)
        if entry is None:
            return Err([errors.not_found(
                "Telegram.Routing.UndefinedCommand", "Command not found"
            )])
        return Ok(entry)

    def get_callback(self, route_key: str) -> Result[HandlerEntry, list[Error]]:
        entry = self.callbacks.get(route_key)
        if entry is None:
            return Err([errors.not_found(
                f"Telegram.Routing.UndefinedCallbackRoute:{route_key}",
                "Callback route not found",
            )])
        return Ok(entry)

    def clear(self) -> None:
        self.commands.clear()
        self.callbacks.clear()


default_registry = HandlerRegistry()
