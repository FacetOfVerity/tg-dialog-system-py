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
