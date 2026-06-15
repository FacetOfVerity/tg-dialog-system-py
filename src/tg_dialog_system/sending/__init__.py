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
