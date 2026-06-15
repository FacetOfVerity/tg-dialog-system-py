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
