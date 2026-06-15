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

Distribution name `tg-dialog-system`, import package `tg_dialog_system`. Requires Python ≥ 3.12.
Dependencies (`aiogram`, `expression`, `pydantic-settings`) are pulled in automatically.

## Use in another project

The package is not on PyPI yet, so install it from a local path, from git, or from a built wheel.

```bash
# From a local checkout (uv)
uv add /path/to/tg-dialog-system-py
# editable, so framework edits are picked up immediately:
uv pip install -e /path/to/tg-dialog-system-py

# From git (after pushing this repo to a remote)
uv add "git+https://github.com/<you>/tg-dialog-system-py.git@v0.1.0"
# pip equivalent:
pip install "tg-dialog-system @ git+https://github.com/<you>/tg-dialog-system-py.git@main"

# Build a wheel and install it anywhere
uv build                                              # -> dist/tg_dialog_system-0.1.0-py3-none-any.whl
uv pip install dist/tg_dialog_system-0.1.0-py3-none-any.whl
```

Then write handlers, implement the three extension protocols, and wire everything with `TgDialogBot`:

```python
# myproject/features/start.py
from expression import Ok
from tg_dialog_system import command_route, MessageContext, TextMessageReply
from tg_dialog_system.models.replies import ReplyResult


@command_route("/start")
async def start(ctx: MessageContext) -> ReplyResult:
    return Ok(TextMessageReply("Welcome!"))
```

```python
# myproject/main.py
import asyncio

import myproject.features  # package containing your decorated handlers
from tg_dialog_system import TgDialogBot, TelegramSettings


async def main() -> None:
    settings = TelegramSettings()  # reads TELEGRAM__BOT_TOKEN from env / .env

    bot = TgDialogBot(
        settings=settings,
        chat_menu_button_provider=MyMenuProvider(),       # implement the 3 protocols
        arbitrary_text_message_handler=MyTextHandler(),   # from tg_dialog_system.protocols
        errors_processor=MyErrorsProcessor(None),
        dependencies={"db": db},                          # injected into handlers by parameter name
        handler_packages=[myproject.features],            # discovered + registered at startup
    )
    # The errors processor needs the live Bot that TgDialogBot creates internally:
    bot._dispatcher._errors = MyErrorsProcessor(bot.aiogram_bot)
    await bot.run()


asyncio.run(main())
```

Key points:

- Handlers are plain async functions decorated with `@command_route` / `@callback_route`. Pass the
  package(s) holding them as `handler_packages`; `discover_handlers` imports every submodule so the
  decorators register the routes.
- The first handler parameter is always the context (`MessageContext` / `CallbackContext`); every other
  parameter is resolved **by name** from `dependencies`.
- Consumers implement three `Protocol`s from `tg_dialog_system.protocols`: `ChatMenuButtonProvider`,
  `ArbitraryTextMessageHandler`, `BotErrorsProcessor`.

The `example/` directory is a complete, runnable reference (pizza-ordering + contact bot) you can copy
as a starting template.

## Quick start (standalone, in this repo)

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

## Develop on the framework itself

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest
uv run ruff check src tests example
```

## Configuration

Settings load from environment variables / `.env` with the `TELEGRAM__` prefix
(`TELEGRAM__BOT_TOKEN`, `TELEGRAM__MAX_MESSAGES_PER_SECOND`, …). See `.env.example`.
