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
