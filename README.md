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
