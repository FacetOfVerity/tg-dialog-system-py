"""Reply-keyboard replies, options, and builder (port ReplyKeyboard* models)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReplyKeyboardButton:
    text: str


@dataclass(frozen=True, slots=True)
class ReplyKeyboardOptions:
    resize_keyboard: bool = False
    one_time_keyboard: bool = False
    selective: bool = False
    input_field_placeholder: str | None = None


class ReplyKeyboardBuilder:
    def __init__(self) -> None:
        self._rows: list[list[ReplyKeyboardButton]] = []

    @property
    def rows(self) -> list[list[ReplyKeyboardButton]]:
        return self._rows

    def add_button(self, button: str | ReplyKeyboardButton) -> ReplyKeyboardBuilder:
        if not self._rows:
            self._rows.append([])
        text = button if isinstance(button, ReplyKeyboardButton) else ReplyKeyboardButton(button)
        self._rows[-1].append(text)
        return self

    def add_row(self, *texts: str | ReplyKeyboardButton) -> ReplyKeyboardBuilder:
        # Drop trailing empty row left by new_row() before appending this one
        if self._rows and not self._rows[-1]:
            self._rows.pop()
        row = [t if isinstance(t, ReplyKeyboardButton) else ReplyKeyboardButton(t) for t in texts]
        self._rows.append(row)
        return self

    def new_row(self) -> ReplyKeyboardBuilder:
        self._rows.append([])
        return self

    def clear_current_row(self) -> ReplyKeyboardBuilder:
        if self._rows:
            self._rows[-1].clear()
        return self

    def remove_last_row(self) -> ReplyKeyboardBuilder:
        if self._rows:
            self._rows.pop()
        return self

    def clear(self) -> ReplyKeyboardBuilder:
        self._rows.clear()
        return self


@dataclass(frozen=True, slots=True)
class ReplyKeyboardMessageReply:
    text: str
    keyboard: ReplyKeyboardBuilder
    options: ReplyKeyboardOptions | None = None


@dataclass(frozen=True, slots=True)
class ReplyKeyboardRemoveMessageReply:
    text: str = ""
    selective: bool = False
