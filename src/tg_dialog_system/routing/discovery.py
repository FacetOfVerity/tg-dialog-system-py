"""Import every submodule of a package so route decorators run (port reflection scan)."""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def discover_handlers(package: ModuleType) -> None:
    """Recursively import all submodules of *package*.

    Importing a module triggers its @command_route / @callback_route decorators,
    registering the handlers. Replaces .NET assembly reflection.
    """
    if not hasattr(package, "__path__"):
        return  # a plain module, nothing to walk

    for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{package.__name__}."):
        importlib.import_module(module_info.name)
