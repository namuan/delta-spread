from collections.abc import Callable
from typing import cast

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMenu, QWidget, QWidgetAction

from ..styles import MENU_ROW_HOVER_STYLE, MENU_STYLE


def build_add_menu(parent: QWidget, on_add_option: Callable[[str], None]) -> QMenu:
    menu = QMenu(parent)
    menu.setStyleSheet(MENU_STYLE)
    header_action = QWidgetAction(parent)
    header_label = QLabel("Options:")
    header_label.setStyleSheet("color: #666; font-weight: bold; padding: 6px 12px;")
    header_action.setDefaultWidget(header_label)
    actions: list[QWidgetAction] = [header_action]

    def make_row(left: str, right: str, color: str, key: str) -> QWidgetAction:
        w = QWidget()
        row_layout = QHBoxLayout(w)
        row_layout.setContentsMargins(12, 6, 12, 6)
        a = QLabel(left)
        a.setStyleSheet("color: #333; font-size: 12px;")
        b = QLabel(right)
        b.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        row_layout.addWidget(a)
        row_layout.addSpacing(8)
        row_layout.addWidget(b)
        w.setStyleSheet(MENU_ROW_HOVER_STYLE)
        act = QWidgetAction(parent)
        act.setDefaultWidget(w)

        def handler() -> None:
            on_add_option(key)
            menu.close()

        def on_release(a0: object | None) -> None:
            _ = a0
            handler()

        w.mouseReleaseEvent = on_release
        return act

    actions.append(make_row("Buy", "Call", "#16A34A", "buy_call"))
    actions.append(make_row("Sell", "Call", "#16A34A", "sell_call"))
    actions.append(make_row("Buy", "Put", "#DC2626", "buy_put"))
    actions.append(make_row("Sell", "Put", "#DC2626", "sell_put"))
    add_act = cast("Callable[[QWidgetAction | None], None]", menu.addAction)
    for a in actions:
        add_act(a)
    return menu
