# tg-dialog-system Python Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-implement the .NET `tg-dialog-system` Telegram dialog framework in idiomatic Python on aiogram 3.x, with a working example bot and a test suite.

**Architecture:** A pure core (`models/`, `errors.py`, `protocols.py` — no aiogram import) plus aiogram-facing infrastructure (`routing/`, `sending/`, `hosting/`). Handlers are decorated async functions returning `expression.Result[ReplyMessage, list[Error]]`; the dispatcher sub-routes aiogram updates by command text / versioned callback key and injects dependencies by parameter name.

**Tech Stack:** Python 3.12+, aiogram 3.x, `expression` (Result type), pydantic-settings, uv + hatchling, ruff, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-06-15-tg-dialog-system-python-port-design.md`

**Conventions for every task:** construct results with `from expression import Ok, Error as Err`; build domain errors via `from tg_dialog_system import errors` then `errors.validation(...)` etc. (avoids the name clash with `expression.Error`).

**`expression` Result API (verified against `expression` 5.6.0 — follow exactly):**
- `Ok(value)` and `Error(error)` are **factory functions**, not classes. Every result is an `expression.Result` instance.
- **Discriminate** with `result.is_ok()` / `result.is_error()` (or `result.tag == "ok"`). **Do NOT** use `isinstance(result, Ok)` or `match result: case Ok(...)` — `Ok`/`Error` are not usable as classes/patterns and will raise.
- **Access** the payload with `result.ok` (valid only when ok) and `result.error` (valid only when error). Reading the wrong side raises `AttributeError`, so always guard with `is_ok()`/`is_error()` first.
- **Equality works**: `Ok(42) == Ok(42)` and `Error([e]) == Error([e])` are `True`, so tests may assert `result == Ok(...)`.
- `match` on **reply dataclasses** (in `ReplyMessageSender`) is fine — those are real classes. The restriction is only about matching on `Ok`/`Error`.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/tg_dialog_system/__init__.py`
- Create: `src/tg_dialog_system/py.typed` (empty)
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "tg-dialog-system"
version = "0.1.0"
description = "Telegram dialog-system bot framework (Python port)"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "aiogram>=3.13",
    "expression>=5.0",
    "pydantic-settings>=2.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/tg_dialog_system"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Create empty `src/tg_dialog_system/__init__.py`, `src/tg_dialog_system/py.typed`, `tests/__init__.py`**

`__init__.py` content for now:
```python
"""Telegram dialog-system bot framework (Python port)."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Write smoke test** — `tests/test_smoke.py`

```python
import tg_dialog_system


def test_package_imports():
    assert tg_dialog_system.__version__ == "0.1.0"
```

- [ ] **Step 4: Install and run**

Run: `uv venv && uv pip install -e ".[dev]" && uv run pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src tests
git commit -m "chore: scaffold Python package with uv/hatchling/pytest/ruff"
```

---

### Task 2: Errors and Result types

**Files:**
- Create: `src/tg_dialog_system/errors.py`
- Test: `tests/test_errors.py`

- [ ] **Step 1: Write failing test** — `tests/test_errors.py`

```python
from tg_dialog_system import errors
from tg_dialog_system.errors import Error, ErrorType


def test_validation_factory_sets_type():
    e = errors.validation("Order.Invalid", "No size selected")
    assert e == Error("Order.Invalid", "No size selected", ErrorType.VALIDATION)
    assert errors.is_validation(e)
    assert not errors.is_unexpected(e)


def test_telegram_api_carries_retry_after():
    e = errors.telegram_api("Telegram.Api.429", "Too many requests", retry_after=7)
    assert e.type is ErrorType.TELEGRAM_API
    assert e.metadata == {"retry_after": 7}
    assert errors.is_telegram_api(e)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_errors.py -v`
Expected: FAIL (`ModuleNotFoundError` / no attribute `validation`)

- [ ] **Step 3: Implement** — `src/tg_dialog_system/errors.py`

```python
"""Domain error model and Result aliases (functional error handling)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from expression import Result  # re-exported for convenience


class ErrorType(Enum):
    FAILURE = "failure"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    TELEGRAM_API = "telegram_api"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True, slots=True)
class Error:
    code: str
    description: str
    type: ErrorType = ErrorType.FAILURE
    metadata: Mapping[str, object] | None = None


type Errors = list[Error]


def failure(code: str, description: str) -> Error:
    return Error(code, description, ErrorType.FAILURE)


def validation(code: str, description: str) -> Error:
    return Error(code, description, ErrorType.VALIDATION)


def not_found(code: str, description: str) -> Error:
    return Error(code, description, ErrorType.NOT_FOUND)


def unexpected(code: str, description: str) -> Error:
    return Error(code, description, ErrorType.UNEXPECTED)


def telegram_api(code: str, description: str, *, retry_after: int | None = None) -> Error:
    metadata = {"retry_after": retry_after} if retry_after is not None else None
    return Error(code, description, ErrorType.TELEGRAM_API, metadata)


def is_validation(error: Error) -> bool:
    return error.type is ErrorType.VALIDATION


def is_not_found(error: Error) -> bool:
    return error.type is ErrorType.NOT_FOUND


def is_telegram_api(error: Error) -> bool:
    return error.type is ErrorType.TELEGRAM_API


def is_unexpected(error: Error) -> bool:
    return error.type is ErrorType.UNEXPECTED


__all__ = [
    "Error",
    "ErrorType",
    "Errors",
    "Result",
    "failure",
    "validation",
    "not_found",
    "unexpected",
    "telegram_api",
    "is_validation",
    "is_not_found",
    "is_telegram_api",
    "is_unexpected",
]
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_errors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/errors.py tests/test_errors.py
git commit -m "feat(errors): add Error model, factories, predicates, Result alias"
```

---

### Task 3: Version enum and CallbackData

**Files:**
- Create: `src/tg_dialog_system/models/__init__.py` (empty for now)
- Create: `src/tg_dialog_system/models/version.py`
- Create: `src/tg_dialog_system/models/callback_data.py`
- Test: `tests/models/__init__.py` (empty), `tests/models/test_callback_data.py`

- [ ] **Step 1: Write failing test** — `tests/models/test_callback_data.py`

```python
from expression import Ok

from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.version import Version


def test_route_key_and_encode():
    cb = CallbackData(Version.V1, "pizza", "size_selected", "Large")
    assert cb.route_key == "V1:pizza:size_selected"
    assert cb.encode() == "V1:pizza:size_selected:Large"


def test_encode_with_none_payload_has_trailing_separator():
    cb = CallbackData(Version.V1, "pizza", "select_size")
    assert cb.encode() == "V1:pizza:select_size:"


def test_parse_valid_with_payload():
    result = CallbackData.parse("V1:pizza:size_selected:Large")
    assert result == Ok(CallbackData(Version.V1, "pizza", "size_selected", "Large"))


def test_parse_without_payload_yields_none():
    result = CallbackData.parse("V2:pizza:confirm")
    assert result == Ok(CallbackData(Version.V2, "pizza", "confirm", None))


def test_parse_empty_is_error():
    assert CallbackData.parse("").is_error()
    assert CallbackData.parse(None).is_error()


def test_parse_too_few_parts_is_error():
    assert CallbackData.parse("V1:pizza").is_error()


def test_parse_bad_version_is_error():
    assert CallbackData.parse("V9:pizza:confirm").is_error()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/models/test_callback_data.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implement `version.py`**

```python
"""Callback API version enum (ports VersionOption)."""

from __future__ import annotations

from enum import IntEnum


class Version(IntEnum):
    V1 = 1
    V2 = 2
```

- [ ] **Step 4: Implement `callback_data.py`**

```python
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

        parts = data.split(CallbackData.SEPARATOR)
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
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/models/test_callback_data.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/models tests/models
git commit -m "feat(models): add Version enum and CallbackData parse/encode"
```

---

### Task 4: Contexts and id aliases

**Files:**
- Create: `src/tg_dialog_system/models/context.py`
- Test: `tests/models/test_context.py`

- [ ] **Step 1: Write failing test** — `tests/models/test_context.py`

```python
from tg_dialog_system.models.context import CallbackContext, MessageContext


def test_message_context_fields():
    ctx = MessageContext(user_id=1, chat_id=2, message_id=3, language_code="ru")
    assert (ctx.user_id, ctx.chat_id, ctx.message_id, ctx.language_code) == (1, 2, 3, "ru")


def test_callback_context_carries_payload():
    ctx = CallbackContext(user_id=1, chat_id=2, message_id=3, language_code=None, payload="Large")
    assert ctx.payload == "Large"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/models/test_context.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/models/context.py`

```python
"""Handler input contexts (port InlineMessageInfo / UserMessageInfo)."""

from __future__ import annotations

from dataclasses import dataclass

type ChatId = int
type UserId = int
type MessageId = int


@dataclass(frozen=True, slots=True)
class MessageContext:
    user_id: UserId
    chat_id: ChatId
    message_id: MessageId
    language_code: str | None = None


@dataclass(frozen=True, slots=True)
class CallbackContext:
    user_id: UserId
    chat_id: ChatId
    message_id: MessageId
    language_code: str | None = None
    payload: str | None = None
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/models/test_context.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/models/context.py tests/models/test_context.py
git commit -m "feat(models): add MessageContext and CallbackContext"
```

---

### Task 5: Menu replies and MenuGrid builder

**Files:**
- Create: `src/tg_dialog_system/models/replies/__init__.py` (filled in Task 7; create empty now)
- Create: `src/tg_dialog_system/models/replies/text.py`
- Create: `src/tg_dialog_system/models/replies/menu.py`
- Test: `tests/models/test_menu.py`

- [ ] **Step 1: Write failing test** — `tests/models/test_menu.py`

```python
from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.replies.menu import MenuButton, MenuGrid
from tg_dialog_system.models.version import Version


def _cb(action: str) -> CallbackData:
    return CallbackData(Version.V1, "pizza", action)


def test_build_with_rows():
    grid = MenuGrid.build(
        lambda b: b.button("A", _cb("a")).button("B", _cb("b")).new_row().button("C", _cb("c"))
    )
    assert grid.rows == (
        (MenuButton("A", _cb("a")), MenuButton("B", _cb("b"))),
        (MenuButton("C", _cb("c")),),
    )


def test_build_finalizes_last_row_without_explicit_new_row():
    grid = MenuGrid.build(lambda b: b.button("only", _cb("x")))
    assert len(grid.rows) == 1
    assert grid.rows[0][0].text == "only"


def test_group_every_chunks_buttons():
    buttons = [MenuButton(str(i), _cb(str(i))) for i in range(5)]
    grid = MenuGrid.build(lambda b: b.group_every(buttons, per_row=2))
    assert [len(row) for row in grid.rows] == [2, 2, 1]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/models/test_menu.py -v`
Expected: FAIL

- [ ] **Step 3: Create empty `src/tg_dialog_system/models/replies/__init__.py`**

```python
```

- [ ] **Step 4: Implement `text.py`**

```python
"""Plain-text reply messages (port TextMessageReply / EditTextMessageReply)."""

from __future__ import annotations

from dataclasses import dataclass

from tg_dialog_system.models.context import MessageId


@dataclass(frozen=True, slots=True)
class TextMessageReply:
    value: str


@dataclass(frozen=True, slots=True)
class EditTextMessageReply:
    message_id: MessageId
    value: str
```

- [ ] **Step 5: Implement `menu.py`**

```python
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
```

- [ ] **Step 6: Run to verify it passes**

Run: `uv run pytest tests/models/test_menu.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/tg_dialog_system/models/replies tests/models/test_menu.py
git commit -m "feat(models): add text/menu replies and MenuGrid builder"
```

---

### Task 6: Reply-keyboard replies and builder

**Files:**
- Create: `src/tg_dialog_system/models/replies/keyboard.py`
- Test: `tests/models/test_keyboard.py`

- [ ] **Step 1: Write failing test** — `tests/models/test_keyboard.py`

```python
from tg_dialog_system.models.replies.keyboard import (
    ReplyKeyboardBuilder,
    ReplyKeyboardButton,
    ReplyKeyboardOptions,
)


def test_add_button_creates_first_row():
    kb = ReplyKeyboardBuilder().add_button("Phone").add_button("Email")
    assert kb.rows == [[ReplyKeyboardButton("Phone"), ReplyKeyboardButton("Email")]]


def test_new_row_and_add_row():
    kb = ReplyKeyboardBuilder().add_button("A").new_row().add_row("B", "C")
    assert [[b.text for b in row] for row in kb.rows] == [["A"], ["B", "C"]]


def test_remove_last_row_and_clear():
    kb = ReplyKeyboardBuilder().add_row("A").add_row("B").remove_last_row()
    assert [[b.text for b in row] for row in kb.rows] == [["A"]]
    kb.clear()
    assert kb.rows == []


def test_options_defaults():
    opts = ReplyKeyboardOptions()
    assert (opts.resize_keyboard, opts.one_time_keyboard, opts.selective) == (False, False, False)
    assert opts.input_field_placeholder is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/models/test_keyboard.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/models/replies/keyboard.py`

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/models/test_keyboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/models/replies/keyboard.py tests/models/test_keyboard.py
git commit -m "feat(models): add reply-keyboard replies and builder"
```

---

### Task 7: ReplyMessage union, ReplyResult, and re-exports

**Files:**
- Modify: `src/tg_dialog_system/models/replies/__init__.py`
- Modify: `src/tg_dialog_system/models/__init__.py`
- Test: `tests/models/test_reply_union.py`

- [ ] **Step 1: Write failing test** — `tests/models/test_reply_union.py`

```python
from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuMessageReply,
    ReplyKeyboardMessageReply,
    ReplyKeyboardRemoveMessageReply,
    ReplyMessage,
    TextMessageReply,
)


def test_text_reply_is_member_of_union():
    reply: ReplyMessage = TextMessageReply("hi")
    assert isinstance(reply, TextMessageReply)


def test_all_reply_types_importable():
    assert EditTextMessageReply and EditMenuMessageReply and MenuMessageReply
    assert ReplyKeyboardMessageReply and ReplyKeyboardRemoveMessageReply
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/models/test_reply_union.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `src/tg_dialog_system/models/replies/__init__.py`**

```python
"""Reply message types and the ReplyMessage union."""

from __future__ import annotations

from expression import Result

from tg_dialog_system.errors import Error
from tg_dialog_system.models.replies.keyboard import (
    ReplyKeyboardBuilder,
    ReplyKeyboardButton,
    ReplyKeyboardMessageReply,
    ReplyKeyboardOptions,
    ReplyKeyboardRemoveMessageReply,
)
from tg_dialog_system.models.replies.menu import (
    EditMenuMessageReply,
    MenuButton,
    MenuGrid,
    MenuMessageReply,
)
from tg_dialog_system.models.replies.text import EditTextMessageReply, TextMessageReply

type ReplyMessage = (
    TextMessageReply
    | EditTextMessageReply
    | MenuMessageReply
    | EditMenuMessageReply
    | ReplyKeyboardMessageReply
    | ReplyKeyboardRemoveMessageReply
)

type ReplyResult = Result[ReplyMessage, list[Error]]

__all__ = [
    "TextMessageReply",
    "EditTextMessageReply",
    "MenuButton",
    "MenuGrid",
    "MenuMessageReply",
    "EditMenuMessageReply",
    "ReplyKeyboardButton",
    "ReplyKeyboardOptions",
    "ReplyKeyboardBuilder",
    "ReplyKeyboardMessageReply",
    "ReplyKeyboardRemoveMessageReply",
    "ReplyMessage",
    "ReplyResult",
]
```

- [ ] **Step 4: Implement `src/tg_dialog_system/models/__init__.py`**

```python
"""Pure domain models (no aiogram dependency)."""

from __future__ import annotations

from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.context import (
    CallbackContext,
    ChatId,
    MessageContext,
    MessageId,
    UserId,
)
from tg_dialog_system.models.version import Version

__all__ = [
    "CallbackData",
    "CallbackContext",
    "MessageContext",
    "ChatId",
    "MessageId",
    "UserId",
    "Version",
]
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/models/test_reply_union.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/models tests/models/test_reply_union.py
git commit -m "feat(models): add ReplyMessage union, ReplyResult, package re-exports"
```

---

### Task 8: Protocols (extension points)

**Files:**
- Create: `src/tg_dialog_system/protocols.py`
- Test: `tests/test_protocols.py`

- [ ] **Step 1: Write failing test** — `tests/test_protocols.py`

```python
from tg_dialog_system.models.context import MessageContext
from tg_dialog_system.models.replies import ReplyResult, TextMessageReply
from tg_dialog_system.protocols import (
    ArbitraryTextMessageHandler,
    BotErrorsProcessor,
    ChatMenuButtonProvider,
)
from expression import Ok


class _Arb:
    async def handle(self, ctx: MessageContext, payload: str) -> ReplyResult:
        return Ok(TextMessageReply(payload))


class _Errs:
    async def send_errors(self, chat_id, errors):
        return None

    async def send_unexpected_error(self, chat_id):
        return None


class _Menu:
    def get_chat_menu_buttons_by_language_code(self):
        return {}


def test_structural_conformance():
    assert isinstance(_Arb(), ArbitraryTextMessageHandler)
    assert isinstance(_Errs(), BotErrorsProcessor)
    assert isinstance(_Menu(), ChatMenuButtonProvider)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_protocols.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/protocols.py`

```python
"""Consumer-implemented extension points (structural Protocols)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aiogram.types import BotCommand

from tg_dialog_system.errors import Errors
from tg_dialog_system.models.context import ChatId, MessageContext
from tg_dialog_system.models.replies import ReplyResult


@runtime_checkable
class ChatMenuButtonProvider(Protocol):
    def get_chat_menu_buttons_by_language_code(self) -> dict[str, list[BotCommand]]: ...


@runtime_checkable
class ArbitraryTextMessageHandler(Protocol):
    async def handle(self, ctx: MessageContext, payload: str) -> ReplyResult: ...


@runtime_checkable
class BotErrorsProcessor(Protocol):
    async def send_errors(self, chat_id: ChatId, errors: Errors) -> None: ...

    async def send_unexpected_error(self, chat_id: ChatId) -> None: ...
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_protocols.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/protocols.py tests/test_protocols.py
git commit -m "feat: add extension-point protocols"
```

---

### Task 9: Configuration settings

**Files:**
- Create: `src/tg_dialog_system/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test** — `tests/test_config.py`

```python
import pytest

from tg_dialog_system.config import BotMode, TelegramSettings

VALID_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz0123456789"


def test_defaults_with_valid_token():
    s = TelegramSettings(bot_token=VALID_TOKEN)
    assert s.mode is BotMode.POLLING
    assert s.max_messages_per_second == 30
    assert s.enable_rate_limiting is True


def test_empty_token_rejected():
    with pytest.raises(ValueError):
        TelegramSettings(bot_token="")


def test_placeholder_token_rejected():
    with pytest.raises(ValueError):
        TelegramSettings(bot_token="YOUR_BOT_TOKEN_HERE")


def test_malformed_token_rejected():
    with pytest.raises(ValueError):
        TelegramSettings(bot_token="not-a-token")


def test_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM__BOT_TOKEN", VALID_TOKEN)
    monkeypatch.setenv("TELEGRAM__MAX_MESSAGES_PER_SECOND", "10")
    s = TelegramSettings()
    assert s.bot_token == VALID_TOKEN
    assert s.max_messages_per_second == 10
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/config.py`

```python
"""Typed bot configuration (port TelegramOptions + ValidateBotToken)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER = "your_bot_token_here"


class BotMode(StrEnum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM__",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str
    mode: BotMode = BotMode.POLLING
    max_messages_per_second: int = 30
    max_retries: int = 3
    initial_retry_delay_ms: int = 1000
    enable_rate_limiting: bool = True
    startup_max_retries: int = 5
    startup_initial_retry_delay_ms: int = 2000
    enable_startup_retries: bool = True

    @field_validator("bot_token")
    @classmethod
    def _validate_token(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Telegram bot token is not configured (TELEGRAM__BOT_TOKEN).")
        if value.lower() == _PLACEHOLDER:
            raise ValueError("Replace the placeholder bot token with a real token from @BotFather.")
        parts = value.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) < 30:
            raise ValueError(
                "Invalid Telegram bot token format. Expected '<bot_id>:<token>'."
            )
        return value
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/config.py tests/test_config.py
git commit -m "feat(config): add TelegramSettings with token validation"
```

---

### Task 10: Handler registry and routing decorators

**Files:**
- Create: `src/tg_dialog_system/routing/__init__.py` (empty for now)
- Create: `src/tg_dialog_system/routing/registry.py`
- Create: `src/tg_dialog_system/routing/decorators.py`
- Test: `tests/routing/__init__.py` (empty), `tests/routing/test_registry.py`

- [ ] **Step 1: Write failing test** — `tests/routing/test_registry.py`

```python
import pytest
from expression import Ok

from tg_dialog_system.models.context import CallbackContext, MessageContext
from tg_dialog_system.models.replies import ReplyResult, TextMessageReply
from tg_dialog_system.models.version import Version
from tg_dialog_system.routing.decorators import callback_route, command_route
from tg_dialog_system.routing.registry import HandlerRegistry


def test_command_route_registers_handler():
    reg = HandlerRegistry()

    @command_route("/start", registry=reg)
    async def handle_start(ctx: MessageContext) -> ReplyResult:
        return Ok(TextMessageReply("hi"))

    lookup = reg.get_command("/start")
    assert lookup.is_ok()
    assert lookup.ok.func is handle_start


def test_callback_route_builds_route_key():
    reg = HandlerRegistry()

    @callback_route(Version.V1, "pizza", "select_size", registry=reg)
    async def select_size(ctx: CallbackContext) -> ReplyResult:
        return Ok(TextMessageReply("ok"))

    lookup = reg.get_callback("V1:pizza:select_size")
    assert lookup.is_ok()


def test_duplicate_command_raises():
    reg = HandlerRegistry()

    @command_route("/dup", registry=reg)
    async def a(ctx: MessageContext) -> ReplyResult:
        return Ok(TextMessageReply("a"))

    with pytest.raises(ValueError):

        @command_route("/dup", registry=reg)
        async def b(ctx: MessageContext) -> ReplyResult:
            return Ok(TextMessageReply("b"))


def test_unknown_command_is_error():
    reg = HandlerRegistry()
    assert reg.get_command("/nope").is_error()


def test_unknown_callback_is_error():
    reg = HandlerRegistry()
    assert reg.get_callback("V1:x:y").is_error()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/routing/test_registry.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `registry.py`**

```python
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
```

- [ ] **Step 4: Implement `decorators.py`**

```python
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
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/routing/test_registry.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/routing tests/routing
git commit -m "feat(routing): add handler registry and route decorators"
```

---

### Task 11: Handler discovery (import-walk)

**Files:**
- Create: `src/tg_dialog_system/routing/discovery.py`
- Test: `tests/routing/test_discovery.py`
- Test fixture package: `tests/routing/sample_handlers/__init__.py`, `tests/routing/sample_handlers/feature.py`

- [ ] **Step 1: Create the fixture package** — `tests/routing/sample_handlers/__init__.py` (empty) and `tests/routing/sample_handlers/feature.py`

```python
from expression import Ok

from tg_dialog_system.models.context import MessageContext
from tg_dialog_system.models.replies import ReplyResult, TextMessageReply
from tg_dialog_system.routing.decorators import command_route
from tg_dialog_system.routing.registry import HandlerRegistry

REGISTRY = HandlerRegistry()


@command_route("/from_discovery", registry=REGISTRY)
async def handle(ctx: MessageContext) -> ReplyResult:
    return Ok(TextMessageReply("discovered"))
```

- [ ] **Step 2: Write failing test** — `tests/routing/test_discovery.py`

```python
import tests.routing.sample_handlers as sample
from tg_dialog_system.routing.discovery import discover_handlers


def test_discover_imports_all_submodules():
    # Importing the package alone does not import feature.py; discovery must.
    discover_handlers(sample)
    lookup = sample.feature.REGISTRY.get_command("/from_discovery")
    assert lookup.is_ok()
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/routing/test_discovery.py -v`
Expected: FAIL (`discover_handlers` undefined)

- [ ] **Step 4: Implement** — `src/tg_dialog_system/routing/discovery.py`

```python
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
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/routing/test_discovery.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/routing/discovery.py tests/routing/test_discovery.py tests/routing/sample_handlers
git commit -m "feat(routing): add package handler discovery"
```

---

### Task 12: BotMessageSender (aiogram-facing)

**Files:**
- Create: `src/tg_dialog_system/sending/__init__.py` (empty for now)
- Create: `src/tg_dialog_system/sending/sender.py`
- Test: `tests/sending/__init__.py` (empty), `tests/sending/test_sender.py`

Note: `MessageSender` is the protocol both `BotMessageSender` and the rate-limited decorator implement. The aiogram `Bot` is faked in tests with an object exposing async `send_message` / `edit_message_text` / `delete_message` returning an object with a `message_id` attribute, or raising aiogram exceptions.

- [ ] **Step 1: Write failing test** — `tests/sending/test_sender.py`

```python
from types import SimpleNamespace

from aiogram.exceptions import TelegramRetryAfter
from expression import Ok

from tg_dialog_system.errors import ErrorType
from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.replies.menu import MenuGrid
from tg_dialog_system.models.version import Version
from tg_dialog_system.sending.sender import BotMessageSender


class FakeBot:
    def __init__(self, *, raise_exc=None):
        self.raise_exc = raise_exc
        self.calls = []

    async def send_message(self, **kwargs):
        self.calls.append(("send_message", kwargs))
        if self.raise_exc:
            raise self.raise_exc
        return SimpleNamespace(message_id=42)

    async def edit_message_text(self, **kwargs):
        self.calls.append(("edit_message_text", kwargs))
        return SimpleNamespace(message_id=7)


async def test_send_message_returns_message_id():
    sender = BotMessageSender(FakeBot())
    result = await sender.send_message(100, "hello")
    assert result.is_ok()
    assert result.ok == 42


async def test_send_menu_encodes_inline_keyboard():
    bot = FakeBot()
    sender = BotMessageSender(bot)
    grid = MenuGrid.build(
        lambda b: b.button("A", CallbackData(Version.V1, "m", "a"))
    )
    await sender.send_menu(100, "pick", grid)
    _, kwargs = bot.calls[-1]
    markup = kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].callback_data == "V1:m:a:"


async def test_retry_after_becomes_telegram_api_error():
    bot = FakeBot(raise_exc=TelegramRetryAfter(method=None, message="flood", retry_after=5))
    sender = BotMessageSender(bot)
    result = await sender.send_message(100, "x")
    assert result.is_error()
    err = result.error[0]
    assert err.type is ErrorType.TELEGRAM_API
    assert err.code == "Telegram.Api.429"
    assert err.metadata == {"retry_after": 5}


async def test_edit_message_text_path():
    sender = BotMessageSender(FakeBot())
    result = await sender.edit_message_text(100, 7, "new")
    assert result == Ok(7)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sending/test_sender.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/sending/sender.py`

```python
"""Maps reply primitives to aiogram Bot calls; converts tg errors to Result (port BotMessageSender)."""

from __future__ import annotations

from typing import Protocol

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from expression import Error as Err
from expression import Ok, Result

from tg_dialog_system import errors
from tg_dialog_system.errors import Error
from tg_dialog_system.models.context import ChatId, MessageId
from tg_dialog_system.models.replies.keyboard import ReplyKeyboardBuilder, ReplyKeyboardOptions
from tg_dialog_system.models.replies.menu import MenuGrid

SendResult = Result[MessageId, list[Error]]


def _inline_markup(grid: MenuGrid) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b.text, callback_data=b.callback_data.encode())
                for b in row
            ]
            for row in grid.rows
        ]
    )


def _reply_markup(
    keyboard: ReplyKeyboardBuilder, options: ReplyKeyboardOptions | None
) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=b.text) for b in row] for row in keyboard.rows if row]
    opts = options or ReplyKeyboardOptions()
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=opts.resize_keyboard,
        one_time_keyboard=opts.one_time_keyboard,
        selective=opts.selective,
        input_field_placeholder=opts.input_field_placeholder or None,
    )


class MessageSender(Protocol):
    async def send_message(self, chat_id: ChatId, message: str) -> SendResult: ...
    async def send_menu(self, chat_id: ChatId, text: str, buttons: MenuGrid) -> SendResult: ...
    async def send_reply_keyboard(
        self,
        chat_id: ChatId,
        text: str,
        keyboard: ReplyKeyboardBuilder,
        options: ReplyKeyboardOptions | None = None,
    ) -> SendResult: ...
    async def remove_reply_keyboard(
        self, chat_id: ChatId, text: str = "", selective: bool = False
    ) -> SendResult: ...
    async def edit_message_text(
        self, chat_id: ChatId, message_id: MessageId, text: str
    ) -> SendResult: ...
    async def edit_message_menu(
        self, chat_id: ChatId, message_id: MessageId, text: str, buttons: MenuGrid
    ) -> SendResult: ...


class BotMessageSender:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def _guard(self, coro_factory, action: str) -> SendResult:
        try:
            message = await coro_factory()
            return Ok(message.message_id)
        except TelegramRetryAfter as exc:
            return Err([errors.telegram_api(
                "Telegram.Api.429", "Too many requests", retry_after=exc.retry_after
            )])
        except (TelegramAPIError, TelegramNetworkError) as exc:
            return Err([errors.telegram_api(
                f"Telegram.Api.{type(exc).__name__}", f"Failed to {action}"
            )])
        except Exception as exc:  # noqa: BLE001 - never leak details to users
            return Err([errors.unexpected(
                f"Exception.{type(exc).__name__}", f"Failed to {action}"
            )])

    async def send_message(self, chat_id: ChatId, message: str) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(chat_id=chat_id, text=message), "send message"
        )

    async def send_menu(self, chat_id: ChatId, text: str, buttons: MenuGrid) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=_inline_markup(buttons),
            ),
            "send menu",
        )

    async def send_reply_keyboard(
        self,
        chat_id: ChatId,
        text: str,
        keyboard: ReplyKeyboardBuilder,
        options: ReplyKeyboardOptions | None = None,
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=_reply_markup(keyboard, options),
            ),
            "send reply keyboard",
        )

    async def remove_reply_keyboard(
        self, chat_id: ChatId, text: str = "", selective: bool = False
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.send_message(
                chat_id=chat_id,
                text=text or "Keyboard removed",
                reply_markup=ReplyKeyboardRemove(selective=selective),
            ),
            "remove reply keyboard",
        )

    async def edit_message_text(
        self, chat_id: ChatId, message_id: MessageId, text: str
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text
            ),
            "edit message",
        )

    async def edit_message_menu(
        self, chat_id: ChatId, message_id: MessageId, text: str, buttons: MenuGrid
    ) -> SendResult:
        return await self._guard(
            lambda: self._bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=_inline_markup(buttons),
            ),
            "edit menu",
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sending/test_sender.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/sending tests/sending
git commit -m "feat(sending): add BotMessageSender with tg-error conversion"
```

---

### Task 13: Sliding-window rate limiter

**Files:**
- Create: `src/tg_dialog_system/sending/rate_limit.py`
- Test: `tests/sending/test_rate_limit.py`

The limiter takes injectable `time_func` and `sleep_func` so tests are deterministic. The fake clock advances when `sleep` is called.

- [ ] **Step 1: Write failing test** — `tests/sending/test_rate_limit.py`

```python
from tg_dialog_system.sending.rate_limit import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


async def test_disabled_never_sleeps():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        2, enabled=False, time_func=clock.time, sleep_func=clock.sleep
    )
    for _ in range(5):
        await limiter.wait_for_availability()
    assert clock.sleeps == []


async def test_admits_up_to_limit_without_sleeping():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        2, window=1.0, time_func=clock.time, sleep_func=clock.sleep
    )
    await limiter.wait_for_availability()
    await limiter.wait_for_availability()
    assert clock.sleeps == []


async def test_third_call_waits_for_window():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        2, window=1.0, time_func=clock.time, sleep_func=clock.sleep
    )
    await limiter.wait_for_availability()
    await limiter.wait_for_availability()
    await limiter.wait_for_availability()
    assert clock.sleeps and clock.sleeps[0] > 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sending/test_rate_limit.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/sending/rate_limit.py`

```python
"""Async sliding-window rate limiter (port TelegramRateLimitService)."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable


class SlidingWindowRateLimiter:
    def __init__(
        self,
        permit_limit: int,
        *,
        enabled: bool = True,
        window: float = 1.0,
        time_func: Callable[[], float] = time.monotonic,
        sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._permit_limit = permit_limit
        self._enabled = enabled
        self._window = window
        self._time = time_func
        self._sleep = sleep_func
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    @property
    def queued_count(self) -> int:
        return len(self._timestamps)

    async def wait_for_availability(self) -> None:
        if not self._enabled:
            return
        async with self._lock:
            while True:
                now = self._time()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._permit_limit:
                    self._timestamps.append(now)
                    return
                wait = self._window - (now - self._timestamps[0])
                if wait > 0:
                    await self._sleep(wait)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sending/test_rate_limit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/sending/rate_limit.py tests/sending/test_rate_limit.py
git commit -m "feat(sending): add async sliding-window rate limiter"
```

---

### Task 14: Retry service

**Files:**
- Create: `src/tg_dialog_system/sending/retry.py`
- Test: `tests/sending/test_retry.py`

- [ ] **Step 1: Write failing test** — `tests/sending/test_retry.py`

```python
from expression import Error as Err
from expression import Ok

from tg_dialog_system import errors
from tg_dialog_system.sending.retry import RetryService


def make_service(**kwargs):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    service = RetryService(
        max_retries=3, initial_retry_delay_ms=1000, sleep_func=fake_sleep, **kwargs
    )
    return service, sleeps


async def test_success_returns_immediately():
    service, sleeps = make_service()

    async def op():
        return Ok(1)

    result = await service.execute_with_retry(op, chat_id=10)
    assert result == Ok(1)
    assert sleeps == []


async def test_non_429_error_not_retried():
    service, sleeps = make_service()

    async def op():
        return Err([errors.validation("X", "bad")])

    result = await service.execute_with_retry(op, chat_id=10)
    assert result.is_error()
    assert sleeps == []


async def test_429_retries_then_succeeds_using_retry_after():
    service, sleeps = make_service()
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        if calls["n"] == 1:
            return Err([errors.telegram_api("Telegram.Api.429", "flood", retry_after=4)])
        return Ok(99)

    result = await service.execute_with_retry(op, chat_id=10)
    assert result == Ok(99)
    assert sleeps == [4]


async def test_429_gives_up_after_max_retries():
    service, sleeps = make_service()

    async def op():
        return Err([errors.telegram_api("Telegram.Api.429", "flood")])

    result = await service.execute_with_retry(op, chat_id=10)
    assert result.is_error()
    # max_retries=3 -> sleeps between attempts 1->2 and 2->3 (exponential backoff)
    assert sleeps == [1.0, 2.0]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sending/test_retry.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/sending/retry.py`

```python
"""Retry-on-429 with exponential backoff (port TelegramRetryService)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from expression import Result

from tg_dialog_system.errors import Error as DomainError
from tg_dialog_system.errors import ErrorType
from tg_dialog_system.models.context import ChatId

_RATE_LIMIT_CODE = "Telegram.Api.429"

Operation = Callable[[], Awaitable[Result]]


def _find_429(errs: list[DomainError]) -> DomainError | None:
    for err in errs:
        if err.type is ErrorType.TELEGRAM_API and err.code == _RATE_LIMIT_CODE:
            return err
    return None


class RetryService:
    def __init__(
        self,
        max_retries: int,
        initial_retry_delay_ms: int,
        *,
        sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._max_retries = max_retries
        self._initial_delay_ms = initial_retry_delay_ms
        self._sleep = sleep_func

    async def execute_with_retry(self, operation: Operation, chat_id: ChatId) -> Result:
        attempt = 0
        while True:
            attempt += 1
            result = await operation()
            if result.is_ok():
                return result
            rate_error = _find_429(result.error)
            if rate_error is None or attempt >= self._max_retries:
                return result
            retry_after = (rate_error.metadata or {}).get("retry_after")
            if retry_after:
                delay = float(retry_after)
            else:
                delay = (self._initial_delay_ms / 1000) * (2 ** (attempt - 1))
            await self._sleep(delay)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sending/test_retry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/sending/retry.py tests/sending/test_retry.py
git commit -m "feat(sending): add retry service with 429 backoff and Retry-After"
```

---

### Task 15: ReplyMessageSender (dispatch by reply type)

**Files:**
- Create: `src/tg_dialog_system/sending/reply_sender.py`
- Test: `tests/sending/test_reply_sender.py`

- [ ] **Step 1: Write failing test** — `tests/sending/test_reply_sender.py`

```python
from expression import Ok

from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuMessageReply,
    ReplyKeyboardBuilder,
    ReplyKeyboardMessageReply,
    ReplyKeyboardRemoveMessageReply,
    TextMessageReply,
)
from tg_dialog_system.models.replies.menu import MenuGrid
from tg_dialog_system.models.version import Version
from tg_dialog_system.sending.reply_sender import ReplyMessageSender


class RecordingSender:
    def __init__(self):
        self.method = None

    async def send_message(self, chat_id, message):
        self.method = "send_message"
        return Ok(1)

    async def send_menu(self, chat_id, text, buttons):
        self.method = "send_menu"
        return Ok(1)

    async def send_reply_keyboard(self, chat_id, text, keyboard, options=None):
        self.method = "send_reply_keyboard"
        return Ok(1)

    async def remove_reply_keyboard(self, chat_id, text="", selective=False):
        self.method = "remove_reply_keyboard"
        return Ok(1)

    async def edit_message_text(self, chat_id, message_id, text):
        self.method = "edit_message_text"
        return Ok(1)

    async def edit_message_menu(self, chat_id, message_id, text, buttons):
        self.method = "edit_message_menu"
        return Ok(1)


def _grid():
    return MenuGrid.build(lambda b: b.button("A", CallbackData(Version.V1, "m", "a")))


async def test_dispatch_each_reply_type():
    cases = [
        (TextMessageReply("hi"), "send_message"),
        (MenuMessageReply("t", _grid()), "send_menu"),
        (EditTextMessageReply(5, "e"), "edit_message_text"),
        (EditMenuMessageReply(5, "t", _grid()), "edit_message_menu"),
        (ReplyKeyboardMessageReply("t", ReplyKeyboardBuilder()), "send_reply_keyboard"),
        (ReplyKeyboardRemoveMessageReply("bye"), "remove_reply_keyboard"),
    ]
    for reply, expected in cases:
        sender = RecordingSender()
        await ReplyMessageSender(sender).send(100, reply)
        assert sender.method == expected
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sending/test_reply_sender.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/sending/reply_sender.py`

```python
"""Selects the sender method based on the reply type (port ReplyMessageSender)."""

from __future__ import annotations

from tg_dialog_system.models.context import ChatId
from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuMessageReply,
    ReplyKeyboardMessageReply,
    ReplyKeyboardRemoveMessageReply,
    ReplyMessage,
    TextMessageReply,
)
from tg_dialog_system.sending.sender import MessageSender, SendResult


class ReplyMessageSender:
    def __init__(self, sender: MessageSender) -> None:
        self._sender = sender

    async def send(self, chat_id: ChatId, reply: ReplyMessage) -> SendResult:
        match reply:
            case EditTextMessageReply():
                return await self._sender.edit_message_text(
                    chat_id, reply.message_id, reply.value
                )
            case EditMenuMessageReply():
                return await self._sender.edit_message_menu(
                    chat_id, reply.message_id, reply.text, reply.buttons
                )
            case TextMessageReply():
                return await self._sender.send_message(chat_id, reply.value)
            case MenuMessageReply():
                return await self._sender.send_menu(chat_id, reply.text, reply.buttons)
            case ReplyKeyboardMessageReply():
                return await self._sender.send_reply_keyboard(
                    chat_id, reply.text, reply.keyboard, reply.options
                )
            case ReplyKeyboardRemoveMessageReply():
                return await self._sender.remove_reply_keyboard(
                    chat_id, reply.text, reply.selective
                )
            case _:
                raise TypeError(f"Unsupported reply type: {type(reply)!r}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sending/test_reply_sender.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/sending/reply_sender.py tests/sending/test_reply_sender.py
git commit -m "feat(sending): add ReplyMessageSender dispatch by reply type"
```

---

### Task 16: RateLimitedBotMessageSender decorator

**Files:**
- Create: `src/tg_dialog_system/sending/rate_limited.py`
- Modify: `src/tg_dialog_system/sending/__init__.py`
- Test: `tests/sending/test_rate_limited.py`

- [ ] **Step 1: Write failing test** — `tests/sending/test_rate_limited.py`

```python
from expression import Ok

from tg_dialog_system.sending.rate_limited import RateLimitedBotMessageSender


class FakeInner:
    def __init__(self):
        self.calls = []

    async def send_message(self, chat_id, message):
        self.calls.append("send_message")
        return Ok(1)


class FakeRateLimiter:
    def __init__(self):
        self.waited = 0

    async def wait_for_availability(self):
        self.waited += 1


class PassthroughRetry:
    async def execute_with_retry(self, operation, chat_id):
        return await operation()


async def test_waits_then_delegates():
    inner = FakeInner()
    limiter = FakeRateLimiter()
    sender = RateLimitedBotMessageSender(inner, limiter, PassthroughRetry())
    result = await sender.send_message(100, "hi")
    assert result == Ok(1)
    assert limiter.waited == 1
    assert inner.calls == ["send_message"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sending/test_rate_limited.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/sending/rate_limited.py`

```python
"""Rate-limit + retry decorator over a MessageSender (port RateLimitedBotMessageSender)."""

from __future__ import annotations

from typing import Protocol

from tg_dialog_system.models.context import ChatId, MessageId
from tg_dialog_system.models.replies.keyboard import ReplyKeyboardBuilder, ReplyKeyboardOptions
from tg_dialog_system.models.replies.menu import MenuGrid
from tg_dialog_system.sending.rate_limit import SlidingWindowRateLimiter
from tg_dialog_system.sending.sender import MessageSender, SendResult


class _Retry(Protocol):
    async def execute_with_retry(self, operation, chat_id: ChatId) -> SendResult: ...


class RateLimitedBotMessageSender:
    def __init__(
        self,
        inner: MessageSender,
        rate_limiter: SlidingWindowRateLimiter,
        retry: _Retry,
    ) -> None:
        self._inner = inner
        self._rate_limiter = rate_limiter
        self._retry = retry

    async def _run(self, op_factory, chat_id: ChatId) -> SendResult:
        async def operation() -> SendResult:
            await self._rate_limiter.wait_for_availability()
            return await op_factory()

        return await self._retry.execute_with_retry(operation, chat_id)

    async def send_message(self, chat_id: ChatId, message: str) -> SendResult:
        return await self._run(lambda: self._inner.send_message(chat_id, message), chat_id)

    async def send_menu(self, chat_id: ChatId, text: str, buttons: MenuGrid) -> SendResult:
        return await self._run(lambda: self._inner.send_menu(chat_id, text, buttons), chat_id)

    async def send_reply_keyboard(
        self,
        chat_id: ChatId,
        text: str,
        keyboard: ReplyKeyboardBuilder,
        options: ReplyKeyboardOptions | None = None,
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.send_reply_keyboard(chat_id, text, keyboard, options), chat_id
        )

    async def remove_reply_keyboard(
        self, chat_id: ChatId, text: str = "", selective: bool = False
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.remove_reply_keyboard(chat_id, text, selective), chat_id
        )

    async def edit_message_text(
        self, chat_id: ChatId, message_id: MessageId, text: str
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.edit_message_text(chat_id, message_id, text), chat_id
        )

    async def edit_message_menu(
        self, chat_id: ChatId, message_id: MessageId, text: str, buttons: MenuGrid
    ) -> SendResult:
        return await self._run(
            lambda: self._inner.edit_message_menu(chat_id, message_id, text, buttons), chat_id
        )
```

- [ ] **Step 4: Fill `src/tg_dialog_system/sending/__init__.py`**

```python
"""Outbound message sending: core sender, rate limiting, retry, reply dispatch."""

from __future__ import annotations

from tg_dialog_system.sending.rate_limit import SlidingWindowRateLimiter
from tg_dialog_system.sending.rate_limited import RateLimitedBotMessageSender
from tg_dialog_system.sending.reply_sender import ReplyMessageSender
from tg_dialog_system.sending.retry import RetryService
from tg_dialog_system.sending.sender import BotMessageSender, MessageSender, SendResult

__all__ = [
    "BotMessageSender",
    "MessageSender",
    "SendResult",
    "SlidingWindowRateLimiter",
    "RateLimitedBotMessageSender",
    "RetryService",
    "ReplyMessageSender",
]
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/sending -v`
Expected: PASS (all sending tests)

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/sending/rate_limited.py src/tg_dialog_system/sending/__init__.py tests/sending/test_rate_limited.py
git commit -m "feat(sending): add rate-limit+retry sender decorator and package exports"
```

---

### Task 17: Update dispatcher (sub-routing + injection + Result handling)

**Files:**
- Create: `src/tg_dialog_system/routing/dispatcher.py`
- Modify: `src/tg_dialog_system/routing/__init__.py`
- Test: `tests/routing/test_dispatcher.py`

The dispatcher reads aiogram `Message` / `CallbackQuery` only through attribute access, so tests pass `SimpleNamespace` fakes. It depends on a `ReplyMessageSender`-like object (anything with `async send(chat_id, reply)`), the registry, the errors processor, the arbitrary-text handler, and a dependency map.

- [ ] **Step 1: Write failing test** — `tests/routing/test_dispatcher.py`

```python
from types import SimpleNamespace

from expression import Error as Err
from expression import Ok

from tg_dialog_system import errors
from tg_dialog_system.models.context import CallbackContext, MessageContext
from tg_dialog_system.models.replies import TextMessageReply
from tg_dialog_system.models.version import Version
from tg_dialog_system.routing.decorators import callback_route, command_route
from tg_dialog_system.routing.dispatcher import BotDispatcher
from tg_dialog_system.routing.registry import HandlerRegistry


class RecordingReplySender:
    def __init__(self):
        self.sent = []

    async def send(self, chat_id, reply):
        self.sent.append((chat_id, reply))
        return Ok(1)


class RecordingErrors:
    def __init__(self):
        self.errors = []
        self.unexpected = []

    async def send_errors(self, chat_id, errs):
        self.errors.append((chat_id, errs))

    async def send_unexpected_error(self, chat_id):
        self.unexpected.append(chat_id)


class EchoArbitrary:
    async def handle(self, ctx, payload):
        return Ok(TextMessageReply(f"echo:{payload}"))


def _message(text):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=500),
        message_id=9,
        from_user=SimpleNamespace(id=1, language_code="en"),
    )


def _query(data):
    return SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=1, language_code="en"),
        message=SimpleNamespace(chat=SimpleNamespace(id=500), message_id=9),
    )


def _make(registry):
    reply_sender = RecordingReplySender()
    errs = RecordingErrors()
    dispatcher = BotDispatcher(
        registry=registry,
        reply_sender=reply_sender,
        errors_processor=errs,
        arbitrary_text_handler=EchoArbitrary(),
        dependencies={"greeting": "hello"},
    )
    return dispatcher, reply_sender, errs


async def test_command_handler_with_injected_dependency():
    reg = HandlerRegistry()

    @command_route("/start", registry=reg)
    async def start(ctx: MessageContext, greeting: str):
        return Ok(TextMessageReply(greeting))

    dispatcher, reply_sender, _ = _make(reg)
    await dispatcher.handle_message(_message("/start"))
    assert reply_sender.sent[0][1] == TextMessageReply("hello")


async def test_arbitrary_text_routed_to_handler():
    reg = HandlerRegistry()
    dispatcher, reply_sender, _ = _make(reg)
    await dispatcher.handle_message(_message("free text"))
    assert reply_sender.sent[0][1] == TextMessageReply("echo:free text")


async def test_empty_message_sends_errors():
    reg = HandlerRegistry()
    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("   "))
    assert errs.errors and errs.errors[0][0] == 500


async def test_unknown_command_sends_errors():
    reg = HandlerRegistry()
    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("/missing"))
    assert errs.errors


async def test_callback_handler_receives_payload():
    reg = HandlerRegistry()
    seen = {}

    @callback_route(Version.V1, "pizza", "size_selected", registry=reg)
    async def size_selected(ctx: CallbackContext):
        seen["payload"] = ctx.payload
        return Ok(TextMessageReply("ok"))

    dispatcher, reply_sender, _ = _make(reg)
    await dispatcher.handle_callback(_query("V1:pizza:size_selected:Large"))
    assert seen["payload"] == "Large"


async def test_unparseable_callback_sends_errors():
    reg = HandlerRegistry()
    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_callback(_query(""))
    assert errs.errors


async def test_handler_exception_sends_unexpected_error():
    reg = HandlerRegistry()

    @command_route("/boom", registry=reg)
    async def boom(ctx: MessageContext):
        raise RuntimeError("kaboom")

    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("/boom"))
    assert errs.unexpected == [500]


async def test_handler_error_result_sends_errors():
    reg = HandlerRegistry()

    @command_route("/bad", registry=reg)
    async def bad(ctx: MessageContext):
        return Err([errors.validation("X", "nope")])

    dispatcher, _, errs = _make(reg)
    await dispatcher.handle_message(_message("/bad"))
    assert errs.errors
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/routing/test_dispatcher.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/routing/dispatcher.py`

```python
"""Routes aiogram updates to handlers, injects deps, applies Result handling.

Ports BotUserInputRouter + BotMessagesRouter + CallbackQueriesRouter.
"""

from __future__ import annotations

import logging
from typing import Any

from expression import Error as Err
from expression import Result

from tg_dialog_system import errors
from tg_dialog_system.models.callback_data import CallbackData
from tg_dialog_system.models.context import CallbackContext, ChatId, MessageContext
from tg_dialog_system.protocols import ArbitraryTextMessageHandler, BotErrorsProcessor
from tg_dialog_system.routing.registry import HandlerEntry, HandlerRegistry

logger = logging.getLogger("tg_dialog_system.dispatcher")


class BotDispatcher:
    def __init__(
        self,
        *,
        registry: HandlerRegistry,
        reply_sender: Any,
        errors_processor: BotErrorsProcessor,
        arbitrary_text_handler: ArbitraryTextMessageHandler,
        dependencies: dict[str, Any] | None = None,
    ) -> None:
        self._registry = registry
        self._reply_sender = reply_sender
        self._errors = errors_processor
        self._arbitrary = arbitrary_text_handler
        self._deps = dependencies or {}

    async def _invoke(self, entry: HandlerEntry, context: Any) -> Result:
        params = list(entry.signature.parameters.values())
        kwargs: dict[str, Any] = {}
        for param in params[1:]:
            if param.name not in self._deps:
                raise LookupError(
                    f"Dependency '{param.name}' for handler '{entry.key}' is not registered"
                )
            kwargs[param.name] = self._deps[param.name]
        return await entry.func(context, **kwargs)

    async def _send_result(self, chat_id: ChatId, result: Result) -> None:
        if result.is_error():
            await self._errors.send_errors(chat_id, result.error)
            return
        send_result = await self._reply_sender.send(chat_id, result.ok)
        if send_result.is_error():
            await self._errors.send_errors(chat_id, send_result.error)

    async def handle_message(self, message: Any) -> None:
        chat_id = message.chat.id
        try:
            text = (message.text or "").strip()
            if not text:
                result: Result = Err([errors.failure(
                    "Telegram.Routing.EmptyMessageText", "Message text cannot be empty"
                )])
            else:
                context = MessageContext(
                    user_id=message.from_user.id,
                    chat_id=chat_id,
                    message_id=message.message_id,
                    language_code=message.from_user.language_code,
                )
                if not text.startswith("/"):
                    result = await self._arbitrary.handle(context, text)
                else:
                    lookup = self._registry.get_command(text)
                    if lookup.is_error():
                        result = Err(lookup.error)
                    else:
                        result = await self._invoke(lookup.ok, context)
            await self._send_result(chat_id, result)
        except Exception:  # noqa: BLE001 - top-level safety net
            logger.exception("Unhandled error processing message")
            await self._try_unexpected(chat_id)

    async def handle_callback(self, query: Any) -> None:
        chat_id = query.message.chat.id
        try:
            parsed = CallbackData.parse(query.data)
            if parsed.is_error():
                result: Result = Err(parsed.error)
            else:
                callback_data = parsed.ok
                lookup = self._registry.get_callback(callback_data.route_key)
                if lookup.is_error():
                    result = Err(lookup.error)
                else:
                    context = CallbackContext(
                        user_id=query.from_user.id,
                        chat_id=chat_id,
                        message_id=query.message.message_id,
                        language_code=query.from_user.language_code,
                        payload=callback_data.payload,
                    )
                    result = await self._invoke(lookup.ok, context)
            await self._send_result(chat_id, result)
        except Exception:  # noqa: BLE001 - top-level safety net
            logger.exception("Unhandled error processing callback")
            await self._try_unexpected(chat_id)

    async def _try_unexpected(self, chat_id: ChatId) -> None:
        try:
            await self._errors.send_unexpected_error(chat_id)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send unexpected-error message")
```

- [ ] **Step 4: Fill `src/tg_dialog_system/routing/__init__.py`**

```python
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
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/routing -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/routing/dispatcher.py src/tg_dialog_system/routing/__init__.py tests/routing/test_dispatcher.py
git commit -m "feat(routing): add update dispatcher with DI and Result handling"
```

---

### Task 18: Bot commands initialization

**Files:**
- Create: `src/tg_dialog_system/hosting/__init__.py` (empty for now)
- Create: `src/tg_dialog_system/hosting/commands_init.py`
- Test: `tests/hosting/__init__.py` (empty), `tests/hosting/test_commands_init.py`

- [ ] **Step 1: Write failing test** — `tests/hosting/test_commands_init.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/hosting/test_commands_init.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/hosting/commands_init.py`

```python
"""Register bot commands per language on startup (port TelegramBotCommandsInitService)."""

from __future__ import annotations

from typing import Any

from aiogram.types import BotCommandScopeDefault, MenuButtonCommands

from tg_dialog_system.protocols import ChatMenuButtonProvider

_DEFAULT_LANGUAGE = "en"


async def set_bot_commands(bot: Any, provider: ChatMenuButtonProvider) -> None:
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    commands_by_language = provider.get_chat_menu_buttons_by_language_code()
    for language_code, commands in commands_by_language.items():
        await bot.set_my_commands(
            commands, scope=BotCommandScopeDefault(), language_code=language_code
        )

    default_commands = commands_by_language[_DEFAULT_LANGUAGE]
    await bot.set_my_commands(
        default_commands, scope=BotCommandScopeDefault(), language_code=None
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/hosting/test_commands_init.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/hosting tests/hosting
git commit -m "feat(hosting): add per-language bot commands initialization"
```

---

### Task 19: Startup-with-retry helper

**Files:**
- Create: `src/tg_dialog_system/hosting/startup.py`
- Test: `tests/hosting/test_startup.py`

This isolates the retry/backoff logic (port `TryStartBotWithRetryAsync`) into a pure, testable coroutine. A `non_retryable` predicate decides which exceptions abort immediately (default: aiogram `TelegramUnauthorizedError`).

- [ ] **Step 1: Write failing test** — `tests/hosting/test_startup.py`

```python
import pytest

from tg_dialog_system.config import TelegramSettings
from tg_dialog_system.hosting.startup import start_with_retry

VALID_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz0123456789"


def _settings(**kwargs):
    return TelegramSettings(bot_token=VALID_TOKEN, **kwargs)


async def test_succeeds_first_try():
    sleeps = []

    async def sleep(s):
        sleeps.append(s)

    async def probe():
        return "me"

    result = await start_with_retry(probe, _settings(), sleep_func=sleep)
    assert result == "me"
    assert sleeps == []


async def test_retries_transient_then_succeeds():
    sleeps = []
    calls = {"n": 0}

    async def sleep(s):
        sleeps.append(s)

    async def probe():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "me"

    result = await start_with_retry(
        probe, _settings(startup_initial_retry_delay_ms=1000), sleep_func=sleep
    )
    assert result == "me"
    assert sleeps == [1.0, 2.0]


async def test_non_retryable_aborts_immediately():
    async def sleep(s):
        raise AssertionError("should not sleep")

    async def probe():
        raise ValueError("fatal")

    with pytest.raises(ValueError):
        await start_with_retry(
            probe, _settings(), sleep_func=sleep, non_retryable=lambda e: isinstance(e, ValueError)
        )


async def test_gives_up_after_max_retries():
    async def sleep(s):
        pass

    async def probe():
        raise RuntimeError("always")

    with pytest.raises(RuntimeError):
        await start_with_retry(probe, _settings(startup_max_retries=2), sleep_func=sleep)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/hosting/test_startup.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/hosting/startup.py`

```python
"""Startup probe with exponential-backoff retry (port TryStartBotWithRetryAsync)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiogram.exceptions import TelegramUnauthorizedError

from tg_dialog_system.config import TelegramSettings

logger = logging.getLogger("tg_dialog_system.startup")

T = TypeVar("T")


def _default_non_retryable(exc: Exception) -> bool:
    return isinstance(exc, TelegramUnauthorizedError)


async def start_with_retry(
    probe: Callable[[], Awaitable[T]],
    settings: TelegramSettings,
    *,
    sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
    non_retryable: Callable[[Exception], bool] = _default_non_retryable,
) -> T:
    attempt = 0
    last_exc: Exception | None = None

    while attempt < settings.startup_max_retries:
        attempt += 1
        try:
            return await probe()
        except Exception as exc:  # noqa: BLE001
            if non_retryable(exc):
                logger.error("Non-retryable startup error: %s", type(exc).__name__)
                raise
            last_exc = exc
            if not settings.enable_startup_retries or attempt >= settings.startup_max_retries:
                break
            delay = (settings.startup_initial_retry_delay_ms / 1000) * (2 ** (attempt - 1))
            logger.warning(
                "Bot startup attempt %d/%d failed (%s); retrying in %.1fs",
                attempt, settings.startup_max_retries, type(exc).__name__, delay,
            )
            await sleep_func(delay)

    raise RuntimeError(
        f"Failed to start Telegram bot after {settings.startup_max_retries} attempts"
    ) from last_exc
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/hosting/test_startup.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tg_dialog_system/hosting/startup.py tests/hosting/test_startup.py
git commit -m "feat(hosting): add startup-with-retry helper"
```

---

### Task 20: TgDialogBot host

**Files:**
- Create: `src/tg_dialog_system/hosting/bot.py`
- Modify: `src/tg_dialog_system/hosting/__init__.py`
- Test: `tests/hosting/test_bot.py`

`TgDialogBot` wires the sender chain, registers the two aiogram handlers, runs discovery, and drives `run()`. The aiogram `Bot`/`Dispatcher` are created internally; tests assert on wiring (construction, registered handlers, discovery, webhook rejection) without starting polling.

- [ ] **Step 1: Write failing test** — `tests/hosting/test_bot.py`

```python
import pytest

import tests.routing.sample_handlers as sample
from tg_dialog_system.config import BotMode, TelegramSettings
from tg_dialog_system.hosting.bot import TgDialogBot
from tg_dialog_system.routing.registry import HandlerRegistry

VALID_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz0123456789"


class Arb:
    async def handle(self, ctx, payload):
        from expression import Ok

        from tg_dialog_system.models.replies import TextMessageReply

        return Ok(TextMessageReply(payload))


class Errs:
    async def send_errors(self, chat_id, errors):
        pass

    async def send_unexpected_error(self, chat_id):
        pass


class Menu:
    def get_chat_menu_buttons_by_language_code(self):
        return {"en": []}


def _bot(**kwargs):
    registry = HandlerRegistry()
    return TgDialogBot(
        settings=TelegramSettings(bot_token=VALID_TOKEN, **kwargs),
        chat_menu_button_provider=Menu(),
        arbitrary_text_message_handler=Arb(),
        errors_processor=Errs(),
        dependencies={"greeting": "hi"},
        registry=registry,
    )


def test_construction_wires_aiogram_handlers():
    bot = _bot()
    # both a message and a callback handler are registered on the dispatcher
    assert bot.aiogram_dispatcher.message.handlers
    assert bot.aiogram_dispatcher.callback_query.handlers


def test_discovery_runs_for_handler_packages():
    registry = HandlerRegistry()
    TgDialogBot(
        settings=TelegramSettings(bot_token=VALID_TOKEN),
        chat_menu_button_provider=Menu(),
        arbitrary_text_message_handler=Arb(),
        errors_processor=Errs(),
        handler_packages=[sample],
        registry=registry,
    )
    # sample.feature registers into its own REGISTRY at import time
    assert sample.feature.REGISTRY.get_command("/from_discovery").is_ok()


async def test_run_rejects_webhook_mode():
    bot = _bot(mode=BotMode.WEBHOOK)
    with pytest.raises(NotImplementedError):
        await bot.run()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/hosting/test_bot.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — `src/tg_dialog_system/hosting/bot.py`

```python
"""Bot host: wiring + lifecycle (port BotHostedService + AddTelegramBot)."""

from __future__ import annotations

import logging
from types import ModuleType
from typing import Any

from aiogram import Bot, Dispatcher

from tg_dialog_system.config import BotMode, TelegramSettings
from tg_dialog_system.hosting.commands_init import set_bot_commands
from tg_dialog_system.hosting.startup import start_with_retry
from tg_dialog_system.protocols import (
    ArbitraryTextMessageHandler,
    BotErrorsProcessor,
    ChatMenuButtonProvider,
)
from tg_dialog_system.routing.discovery import discover_handlers
from tg_dialog_system.routing.dispatcher import BotDispatcher
from tg_dialog_system.routing.registry import HandlerRegistry, default_registry
from tg_dialog_system.sending.rate_limit import SlidingWindowRateLimiter
from tg_dialog_system.sending.rate_limited import RateLimitedBotMessageSender
from tg_dialog_system.sending.reply_sender import ReplyMessageSender
from tg_dialog_system.sending.retry import RetryService
from tg_dialog_system.sending.sender import BotMessageSender

logger = logging.getLogger("tg_dialog_system.bot")


class TgDialogBot:
    def __init__(
        self,
        *,
        settings: TelegramSettings,
        chat_menu_button_provider: ChatMenuButtonProvider,
        arbitrary_text_message_handler: ArbitraryTextMessageHandler,
        errors_processor: BotErrorsProcessor,
        dependencies: dict[str, Any] | None = None,
        handler_packages: list[ModuleType] | None = None,
        registry: HandlerRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._provider = chat_menu_button_provider
        self._bot = Bot(token=settings.bot_token)
        self._dp = Dispatcher()

        registry = registry or default_registry
        for package in handler_packages or []:
            discover_handlers(package)

        core_sender = BotMessageSender(self._bot)
        rate_limiter = SlidingWindowRateLimiter(
            settings.max_messages_per_second, enabled=settings.enable_rate_limiting
        )
        retry = RetryService(settings.max_retries, settings.initial_retry_delay_ms)
        self._sender = RateLimitedBotMessageSender(core_sender, rate_limiter, retry)
        reply_sender = ReplyMessageSender(self._sender)

        deps = dict(dependencies or {})
        deps.setdefault("bot_message_sender", self._sender)

        self._dispatcher = BotDispatcher(
            registry=registry,
            reply_sender=reply_sender,
            errors_processor=errors_processor,
            arbitrary_text_handler=arbitrary_text_message_handler,
            dependencies=deps,
        )
        self._register_handlers()

    @property
    def aiogram_bot(self) -> Bot:
        return self._bot

    @property
    def aiogram_dispatcher(self) -> Dispatcher:
        return self._dp

    def _register_handlers(self) -> None:
        self._dp.message.register(self._on_message)
        self._dp.callback_query.register(self._on_callback)

    async def _on_message(self, message: Any) -> None:
        await self._dispatcher.handle_message(message)

    async def _on_callback(self, query: Any) -> None:
        await self._dispatcher.handle_callback(query)
        try:
            await query.answer()
        except Exception:  # noqa: BLE001
            logger.debug("callback answer failed", exc_info=True)

    async def run(self) -> None:
        if self._settings.mode is BotMode.WEBHOOK:
            raise NotImplementedError("Webhook mode is not implemented; use polling.")

        await start_with_retry(lambda: self._bot.get_me(), self._settings)
        await set_bot_commands(self._bot, self._provider)
        logger.info("Starting polling")
        await self._dp.start_polling(self._bot, handle_signals=False)
```

- [ ] **Step 4: Fill `src/tg_dialog_system/hosting/__init__.py`**

```python
"""Hosting: the TgDialogBot entry point and startup helpers."""

from __future__ import annotations

from tg_dialog_system.hosting.bot import TgDialogBot
from tg_dialog_system.hosting.commands_init import set_bot_commands
from tg_dialog_system.hosting.startup import start_with_retry

__all__ = ["TgDialogBot", "set_bot_commands", "start_with_retry"]
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/hosting -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/hosting/bot.py src/tg_dialog_system/hosting/__init__.py tests/hosting/test_bot.py
git commit -m "feat(hosting): add TgDialogBot host with wiring and lifecycle"
```

---

### Task 21: Public API surface

**Files:**
- Modify: `src/tg_dialog_system/__init__.py`
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write failing test** — `tests/test_public_api.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_public_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — replace `src/tg_dialog_system/__init__.py`

```python
"""Telegram dialog-system bot framework (Python port).

Public API for building dialog bots: routing decorators, reply types, builders,
the configuration model, and the TgDialogBot host.
"""

from __future__ import annotations

from tg_dialog_system import errors
from tg_dialog_system.config import BotMode, TelegramSettings
from tg_dialog_system.hosting import TgDialogBot
from tg_dialog_system.models import (
    CallbackContext,
    CallbackData,
    MessageContext,
    Version,
)
from tg_dialog_system.models.replies import (
    EditMenuMessageReply,
    EditTextMessageReply,
    MenuButton,
    MenuGrid,
    MenuMessageReply,
    ReplyKeyboardBuilder,
    ReplyKeyboardButton,
    ReplyKeyboardMessageReply,
    ReplyKeyboardOptions,
    ReplyKeyboardRemoveMessageReply,
    ReplyMessage,
    ReplyResult,
    TextMessageReply,
)
from tg_dialog_system.protocols import (
    ArbitraryTextMessageHandler,
    BotErrorsProcessor,
    ChatMenuButtonProvider,
)
from tg_dialog_system.routing import callback_route, command_route, discover_handlers

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "errors",
    "TgDialogBot",
    "TelegramSettings",
    "BotMode",
    "command_route",
    "callback_route",
    "discover_handlers",
    "CallbackData",
    "Version",
    "MessageContext",
    "CallbackContext",
    "TextMessageReply",
    "EditTextMessageReply",
    "MenuButton",
    "MenuMessageReply",
    "EditMenuMessageReply",
    "MenuGrid",
    "ReplyKeyboardButton",
    "ReplyKeyboardOptions",
    "ReplyKeyboardBuilder",
    "ReplyKeyboardMessageReply",
    "ReplyKeyboardRemoveMessageReply",
    "ReplyMessage",
    "ReplyResult",
    "ArbitraryTextMessageHandler",
    "BotErrorsProcessor",
    "ChatMenuButtonProvider",
]
```

- [ ] **Step 4: Run full suite to verify everything passes**

Run: `uv run pytest -v`
Expected: PASS (all tests)

- [ ] **Step 5: Lint**

Run: `uv run ruff check src tests`
Expected: no errors (fix any reported)

- [ ] **Step 6: Commit**

```bash
git add src/tg_dialog_system/__init__.py tests/test_public_api.py
git commit -m "feat: expose curated public API"
```

---

### Task 22: Example bot — services and infrastructure

**Files:**
- Create: `example/__init__.py` (empty), `example/bot/__init__.py` (empty)
- Create: `example/bot/services/__init__.py` (empty)
- Create: `example/bot/services/localization.py`
- Create: `example/bot/services/order_state.py`
- Create: `example/bot/infrastructure/__init__.py` (empty)
- Create: `example/bot/infrastructure/chat_menu_button_provider.py`
- Create: `example/bot/infrastructure/errors_processor.py`
- Create: `example/bot/infrastructure/arbitrary_text_handler.py`
- Test: `tests/example/__init__.py` (empty), `tests/example/test_services.py`

- [ ] **Step 1: Write failing test** — `tests/example/test_services.py`

```python
from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState


def test_localization_falls_back_to_english():
    loc = LocalizationService()
    assert loc.get(MessageKey.ORDER_BUTTON, "fr") == loc.get(MessageKey.ORDER_BUTTON, "en")


def test_localization_formats_args():
    loc = LocalizationService()
    text = loc.get(MessageKey.SELECT_TOPPINGS, "en", "large")
    assert "large" in text


def test_order_state_roundtrip():
    state = OrderState()
    order = state.get_or_create(7)
    order.size = "Large"
    order.toppings.append("Cheese")
    assert state.get_or_create(7).toppings == ["Cheese"]
    state.clear(7)
    assert state.get_or_create(7).size is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/example/test_services.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `example/bot/services/localization.py`**

```python
"""Multi-language strings for the example bot (port LocalizationService)."""

from __future__ import annotations

from enum import Enum, auto


class MessageKey(Enum):
    WELCOME = auto()
    ORDER_BUTTON = auto()
    CONTACT_MESSAGE = auto()
    PHONE_BUTTON = auto()
    EMAIL_BUTTON = auto()
    CANCEL_BUTTON = auto()
    KEYBOARD_REMOVED = auto()
    PHONE_CONTACT_RESPONSE = auto()
    EMAIL_CONTACT_RESPONSE = auto()
    SELECT_SIZE = auto()
    SIZE_SMALL = auto()
    SIZE_MEDIUM = auto()
    SIZE_LARGE = auto()
    SELECT_TOPPINGS = auto()
    TOPPING_CHEESE = auto()
    TOPPING_PEPPERONI = auto()
    TOPPING_MUSHROOMS = auto()
    TOPPING_OLIVES = auto()
    CONFIRM_BUTTON = auto()
    BACK_BUTTON = auto()
    ORDER_CONFIRMATION = auto()
    ORDER_SUCCESS = auto()
    NEW_ORDER_BUTTON = auto()
    ERROR_TOO_MANY_TOPPINGS = auto()
    NO_TOPPINGS = auto()


_MESSAGES: dict[str, dict[MessageKey, str]] = {
    "en": {
        MessageKey.WELCOME: "Welcome to Pizza Bot! 🍕\n\nClick the button below to start ordering.",
        MessageKey.ORDER_BUTTON: "Order Pizza",
        MessageKey.CONTACT_MESSAGE: "How would you like to contact us?\n\nChoose an option below:",
        MessageKey.PHONE_BUTTON: "📞 Phone",
        MessageKey.EMAIL_BUTTON: "📧 Email",
        MessageKey.CANCEL_BUTTON: "❌ Cancel",
        MessageKey.KEYBOARD_REMOVED: "Keyboard hidden. Use /contact to show it again.",
        MessageKey.PHONE_CONTACT_RESPONSE: "Phone: +1 (555) 123-4567\n\nSupport: 9 AM - 6 PM EST.",
        MessageKey.EMAIL_CONTACT_RESPONSE: "Email: support@pizzabot.example.com\n\nReply within 24h.",
        MessageKey.SELECT_SIZE: "Please select pizza size:",
        MessageKey.SIZE_SMALL: "Small (25cm)",
        MessageKey.SIZE_MEDIUM: "Medium (30cm)",
        MessageKey.SIZE_LARGE: "Large (35cm)",
        MessageKey.SELECT_TOPPINGS: "Select toppings for your {0} pizza:",
        MessageKey.TOPPING_CHEESE: "Extra Cheese",
        MessageKey.TOPPING_PEPPERONI: "Pepperoni",
        MessageKey.TOPPING_MUSHROOMS: "Mushrooms",
        MessageKey.TOPPING_OLIVES: "Olives",
        MessageKey.CONFIRM_BUTTON: "Confirm Order",
        MessageKey.BACK_BUTTON: "← Back",
        MessageKey.ORDER_CONFIRMATION: "Your order:\n• Size: {0}\n• Toppings: {1}\n\nTotal: ${2}\n\nConfirm?",
        MessageKey.ORDER_SUCCESS: "Order placed successfully! 🎉\n\nReady in 20 minutes.",
        MessageKey.NEW_ORDER_BUTTON: "Order Another Pizza",
        MessageKey.ERROR_TOO_MANY_TOPPINGS: "You can select maximum 3 toppings!",
        MessageKey.NO_TOPPINGS: "No toppings",
    },
    "ru": {
        MessageKey.WELCOME: "Добро пожаловать в Pizza Bot! 🍕\n\nНажмите кнопку ниже, чтобы начать заказ.",
        MessageKey.ORDER_BUTTON: "Заказать пиццу",
        MessageKey.CONTACT_MESSAGE: "Как вы хотите связаться с нами?\n\nВыберите вариант ниже:",
        MessageKey.PHONE_BUTTON: "📞 Телефон",
        MessageKey.EMAIL_BUTTON: "📧 Email",
        MessageKey.CANCEL_BUTTON: "❌ Отмена",
        MessageKey.KEYBOARD_REMOVED: "Клавиатура скрыта. Используйте /contact для отображения.",
        MessageKey.PHONE_CONTACT_RESPONSE: "Телефон: +7 (495) 123-45-67\n\nПоддержка: 9-18 МСК.",
        MessageKey.EMAIL_CONTACT_RESPONSE: "Email: support@pizzabot.example.ru\n\nОтветим в течение 24 часов.",
        MessageKey.SELECT_SIZE: "Выберите размер пиццы:",
        MessageKey.SIZE_SMALL: "Маленькая (25см)",
        MessageKey.SIZE_MEDIUM: "Средняя (30см)",
        MessageKey.SIZE_LARGE: "Большая (35см)",
        MessageKey.SELECT_TOPPINGS: "Выберите топпинги для {0} пиццы:",
        MessageKey.TOPPING_CHEESE: "Доп. сыр",
        MessageKey.TOPPING_PEPPERONI: "Пепперони",
        MessageKey.TOPPING_MUSHROOMS: "Грибы",
        MessageKey.TOPPING_OLIVES: "Оливки",
        MessageKey.CONFIRM_BUTTON: "Подтвердить заказ",
        MessageKey.BACK_BUTTON: "← Назад",
        MessageKey.ORDER_CONFIRMATION: "Ваш заказ:\n• Размер: {0}\n• Топпинги: {1}\n\nИтого: ${2}\n\nПодтвердить?",
        MessageKey.ORDER_SUCCESS: "Заказ успешно оформлен! 🎉\n\nГотово через 20 минут.",
        MessageKey.NEW_ORDER_BUTTON: "Заказать еще пиццу",
        MessageKey.ERROR_TOO_MANY_TOPPINGS: "Вы можете выбрать максимум 3 топпинга!",
        MessageKey.NO_TOPPINGS: "Без топпингов",
    },
}


class LocalizationService:
    def get(self, key: MessageKey, language_code: str | None = None, *args: object) -> str:
        lang = language_code if language_code in _MESSAGES else "en"
        message = _MESSAGES[lang][key]
        return message.format(*args) if args else message
```

- [ ] **Step 4: Implement `example/bot/services/order_state.py`**

```python
"""In-memory pizza order state (port OrderState / PizzaOrder)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PizzaOrder:
    size: str | None = None
    toppings: list[str] = field(default_factory=list)


class OrderState:
    def __init__(self) -> None:
        self._orders: dict[int, PizzaOrder] = {}

    def get_or_create(self, user_id: int) -> PizzaOrder:
        return self._orders.setdefault(user_id, PizzaOrder())

    def clear(self, user_id: int) -> None:
        self._orders.pop(user_id, None)
```

- [ ] **Step 5: Implement `example/bot/infrastructure/chat_menu_button_provider.py`**

```python
"""Bot command menu per language (port ChatMenuButtonProvider)."""

from __future__ import annotations

from aiogram.types import BotCommand


class ChatMenuButtonProvider:
    def get_chat_menu_buttons_by_language_code(self) -> dict[str, list[BotCommand]]:
        return {
            "en": [
                BotCommand(command="start", description="Start the bot"),
                BotCommand(command="contact", description="Contact support"),
                BotCommand(command="hide", description="Hide keyboard"),
            ],
            "ru": [
                BotCommand(command="start", description="Запустить бота"),
                BotCommand(command="contact", description="Поддержка"),
                BotCommand(command="hide", description="Скрыть клавиатуру"),
            ],
        }
```

- [ ] **Step 6: Implement `example/bot/infrastructure/errors_processor.py`**

```python
"""User-facing error formatting (port BotErrorsProcessor)."""

from __future__ import annotations

from aiogram import Bot

from tg_dialog_system import errors
from tg_dialog_system.errors import Error, Errors
from tg_dialog_system.models.context import ChatId


class BotErrorsProcessor:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_errors(self, chat_id: ChatId, error_list: Errors) -> None:
        await self._bot.send_message(chat_id=chat_id, text=self._format(error_list))

    async def send_unexpected_error(self, chat_id: ChatId) -> None:
        await self._bot.send_message(
            chat_id=chat_id, text="⚠️ Something went wrong. Please try again later."
        )

    @staticmethod
    def _format(error_list: Errors) -> str:
        if not error_list:
            return "⚠️ An unknown error occurred."
        lines: list[str] = []
        for error in error_list:
            lines.append(BotErrorsProcessor._line(error))
        return "\n".join(lines)

    @staticmethod
    def _line(error: Error) -> str:
        if errors.is_validation(error):
            return f"• {error.description}"
        if errors.is_not_found(error):
            return "• Command not found"
        if errors.is_telegram_api(error):
            return "• Service temporarily unavailable"
        return "• A technical error occurred"
```

- [ ] **Step 7: Implement `example/bot/infrastructure/arbitrary_text_handler.py`**

This wires the contact reply-keyboard text (the loose end from the .NET example): button text maps to the proper response; unknown text falls back to "don't understand".

```python
"""Routes free text and reply-keyboard button presses (port ArbitraryTextMessageHandler)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system.models.context import MessageContext
from tg_dialog_system.models.replies import (
    ReplyKeyboardRemoveMessageReply,
    ReplyResult,
    TextMessageReply,
)

_PHONE_KEYS = {"en", "ru"}


class ArbitraryTextMessageHandler:
    def __init__(self, localization: LocalizationService) -> None:
        self._loc = localization
        self._phone_texts = {self._loc.get(MessageKey.PHONE_BUTTON, lang) for lang in _PHONE_KEYS}
        self._email_texts = {self._loc.get(MessageKey.EMAIL_BUTTON, lang) for lang in _PHONE_KEYS}
        self._cancel_texts = {self._loc.get(MessageKey.CANCEL_BUTTON, lang) for lang in _PHONE_KEYS}

    async def handle(self, ctx: MessageContext, payload: str) -> ReplyResult:
        lang = ctx.language_code
        if payload in self._phone_texts:
            return Ok(ReplyKeyboardRemoveMessageReply(
                self._loc.get(MessageKey.PHONE_CONTACT_RESPONSE, lang)
            ))
        if payload in self._email_texts:
            return Ok(ReplyKeyboardRemoveMessageReply(
                self._loc.get(MessageKey.EMAIL_CONTACT_RESPONSE, lang)
            ))
        if payload in self._cancel_texts:
            return Ok(ReplyKeyboardRemoveMessageReply(
                self._loc.get(MessageKey.KEYBOARD_REMOVED, lang)
            ))
        fallback = (
            "Извините, я не понимаю это сообщение. Используйте команды меню или /start"
            if lang == "ru"
            else "Sorry, I don't understand. Please use the menu commands or /start"
        )
        return Ok(TextMessageReply(fallback))
```

- [ ] **Step 8: Run to verify it passes**

Run: `uv run pytest tests/example/test_services.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add example tests/example
git commit -m "feat(example): add localization, order state, and infrastructure"
```

---

### Task 23: Example bot — feature handlers

**Files:**
- Create: `example/bot/features/__init__.py` (empty)
- Create: `example/bot/features/start/__init__.py` (empty), `example/bot/features/start/handle_start.py`
- Create: `example/bot/features/pizza/__init__.py` (empty) and handlers: `select_size.py`, `size_selected.py`, `toggle_topping_v1.py`, `toggle_topping_v2.py`, `confirm_order.py`, `place_order.py`
- Create: `example/bot/features/contact/__init__.py` (empty), `show_contact_keyboard.py`, `hide_contact_keyboard.py`
- Test: `tests/example/test_feature_flow.py`

All handlers use the module-level `default_registry` (the decorators' default). Dependencies `localization` and `order_state` are injected by name.

- [ ] **Step 1: Write failing test** — `tests/example/test_feature_flow.py`

```python
from types import SimpleNamespace

from expression import Ok

import example.bot.features as features
from example.bot.services.localization import LocalizationService
from example.bot.services.order_state import OrderState
from tg_dialog_system.models.replies import EditMenuMessageReply, MenuMessageReply
from tg_dialog_system.routing.dispatcher import BotDispatcher
from tg_dialog_system.routing.registry import default_registry
from tg_dialog_system.routing.discovery import discover_handlers


class ReplySink:
    def __init__(self):
        self.last = None

    async def send(self, chat_id, reply):
        self.last = reply
        return Ok(1)


class NoErrors:
    async def send_errors(self, chat_id, errors):
        raise AssertionError(f"unexpected errors: {errors}")

    async def send_unexpected_error(self, chat_id):
        raise AssertionError("unexpected error")


class NoArb:
    async def handle(self, ctx, payload):
        raise AssertionError("arbitrary handler should not be called")


def _message(text):
    return SimpleNamespace(
        text=text, chat=SimpleNamespace(id=1),
        message_id=10, from_user=SimpleNamespace(id=99, language_code="en"),
    )


def _query(data):
    return SimpleNamespace(
        data=data, from_user=SimpleNamespace(id=99, language_code="en"),
        message=SimpleNamespace(chat=SimpleNamespace(id=1), message_id=10),
    )


def _dispatcher():
    discover_handlers(features)
    return BotDispatcher(
        registry=default_registry,
        reply_sender=(sink := ReplySink()),
        errors_processor=NoErrors(),
        arbitrary_text_handler=NoArb(),
        dependencies={"localization": LocalizationService(), "order_state": OrderState()},
    ), sink


async def test_start_shows_menu():
    dispatcher, sink = _dispatcher()
    await dispatcher.handle_message(_message("/start"))
    assert isinstance(sink.last, MenuMessageReply)


async def test_select_size_then_size_selected():
    dispatcher, sink = _dispatcher()
    await dispatcher.handle_callback(_query("V1:pizza:select_size:"))
    assert isinstance(sink.last, EditMenuMessageReply)
    await dispatcher.handle_callback(_query("V1:pizza:size_selected:Large"))
    assert isinstance(sink.last, EditMenuMessageReply)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/example/test_feature_flow.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `example/bot/features/start/handle_start.py`**

```python
"""/start — entry point (port HandleStartCommand)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import (
    CallbackData,
    MenuGrid,
    MenuMessageReply,
    MessageContext,
    Version,
    command_route,
)
from tg_dialog_system.models.replies import ReplyResult


@command_route("/start")
async def handle_start(ctx: MessageContext, localization: LocalizationService) -> ReplyResult:
    lang = ctx.language_code
    menu = MenuGrid.build(
        lambda b: b.button(
            localization.get(MessageKey.ORDER_BUTTON, lang),
            CallbackData(Version.V1, "pizza", "select_size", ""),
        )
    )
    return Ok(MenuMessageReply(localization.get(MessageKey.WELCOME, lang), menu))
```

- [ ] **Step 4: Implement `example/bot/features/pizza/select_size.py`**

```python
"""Pizza size selection menu (port SelectSizeCallback)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import (
    CallbackContext,
    CallbackData,
    EditMenuMessageReply,
    MenuGrid,
    Version,
    callback_route,
)
from tg_dialog_system.models.replies import ReplyResult


@callback_route(Version.V1, "pizza", "select_size")
async def select_size(ctx: CallbackContext, localization: LocalizationService) -> ReplyResult:
    lang = ctx.language_code

    def build(b: MenuGrid.Builder) -> MenuGrid.Builder:
        return (
            b.button(localization.get(MessageKey.SIZE_SMALL, lang),
                     CallbackData(Version.V1, "pizza", "size_selected", "Small"))
            .button(localization.get(MessageKey.SIZE_MEDIUM, lang),
                    CallbackData(Version.V1, "pizza", "size_selected", "Medium"))
            .new_row()
            .button(localization.get(MessageKey.SIZE_LARGE, lang),
                    CallbackData(Version.V1, "pizza", "size_selected", "Large"))
        )

    return Ok(EditMenuMessageReply(
        ctx.message_id, localization.get(MessageKey.SELECT_SIZE, lang), MenuGrid.build(build)
    ))
```

- [ ] **Step 5: Implement `example/bot/features/pizza/_toppings.py`** (shared menu builder, DRY for v1/v2)

```python
"""Shared toppings-menu builder for the pizza feature."""

from __future__ import annotations

from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import PizzaOrder
from tg_dialog_system import CallbackData, MenuGrid, Version

_TOPPINGS = [
    ("Cheese", MessageKey.TOPPING_CHEESE),
    ("Pepperoni", MessageKey.TOPPING_PEPPERONI),
    ("Mushrooms", MessageKey.TOPPING_MUSHROOMS),
    ("Olives", MessageKey.TOPPING_OLIVES),
]


def build_toppings_menu(
    version: Version, order: PizzaOrder, localization: LocalizationService, lang: str | None
) -> MenuGrid:
    def label(value: str, key: MessageKey) -> str:
        text = localization.get(key, lang)
        return f"✅ {text}" if value in order.toppings else text

    def build(b: MenuGrid.Builder) -> MenuGrid.Builder:
        b.button(label(*_TOPPINGS[0]), CallbackData(version, "pizza", "toggle_topping", "Cheese"))
        b.button(label(*_TOPPINGS[1]), CallbackData(version, "pizza", "toggle_topping", "Pepperoni"))
        b.new_row()
        b.button(label(*_TOPPINGS[2]), CallbackData(version, "pizza", "toggle_topping", "Mushrooms"))
        b.button(label(*_TOPPINGS[3]), CallbackData(version, "pizza", "toggle_topping", "Olives"))
        b.new_row()
        b.button(localization.get(MessageKey.CONFIRM_BUTTON, lang),
                 CallbackData(Version.V1, "pizza", "confirm", ""))
        b.new_row()
        b.button(localization.get(MessageKey.BACK_BUTTON, lang),
                 CallbackData(Version.V1, "pizza", "select_size", ""))
        return b

    return MenuGrid.build(build)
```

- [ ] **Step 6: Implement `example/bot/features/pizza/size_selected.py`**

```python
"""Process size selection, show toppings (port SizeSelectedCallback)."""

from __future__ import annotations

from expression import Error as Err
from expression import Ok

from example.bot.features.pizza._toppings import build_toppings_menu
from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import CallbackContext, EditMenuMessageReply, Version, callback_route, errors
from tg_dialog_system.models.replies import ReplyResult

_VALID_SIZES = {"Small", "Medium", "Large"}


@callback_route(Version.V1, "pizza", "size_selected")
async def size_selected(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    if not ctx.payload or ctx.payload not in _VALID_SIZES:
        return Err([errors.validation("Size.Invalid", "Invalid pizza size selected")])

    order = order_state.get_or_create(ctx.user_id)
    order.size = ctx.payload
    order.toppings.clear()

    lang = ctx.language_code
    menu = build_toppings_menu(Version.V1, order, localization, lang)
    text = localization.get(MessageKey.SELECT_TOPPINGS, lang, ctx.payload.lower())
    return Ok(EditMenuMessageReply(ctx.message_id, text, menu))
```

- [ ] **Step 7: Implement `example/bot/features/pizza/toggle_topping_v1.py`**

```python
"""Toggle topping, no limit (port v1 ToggleToppingCallback)."""

from __future__ import annotations

from expression import Error as Err
from expression import Ok

from example.bot.features.pizza._toppings import build_toppings_menu
from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import CallbackContext, EditMenuMessageReply, Version, callback_route, errors
from tg_dialog_system.models.replies import ReplyResult


@callback_route(Version.V1, "pizza", "toggle_topping")
async def toggle_topping_v1(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    if not ctx.payload:
        return Err([errors.validation("Topping.Invalid", "Invalid topping")])

    order = order_state.get_or_create(ctx.user_id)
    if ctx.payload in order.toppings:
        order.toppings.remove(ctx.payload)
    else:
        order.toppings.append(ctx.payload)

    lang = ctx.language_code
    size_text = order.size.lower() if order.size else "unknown"
    text = localization.get(MessageKey.SELECT_TOPPINGS, lang, size_text)
    menu = build_toppings_menu(Version.V1, order, localization, lang)
    return Ok(EditMenuMessageReply(ctx.message_id, text, menu))
```

- [ ] **Step 8: Implement `example/bot/features/pizza/toggle_topping_v2.py`**

```python
"""Toggle topping, max 3 (port v2 ToggleToppingCallback)."""

from __future__ import annotations

from expression import Error as Err
from expression import Ok

from example.bot.features.pizza._toppings import build_toppings_menu
from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import CallbackContext, EditMenuMessageReply, Version, callback_route, errors
from tg_dialog_system.models.replies import ReplyResult

_MAX_TOPPINGS = 3


@callback_route(Version.V2, "pizza", "toggle_topping")
async def toggle_topping_v2(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    if not ctx.payload:
        return Err([errors.validation("Topping.Invalid", "Invalid topping")])

    order = order_state.get_or_create(ctx.user_id)
    lang = ctx.language_code
    if ctx.payload in order.toppings:
        order.toppings.remove(ctx.payload)
    else:
        if len(order.toppings) >= _MAX_TOPPINGS:
            return Err([errors.validation(
                "Toppings.TooMany", localization.get(MessageKey.ERROR_TOO_MANY_TOPPINGS, lang)
            )])
        order.toppings.append(ctx.payload)

    size_text = order.size.lower() if order.size else "unknown"
    text = localization.get(MessageKey.SELECT_TOPPINGS, lang, size_text)
    if len(order.toppings) == _MAX_TOPPINGS:
        text += f"\n\n⚠️ {localization.get(MessageKey.ERROR_TOO_MANY_TOPPINGS, lang)}"
    menu = build_toppings_menu(Version.V2, order, localization, lang)
    return Ok(EditMenuMessageReply(ctx.message_id, text, menu))
```

- [ ] **Step 9: Implement `example/bot/features/pizza/confirm_order.py`**

```python
"""Order confirmation with price (port ConfirmOrderCallback)."""

from __future__ import annotations

from expression import Error as Err
from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import (
    CallbackContext,
    CallbackData,
    EditMenuMessageReply,
    MenuGrid,
    Version,
    callback_route,
    errors,
)
from tg_dialog_system.models.replies import ReplyResult

_BASE_PRICE = {"Small": 8.99, "Medium": 12.99, "Large": 16.99}


@callback_route(Version.V1, "pizza", "confirm")
async def confirm_order(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    order = order_state.get_or_create(ctx.user_id)
    if order.size is None:
        return Err([errors.validation("Order.Invalid", "No size selected")])

    lang = ctx.language_code
    total = _BASE_PRICE[order.size] + len(order.toppings) * 1.5
    toppings_text = (
        ", ".join(order.toppings) if order.toppings else localization.get(MessageKey.NO_TOPPINGS, lang)
    )
    text = localization.get(
        MessageKey.ORDER_CONFIRMATION, lang, order.size, toppings_text, f"{total:.2f}"
    )

    def build(b: MenuGrid.Builder) -> MenuGrid.Builder:
        return (
            b.button(localization.get(MessageKey.CONFIRM_BUTTON, lang),
                     CallbackData(Version.V1, "pizza", "place_order", ""))
            .new_row()
            .button(localization.get(MessageKey.BACK_BUTTON, lang),
                    CallbackData(Version.V1, "pizza", "size_selected", order.size))
        )

    return Ok(EditMenuMessageReply(ctx.message_id, text, MenuGrid.build(build)))
```

- [ ] **Step 10: Implement `example/bot/features/pizza/place_order.py`**

```python
"""Place the order and reset state (port PlaceOrderCallback)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from example.bot.services.order_state import OrderState
from tg_dialog_system import (
    CallbackContext,
    CallbackData,
    EditMenuMessageReply,
    MenuGrid,
    Version,
    callback_route,
)
from tg_dialog_system.models.replies import ReplyResult


@callback_route(Version.V1, "pizza", "place_order")
async def place_order(
    ctx: CallbackContext, localization: LocalizationService, order_state: OrderState
) -> ReplyResult:
    order_state.clear(ctx.user_id)
    lang = ctx.language_code
    menu = MenuGrid.build(
        lambda b: b.button(
            localization.get(MessageKey.NEW_ORDER_BUTTON, lang),
            CallbackData(Version.V1, "pizza", "select_size", ""),
        )
    )
    return Ok(EditMenuMessageReply(
        ctx.message_id, localization.get(MessageKey.ORDER_SUCCESS, lang), menu
    ))
```

- [ ] **Step 11: Implement `example/bot/features/contact/show_contact_keyboard.py`**

```python
"""/contact — show a reply keyboard (port ShowContactKeyboardCommand)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import (
    MessageContext,
    ReplyKeyboardBuilder,
    ReplyKeyboardMessageReply,
    ReplyKeyboardOptions,
    command_route,
)
from tg_dialog_system.models.replies import ReplyResult


@command_route("/contact")
async def show_contact_keyboard(
    ctx: MessageContext, localization: LocalizationService
) -> ReplyResult:
    lang = ctx.language_code
    keyboard = (
        ReplyKeyboardBuilder()
        .add_button(localization.get(MessageKey.PHONE_BUTTON, lang))
        .add_button(localization.get(MessageKey.EMAIL_BUTTON, lang))
        .new_row()
        .add_button(localization.get(MessageKey.CANCEL_BUTTON, lang))
    )
    options = ReplyKeyboardOptions(
        resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Choose..."
    )
    return Ok(ReplyKeyboardMessageReply(
        localization.get(MessageKey.CONTACT_MESSAGE, lang), keyboard, options
    ))
```

- [ ] **Step 12: Implement `example/bot/features/contact/hide_contact_keyboard.py`**

```python
"""/hide — remove the reply keyboard (port HideContactKeyboardCommand)."""

from __future__ import annotations

from expression import Ok

from example.bot.services.localization import LocalizationService, MessageKey
from tg_dialog_system import MessageContext, ReplyKeyboardRemoveMessageReply, command_route
from tg_dialog_system.models.replies import ReplyResult


@command_route("/hide")
async def hide_contact_keyboard(
    ctx: MessageContext, localization: LocalizationService
) -> ReplyResult:
    return Ok(ReplyKeyboardRemoveMessageReply(
        localization.get(MessageKey.KEYBOARD_REMOVED, ctx.language_code)
    ))
```

- [ ] **Step 13: Run to verify it passes**

Run: `uv run pytest tests/example/test_feature_flow.py -v`
Expected: PASS

- [ ] **Step 14: Commit**

```bash
git add example/bot/features tests/example/test_feature_flow.py
git commit -m "feat(example): add start/pizza/contact feature handlers"
```

---

### Task 24: Example entry point, docs, and final verification

**Files:**
- Create: `example/bot/main.py`
- Create: `.env.example`
- Modify: `README.md`
- Test: full suite + lint (no new test file)

- [ ] **Step 1: Implement `example/bot/main.py`**

```python
"""Run the example pizza/contact bot.

Usage:
    TELEGRAM__BOT_TOKEN=123:abc... uv run python -m example.bot.main
"""

from __future__ import annotations

import asyncio
import logging

import example.bot.features as features
from example.bot.infrastructure.arbitrary_text_handler import ArbitraryTextMessageHandler
from example.bot.infrastructure.chat_menu_button_provider import ChatMenuButtonProvider
from example.bot.infrastructure.errors_processor import BotErrorsProcessor
from example.bot.services.localization import LocalizationService
from example.bot.services.order_state import OrderState
from tg_dialog_system import TelegramSettings, TgDialogBot


async def _main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = TelegramSettings()  # reads TELEGRAM__BOT_TOKEN from env / .env

    localization = LocalizationService()
    order_state = OrderState()

    bot = TgDialogBot(
        settings=settings,
        chat_menu_button_provider=ChatMenuButtonProvider(),
        arbitrary_text_message_handler=ArbitraryTextMessageHandler(localization),
        errors_processor=BotErrorsProcessor(None),  # replaced below with the real Bot
        dependencies={"localization": localization, "order_state": order_state},
        handler_packages=[features],
    )
    # The errors processor needs the live aiogram Bot; inject it now that it exists.
    bot._dispatcher._errors = BotErrorsProcessor(bot.aiogram_bot)  # noqa: SLF001
    await bot.run()


if __name__ == "__main__":
    asyncio.run(_main())
```

Note: the small `_errors` reassignment avoids a chicken-and-egg between the host (which
creates the `Bot`) and the errors processor (which needs it). If you prefer no private
access, construct the processor lazily; this is acceptable for an example.

- [ ] **Step 2: Create `.env.example`**

```bash
# Telegram bot configuration (see README). Copy to .env and fill in your token.
TELEGRAM__BOT_TOKEN=123456789:replace-with-your-real-botfather-token
TELEGRAM__MODE=polling
TELEGRAM__MAX_MESSAGES_PER_SECOND=30
TELEGRAM__MAX_RETRIES=3
TELEGRAM__INITIAL_RETRY_DELAY_MS=1000
TELEGRAM__ENABLE_RATE_LIMITING=true
TELEGRAM__STARTUP_MAX_RETRIES=5
TELEGRAM__STARTUP_INITIAL_RETRY_DELAY_MS=2000
TELEGRAM__ENABLE_STARTUP_RETRIES=true
```

- [ ] **Step 3: Replace `README.md`**

```markdown
# tg-dialog-system (Python)

A framework for building Telegram bots with structured dialog systems, on aiogram 3.x.
Python port of the .NET `tg-dialog-system`.

## Features

- Decorator routing: `@command_route("/start")` and `@callback_route(Version.V1, "menu", "action")`
- Versioned callbacks encoded as `Version:MenuId:Action:Payload`
- Functional error handling with `expression.Result` (`Ok` / `Error`)
- Reply types: text, menu (inline keyboard), edit-text, edit-menu, reply-keyboard, reply-keyboard-remove
- Fluent builders: `MenuGrid`, `ReplyKeyboardBuilder`
- Built-in rate limiting (sliding window) + retry on 429 with `Retry-After`
- Polling host with startup retry and per-language command initialization
- Dependency injection by parameter name

## Install

```bash
uv venv
uv pip install -e ".[dev]"
```

## Quick start

```python
from expression import Ok
from tg_dialog_system import command_route, MessageContext, TextMessageReply
from tg_dialog_system.models.replies import ReplyResult


@command_route("/start")
async def start(ctx: MessageContext) -> ReplyResult:
    return Ok(TextMessageReply("Welcome!"))
```

Wire and run with `TgDialogBot` (see `example/bot/main.py`).

## Run the example

```bash
cp .env.example .env   # set TELEGRAM__BOT_TOKEN
uv run python -m example.bot.main
```

## Test

```bash
uv run pytest
uv run ruff check src tests example
```

## Configuration

Settings load from environment variables / `.env` with the `TELEGRAM__` prefix
(`TELEGRAM__BOT_TOKEN`, `TELEGRAM__MAX_MESSAGES_PER_SECOND`, …). See `.env.example`.
```

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS (all tests across models, routing, sending, hosting, config, example)

- [ ] **Step 5: Lint the whole tree**

Run: `uv run ruff check src tests example`
Expected: no errors (fix any reported, e.g. import order)

- [ ] **Step 6: Commit**

```bash
git add example/bot/main.py .env.example README.md
git commit -m "feat(example): add entry point, .env example, and README"
```

---

## Final review checklist (run after Task 24)

- [ ] `uv run pytest` is fully green.
- [ ] `uv run ruff check src tests example` is clean.
- [ ] The `expression` Result API is used as documented in the Conventions header: discriminate with `result.is_ok()`/`result.is_error()` and read `result.ok`/`result.error` (guarded). No `isinstance(x, Ok)` and no `match result: case Ok(...)` anywhere (verified against `expression` 5.6.0). Equality assertions against `Ok(...)`/`Error(...)` are fine.
- [ ] Webhook mode raises `NotImplementedError` (parity with source).
- [ ] The contact reply-keyboard flow responds (the wired loose end).
