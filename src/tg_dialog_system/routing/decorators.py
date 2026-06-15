"""@command_route / @callback_route decorators (port the routing attributes)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from tg_dialog_system.models.version import Version
from tg_dialog_system.routing.registry import HandlerRegistry, default_registry

F = TypeVar("F", bound=Callable[..., Awaitable])


def command_route(command: str, *, registry: HandlerRegistry | None = None) -> Callable[[F], F]:
    target = registry or default_registry

    def decorator(func: F) -> F:
        target.register_command(command, func)
        return func

    return decorator


def callback_route(
    version: Version,
    menu_id: str,
    action: str,
    *,
    registry: HandlerRegistry | None = None,
) -> Callable[[F], F]:
    target = registry or default_registry
    route_key = f"{version.name}:{menu_id}:{action}"

    def decorator(func: F) -> F:
        target.register_callback(route_key, func)
        return func

    return decorator
