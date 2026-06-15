# tg-dialog-system — Python port design

**Date:** 2026-06-15
**Status:** Approved (design); ready for implementation planning
**Source:** `../tg-dialog-system` — C#/.NET 9 framework for Telegram dialog-system bots

## Goal

Re-implement the functionality of the .NET `tg-dialog-system` framework in Python,
keeping all of its concepts but expressing them idiomatically. Deliver a reusable,
installable framework package plus a working example bot and a test suite, mirroring
the structure of the source repository.

## Locked decisions

| Topic | Decision |
|-------|----------|
| Telegram library | **aiogram 3.x** (async; we build our dialog layer on top of its dispatcher) |
| Fidelity | **Idiomatic Python, same concepts** — decorators instead of reflection+attributes, type hints, dataclasses; drop heavy DI / MediatR ceremony |
| Error model | **`Result` type via the `expression` library** — handlers return `Result[ReplyMessage, list[Error]]` |
| Scope | **Framework + example bot + tests** |
| Handler style | **Decorated async functions** returning `Result[...]` |
| Dependency injection | **aiogram's built-in injection** (dispatcher workflow data; params resolved by name) |
| Tooling | **uv + hatchling, Python 3.12+, ruff, pytest** |
| Config | **pydantic-settings** (env + `.env`), env prefix `TELEGRAM__` |

## Concept mapping (.NET → Python)

| .NET | Python |
|------|--------|
| `ErrorOr<T>` | `expression.Result[T, list[Error]]` (`Ok` / `Error`) |
| `Error.Validation(code, desc)` | `errors.validation(code, desc)` → `Error` |
| `ErrorTypeExtensions.IsValidation()` | `errors.is_validation(err)` predicates |
| `[CommandRoute("/start")]` + record + MediatR `Handler` | `@command_route("/start")` on an async function |
| `[CallbackRoute(V1,"pizza","select_size")]` | `@callback_route(Version.V1, "pizza", "select_size")` |
| `[ReplyMessageBehavior(Edit)]` attribute | **Dropped** — edit-vs-send is driven by the reply type (see "Deliberate cleanups") |
| `InlineMessageInfo` / `UserMessageInfo` | `CallbackContext` / `MessageContext` dataclasses |
| `CallbackData` `Version:MenuId:Action:Payload` | `CallbackData` dataclass with `parse()` / `encode()` / `route_key` |
| `VersionOption` | `Version` enum (`V1`, `V2`) |
| `TgUserChatId`, `TgBotMessageId`, … (StronglyTypedIds) | plain `int` with semantic aliases (`ChatId = int`) — **wrappers dropped** |
| `MenuGrid.Build(b => …)` / `Builder` | `MenuGrid.build(lambda b: …)` + fluent `MenuGrid.builder()` |
| `ReplyKeyboardBuilder` | `ReplyKeyboardBuilder` (fluent) |
| `IReplyMessage` + reply records | `ReplyMessage` union + frozen dataclasses |
| `IBotMessageSender` | `BotMessageSender` (maps replies → aiogram calls; catches tg errors → `Error`) |
| `RateLimitedBotMessageSender` (decorator) | `RateLimitedBotMessageSender` (wraps `BotMessageSender`) |
| `TelegramRateLimitService` (SlidingWindow) | `SlidingWindowRateLimiter` (asyncio) |
| `TelegramRetryService` (429 backoff) | `RetryService` — uses `TelegramRetryAfter.retry_after` when present |
| `ReplyMessageSender` | `ReplyMessageSender` — selects sender method by reply type |
| `RoutingTypesProvider` (assembly reflection) | `HandlerRegistry` (populated by decorators) + `discovery` (import-walk) |
| MediatR `mediator.Send(command)` | direct `await handler(ctx, **deps)` with by-name injection |
| `BotHostedService` (polling + startup retry) | `TgDialogBot.run()` — aiogram polling + startup retry |
| `TelegramBotCommandsInitService` | `set_bot_commands()` on startup |
| `IChatMenuButtonProvider` / `IArbitraryTextMessageHandler` / `IBotErrorsProcessor` | `Protocol`s of the same names |
| `AddTelegramBot<…>(config)` (MS DI) | `TgDialogBot(settings, providers, deps)` builder |
| `appsettings.json` + `Telegram__` env | `TelegramSettings(BaseSettings)`, env + `.env` |

## Project layout

```
pyproject.toml              # hatchling; deps: aiogram, expression, pydantic-settings; dev: pytest, ruff
README.md
.env.example
src/tg_dialog_system/
  __init__.py               # curated public API re-exports
  config.py                 # TelegramSettings (pydantic-settings) + token validation
  errors.py                 # Error dataclass, ErrorType, factories, predicates, Result aliases
  models/
    __init__.py
    version.py              # Version enum
    callback_data.py        # CallbackData
    context.py              # MessageContext, CallbackContext, id aliases
    replies/
      __init__.py           # ReplyMessage union + re-exports
      text.py               # TextMessageReply, EditTextMessageReply
      menu.py               # MenuButton, MenuGrid (+ builder), MenuMessageReply, EditMenuMessageReply
      keyboard.py           # ReplyKeyboardButton/Options/Builder, ReplyKeyboard{Message,Remove}Reply
  protocols.py              # ChatMenuButtonProvider, ArbitraryTextMessageHandler, BotErrorsProcessor
  routing/
    __init__.py
    decorators.py           # @command_route, @callback_route
    registry.py             # HandlerRegistry, HandlerEntry
    discovery.py            # discover_handlers(package): import-walk to trigger decorators
    dispatcher.py           # message + callback routing, dependency injection, Result handling
  sending/
    __init__.py
    sender.py               # BotMessageSender (aiogram-facing)
    rate_limit.py           # SlidingWindowRateLimiter
    retry.py                # RetryService
    reply_sender.py         # ReplyMessageSender
  hosting/
    __init__.py
    bot.py                  # TgDialogBot
    commands_init.py        # set bot commands per language
example/
  bot/
    main.py                 # wiring + run
    config (.env.example)
    features/
      start/v1/handle_start.py
      pizza/v1/{select_size,size_selected,toggle_topping,confirm_order,place_order}.py
      pizza/v2/toggle_topping.py
      contact/v1/show_contact_keyboard.py
      contact/v1/hide_contact_keyboard.py
    services/{localization.py, order_state.py}
    infrastructure/{arbitrary_text_handler.py, chat_menu_button_provider.py, errors_processor.py}
tests/
  models/, routing/, sending/, config/  (pytest, mirrors the .NET test suite)
```

The .NET **Abstractions vs Infrastructure** split is preserved: `models/` + `errors.py` +
`protocols.py` are pure (no aiogram import); `routing/` + `sending/` + `hosting/` are the
aiogram-facing infrastructure.

## Component design

### Errors & Result (`errors.py`)

```python
class ErrorType(Enum):
    FAILURE; VALIDATION; NOT_FOUND; TELEGRAM_API; UNEXPECTED

@dataclass(frozen=True, slots=True)
class Error:
    code: str
    description: str
    type: ErrorType = ErrorType.FAILURE
    metadata: Mapping[str, object] | None = None   # carries e.g. retry_after for 429

# factories
def validation(code, description) -> Error
def not_found(code, description) -> Error
def unexpected(code, description) -> Error
def telegram_api(code, description, *, retry_after: int | None = None) -> Error
def failure(code, description) -> Error

# predicates
def is_validation(e) / is_not_found(e) / is_telegram_api(e) / is_unexpected(e) -> bool

# aliases
type Errors = list[Error]
type ReplyResult = Result[ReplyMessage, Errors]   # the handler return type
```

`Result`, `Ok`, `Error`(ctor) come from `expression`. To avoid the name clash between
`expression.Error` (the Result constructor) and our domain `Error`, import the expression
one under an alias (`from expression import Result, Ok, Error as Err`).

### Version & CallbackData (`models/`)

```python
class Version(IntEnum): V1 = 1; V2 = 2

@dataclass(frozen=True, slots=True)
class CallbackData:
    version: Version
    menu_id: str
    action: str
    payload: str | None = None
    SEPARATOR: ClassVar[str] = ":"
    @property
    def route_key(self) -> str            # "V1:pizza:select_size"
    def encode(self) -> str               # "V1:pizza:select_size:Large"  (payload may be "")
    @staticmethod
    def parse(data: str | None) -> Result[CallbackData, Errors]
```

`parse` mirrors the .NET logic: reject empty; split on `:`; require ≥3 parts; parse the
version (case-insensitive, accepts `V1`/`v1`/`1`); payload is the 4th part or `None`.
On failure returns `Err([errors.failure("Telegram.Routing.InvalidCallbackData", …)])`.

### Contexts (`models/context.py`)

```python
ChatId = int; UserId = int; MessageId = int

@dataclass(frozen=True, slots=True)
class MessageContext:
    user_id: UserId; chat_id: ChatId; message_id: MessageId; language_code: str | None

@dataclass(frozen=True, slots=True)
class CallbackContext:
    user_id: UserId; chat_id: ChatId; message_id: MessageId
    language_code: str | None
    payload: str | None        # decoded from the callback data (replaces the .NET `Payload` ctor arg)
```

The context is always the **first positional parameter** of a handler.

### Reply types (`models/replies/`)

Frozen dataclasses; `ReplyMessage` is their union (for typing + the sender's dispatch):

- `TextMessageReply(value: str)`
- `EditTextMessageReply(message_id: MessageId, value: str)`
- `MenuMessageReply(text: str, buttons: MenuGrid)`
- `EditMenuMessageReply(message_id: MessageId, text: str, buttons: MenuGrid)`
- `ReplyKeyboardMessageReply(text: str, keyboard: ReplyKeyboardBuilder, options: ReplyKeyboardOptions | None = None)`
- `ReplyKeyboardRemoveMessageReply(text: str = "", selective: bool = False)`

**MenuGrid / builder** (ports `MenuGrid.Builder`): methods `button(text, callback_data)`,
`new_row()`, `group_every(buttons, per_row)`; `build(configure)` applies a callable to a
fresh builder and finalizes (auto-closing the last row), matching `MenuGrid.Build(b => …)`.
Exposes `rows: tuple[tuple[MenuButton, …], …]`.

**ReplyKeyboardBuilder** (ports the C# builder): `add_button(text|button)`, `add_row(*texts)`,
`new_row()`, `clear_current_row()`, `remove_last_row()`, `clear()`. `ReplyKeyboardOptions`
= `(resize_keyboard=False, one_time_keyboard=False, selective=False, input_field_placeholder=None)`.

### Protocols (`protocols.py`)

```python
class ChatMenuButtonProvider(Protocol):
    def get_chat_menu_buttons_by_language_code(self) -> dict[str, list[BotCommand]]: ...

class ArbitraryTextMessageHandler(Protocol):
    async def handle(self, ctx: MessageContext, payload: str) -> Result[ReplyMessage, Errors]: ...

class BotErrorsProcessor(Protocol):
    async def send_errors(self, chat_id: ChatId, errors: Errors) -> None: ...
    async def send_unexpected_error(self, chat_id: ChatId) -> None: ...
```

`BotCommand` is aiogram's type (used only at the provider boundary).

### Routing (`routing/`)

**Decorators** register into a module-level default `HandlerRegistry`:

```python
@command_route("/start")
async def handle_start(ctx: MessageContext, localization: LocalizationService) -> ReplyResult: ...

@callback_route(Version.V1, "pizza", "select_size")
async def select_size(ctx: CallbackContext, localization: LocalizationService) -> ReplyResult: ...
```

`HandlerEntry` stores `(kind, key, func, signature)`. `HandlerRegistry` holds two dicts:
`commands[str] -> entry` and `callbacks[route_key] -> entry`. Duplicate keys raise at
registration time (decorator import). Lookups mirror `RoutingTypesProvider`: miss →
`Err([not_found(...)])` (`Telegram.Routing.UndefinedCommand` /
`Telegram.Routing.UndefinedCallbackRoute:{route_key}`).

**discovery** — `discover_handlers(package)` walks `pkgutil.walk_packages` and imports every
submodule so the decorators run. Replaces .NET assembly scanning. `TgDialogBot` calls it for
each feature package the consumer registers.

**Dependency injection** — for each handler the dispatcher inspects `signature.parameters`:
the first parameter receives the context; every other parameter is resolved **by name** from
the dependency map (the dispatcher's workflow data). A missing dependency raises a clear
`KeyError`-style error at dispatch. (This mirrors aiogram's by-name injection, applied to our
sub-routed handlers.)

**Dispatcher** registers exactly two aiogram handlers on the aiogram `Dispatcher`
(a `Message` handler and a `CallbackQuery` handler); aiogram injects workflow data into those.
Flow per update (ports `BotUserInputRouter` + `BotMessagesRouter` + `CallbackQueriesRouter`):

- Message: trim text; empty → `Err(EmptyMessageText)`. If it does not start with `/` → call the
  registered `ArbitraryTextMessageHandler`. Otherwise look up the command, build `MessageContext`,
  inject deps, `await` the handler.
- CallbackQuery: `CallbackData.parse(query.data)`; look up by `route_key`; build `CallbackContext`
  (with `payload`); inject deps; `await` the handler.
- On `Ok(reply)` → `ReplyMessageSender.send(chat_id, reply)`; if the send itself fails →
  `BotErrorsProcessor.send_errors`. On `Err(errors)` → `send_errors`. Any unhandled exception in
  the whole pipeline is caught, logged, and `send_unexpected_error` is attempted (mirrors the
  .NET top-level try/except). chat_id is extracted defensively from the update.

### Sending (`sending/`)

**BotMessageSender** wraps the aiogram `Bot`. Async methods returning
`Result[MessageId, Errors]`: `send_message`, `send_menu`, `send_reply_keyboard`,
`remove_reply_keyboard`, `edit_message_text`, `edit_message_menu`. Menus render via a
`MenuGrid → InlineKeyboardMarkup` mapping (callback button text + `callback_data.encode()`);
reply keyboards via `ReplyKeyboardBuilder → ReplyKeyboardMarkup` (+ options) and
`ReplyKeyboardRemove`. `parse_mode=HTML` for menus, matching the source. aiogram exceptions
are caught and converted: `TelegramRetryAfter` → `telegram_api(..., retry_after=e.retry_after)`
with code `Telegram.Api.429`; other `TelegramAPIError`/network errors → `unexpected(...)` /
`telegram_api(...)`. No technical detail leaks into the `Error.description` (security parity).

**SlidingWindowRateLimiter** — asyncio sliding-window limiter: `permit_limit =
max_messages_per_second` per 1s window, segmented (10 segments) for smoothness, with an
internal queue/lock. `await wait_for_availability()` blocks until a permit is free. When
disabled (`enable_rate_limiting=False`) it returns immediately. Tracks a `queued_count`.

**RetryService** — `execute_with_retry(operation, chat_id)`: runs the operation; on success
returns. Detects a 429 by inspecting the `Err` for an `Error` of type `TELEGRAM_API` with code
`Telegram.Api.429`. Non-429 errors return immediately (no retry). On 429, retries up to
`max_retries` with delay = `retry_after` (from `Error.metadata`) if present, else
`initial_retry_delay_ms * 2**(attempt-1)`. This improves on the .NET version, which could not
extract `Retry-After`.

**RateLimitedBotMessageSender** — decorator implementing the same interface as
`BotMessageSender`; each method does `await rate_limiter.wait_for_availability()` then runs
through `retry_service.execute_with_retry(...)`. Ports the .NET decorator 1:1.

**ReplyMessageSender** — `send(chat_id, reply)` dispatches on the reply type to the matching
`BotMessageSender` method (`EditTextMessageReply` → `edit_message_text`,
`EditMenuMessageReply` → `edit_message_menu`, `TextMessageReply` → `send_message`,
`MenuMessageReply` → `send_menu`, reply-keyboard types → their senders). Mirrors the .NET
`ReplyMessageSender` switch.

### Config (`config.py`)

```python
class BotMode(StrEnum): POLLING; WEBHOOK

class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM__", env_file=".env", extra="ignore")
    bot_token: str
    mode: BotMode = BotMode.POLLING
    max_messages_per_second: int = 30
    max_retries: int = 3
    initial_retry_delay_ms: int = 1000
    enable_rate_limiting: bool = True
    startup_max_retries: int = 5
    startup_initial_retry_delay_ms: int = 2000
    enable_startup_retries: bool = True
```

A validator ports `ValidateBotToken`: reject empty / placeholder; require `<digits>:<token>`
with the token part ≥ 30 chars.

### Hosting (`hosting/`)

**TgDialogBot** is the consumer entry point (replaces `AddTelegramBot<…>`):

```python
bot = TgDialogBot(
    settings=TelegramSettings(),
    chat_menu_button_provider=...,
    arbitrary_text_message_handler=...,
    errors_processor=...,
    dependencies={"localization": ..., "order_state": ...},   # injected by name
    handler_packages=[example.bot.features],                  # discovered at startup
)
await bot.run()
```

Construction builds the aiogram `Bot` + `Dispatcher`, wires the sender chain
(`BotMessageSender` → `RateLimitedBotMessageSender` → `ReplyMessageSender`), puts the
dependency map into the dispatcher workflow data, registers the two routing handlers, and runs
`discover_handlers` over each handler package. `run()` performs startup with retry (ports
`TryStartBotWithRetryAsync`: exponential backoff, fail-fast on 401/404, give-up after
`startup_max_retries`), sets bot commands (`commands_init`), then starts polling. Only polling
is implemented; `WEBHOOK` is accepted in config but raises `NotImplementedError` (parity — the
.NET source also only implements polling).

**commands_init** ports `TelegramBotCommandsInitService`: set the chat menu button to
"commands", then `set_my_commands` per language code from the provider, with the `en` set as the
default for unsupported languages.

## Deliberate cleanups (improving code we are porting)

1. **Drop `ReplyMessageBehavior` attribute.** In the source, `ReplyMessageSender` decides
   edit-vs-send purely from the reply type; the attribute is declared but never read there, and
   `Delete` is never implemented. The Python port encodes the action in the reply type only.
2. **Drop StronglyTypedId wrappers.** Plain `int` + semantic aliases; no friction, no codegen.
3. **Wire the contact text handlers.** In the .NET example the phone/email reply-keyboard text
   handlers exist but are never routed (the arbitrary-text handler just says "I don't
   understand"). The Python example's `ArbitraryTextMessageHandler` matches the localized
   phone/email/cancel button text and returns the proper `ReplyKeyboardRemoveMessageReply`, so
   the contact flow actually works; unknown text still falls back to the "don't understand"
   reply.
4. **Use `TelegramRetryAfter.retry_after`** in the retry path (the .NET `TryExtractRetryAfter`
   was a stub returning `null`).

## Example bot

Ports the pizza-ordering + contact example to the function-handler API, preserving the flow:
`/start` → select size → size selected → toggle topping (v1 no limit; v2 max-3 with validation)
→ confirm → place order (clears state), plus `/contact` (reply keyboard) and `/hide`. Includes
`LocalizationService` (en/ru, same `MessageKey`s and strings), in-memory `OrderState`
(dict keyed by user id), `ChatMenuButtonProvider`, and `BotErrorsProcessor` (formats validation
errors for the user; hides technical detail). `main.py` loads `TelegramSettings`, constructs
`TgDialogBot`, and runs it. `.env.example` documents `TELEGRAM__BOT_TOKEN`, etc.

## Tests

pytest suite mirroring the .NET tests, no live Telegram calls:

- **models** — `CallbackData.parse`/`encode`/`route_key` (valid, empty, too-few-parts, bad
  version, with/without payload); `MenuGrid` builder (rows, `new_row`, `group_every`,
  last-row finalization); `ReplyKeyboardBuilder` (add/new_row/clear/remove); reply dataclasses.
- **routing** — decorator registration + duplicate detection; registry lookups (hit/miss);
  dependency injection by name; dispatcher message flow (command, arbitrary text, empty),
  callback flow (valid, unparseable, unknown route), Ok→send / Err→send_errors /
  exception→send_unexpected_error — using a fake `BotMessageSender` and fakes for the protocols.
- **sending** — `SlidingWindowRateLimiter` admits within limit and throttles past it (using a
  controllable clock); `RetryService` retries only on 429, respects `retry_after`, backs off,
  and gives up after `max_retries`; `ReplyMessageSender` routes each reply type to the right
  method.
- **config** — token validation (empty / placeholder / bad format / valid); env + `.env`
  loading and defaults.

## Out of scope (parity with source)

- Webhook mode (enum value only; raises `NotImplementedError`).
- `Delete` reply behavior (never implemented in source).
- Persistence (example state is in-memory, as in the source).
- NuGet/package publishing pipeline (the Python package is `pip install`-able from source;
  publishing config is not part of this work).
```

