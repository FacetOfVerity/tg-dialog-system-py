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
        MessageKey.EMAIL_CONTACT_RESPONSE: "Email: support@pizzabot.example.com\n\nReply within 24h.",  # noqa: E501
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
        MessageKey.ORDER_CONFIRMATION: "Your order:\n• Size: {0}\n• Toppings: {1}\n\nTotal: ${2}\n\nConfirm?",  # noqa: E501
        MessageKey.ORDER_SUCCESS: "Order placed successfully! 🎉\n\nReady in 20 minutes.",
        MessageKey.NEW_ORDER_BUTTON: "Order Another Pizza",
        MessageKey.ERROR_TOO_MANY_TOPPINGS: "You can select maximum 3 toppings!",
        MessageKey.NO_TOPPINGS: "No toppings",
    },
    "ru": {
        MessageKey.WELCOME: "Добро пожаловать в Pizza Bot! 🍕\n\nНажмите кнопку ниже, чтобы начать заказ.",  # noqa: E501
        MessageKey.ORDER_BUTTON: "Заказать пиццу",
        MessageKey.CONTACT_MESSAGE: "Как вы хотите связаться с нами?\n\nВыберите вариант ниже:",
        MessageKey.PHONE_BUTTON: "📞 Телефон",
        MessageKey.EMAIL_BUTTON: "📧 Email",
        MessageKey.CANCEL_BUTTON: "❌ Отмена",
        MessageKey.KEYBOARD_REMOVED: "Клавиатура скрыта. Используйте /contact для отображения.",
        MessageKey.PHONE_CONTACT_RESPONSE: "Телефон: +7 (495) 123-45-67\n\nПоддержка: 9-18 МСК.",
        MessageKey.EMAIL_CONTACT_RESPONSE: "Email: support@pizzabot.example.ru\n\nОтветим в течение 24 часов.",  # noqa: E501
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
        MessageKey.ORDER_CONFIRMATION: "Ваш заказ:\n• Размер: {0}\n• Топпинги: {1}\n\nИтого: ${2}\n\nПодтвердить?",  # noqa: E501
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
