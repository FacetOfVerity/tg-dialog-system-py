"""Inline-keyboard replies and the MenuGrid builder (port MenuGrid / MenuButton)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.context import MessageId


@dataclass(frozen=True, slots=True)
class MenuButton:
    text: str
    callback_data: CallbackData


class MenuGrid:
    def __init__(self, rows: Iterable[Iterable[MenuButton]]) -> None:
        self._rows: tuple[tuple[MenuButton, ...], ...] = tuple(
            tuple(row) for row in rows
        )

    @property
    def rows(self) -> tuple[tuple[MenuButton, ...], ...]:
        return self._rows

    @staticmethod
    def builder() -> MenuGrid.Builder:
        return MenuGrid.Builder()

    @staticmethod
    def build(configure: Callable[[MenuGrid.Builder], MenuGrid.Builder]) -> MenuGrid:
        builder = MenuGrid.Builder()
        configure(builder)
        return builder.build()

    class Builder:
        def __init__(self) -> None:
            self._rows: list[list[MenuButton]] = []
            self._current: list[MenuButton] = []

        def button(self, text: str, callback_data: CallbackData) -> MenuGrid.Builder:
            self._current.append(MenuButton(text, callback_data))
            return self

        def new_row(self) -> MenuGrid.Builder:
            if self._current:
                self._rows.append(self._current)
                self._current = []
            return self

        def group_every(
            self, buttons: Iterable[MenuButton], per_row: int
        ) -> MenuGrid.Builder:
            chunk: list[MenuButton] = []
            for button in buttons:
                chunk.append(button)
                if len(chunk) == per_row:
                    self._rows.append(chunk)
                    chunk = []
            if chunk:
                self._rows.append(chunk)
            return self

        def build(self) -> MenuGrid:
            self.new_row()
            return MenuGrid(self._rows)


@dataclass(frozen=True, slots=True)
class MenuMessageReply:
    text: str
    buttons: MenuGrid


@dataclass(frozen=True, slots=True)
class EditMenuMessageReply:
    message_id: MessageId
    text: str
    buttons: MenuGrid
