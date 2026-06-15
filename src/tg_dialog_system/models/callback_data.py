"""Parsed callback payload: "Version:MenuId:Action:Payload" (ports CallbackData)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from expression import Error as Err
from expression import Ok, Result

from tg_dialog_system import errors
from tg_dialog_system.errors import Error
from tg_dialog_system.models.version import Version


def _parse_version(raw: str) -> Version | None:
    candidate = raw.strip().upper()
    for version in Version:
        if candidate == version.name or raw.strip() == str(version.value):
            return version
    return None


@dataclass(frozen=True, slots=True)
class CallbackData:
    version: Version
    menu_id: str
    action: str
    payload: str | None = None

    SEPARATOR: ClassVar[str] = ":"

    @property
    def route_key(self) -> str:
        return self.SEPARATOR.join([self.version.name, self.menu_id, self.action])

    def encode(self) -> str:
        return self.SEPARATOR.join(
            [self.version.name, self.menu_id, self.action, self.payload or ""]
        )

    @staticmethod
    def parse(data: str | None) -> Result[CallbackData, list[Error]]:
        if data is None or not data.strip():
            return Err([errors.failure(
                "Telegram.Routing.InvalidCallbackData", "Callback data cannot be empty"
            )])

        parts = data.split(CallbackData.SEPARATOR, 3)
        if len(parts) < 3:
            return Err([errors.failure(
                "Telegram.Routing.InvalidCallbackData", "Callback data is malformed"
            )])

        version = _parse_version(parts[0])
        if version is None:
            return Err([errors.failure(
                "Telegram.Routing.InvalidCallbackData", "Unknown callback version"
            )])

        payload = parts[3] if len(parts) > 3 else None
        return Ok(CallbackData(version, parts[1], parts[2], payload))
