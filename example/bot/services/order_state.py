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
