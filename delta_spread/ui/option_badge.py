from typing import override

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPaintEvent
from PyQt6.QtWidgets import QWidget

from .styles import COLOR_TEXT_PRIMARY


class OptionBadge(QWidget):
    def __init__(
        self,
        text: str,
        color_bg: str,
        *,
        is_call: bool = False,
        pointer_up: bool = False,
    ) -> None:
        super().__init__()
        self.text = text
        self.color_bg = color_bg
        self.is_call = is_call
        self.pointer_up = pointer_up
        self.setFixedSize(50, 25)

    @override
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        if self.pointer_up:
            path.addRoundedRect(0, 5, self.width(), self.height() - 5, 3, 3)
            path.moveTo(self.width() / 2 - 5, 5)
            path.lineTo(self.width() / 2, 0)
            path.lineTo(self.width() / 2 + 5, 5)
        else:
            path.addRoundedRect(0, 0, self.width(), self.height() - 5, 3, 3)
            path.moveTo(self.width() / 2 - 5, self.height() - 5)
            path.lineTo(self.width() / 2, self.height())
            path.lineTo(self.width() / 2 + 5, self.height() - 5)
        painter.fillPath(path, QColor(self.color_bg))
        painter.setPen(
            QColor(COLOR_TEXT_PRIMARY) if self.pointer_up else Qt.GlobalColor.white
        )
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        tgt_rect = (
            self.rect().adjusted(0, 5, 0, 0)
            if self.pointer_up
            else self.rect().adjusted(0, 0, 0, -5)
        )
        painter.drawText(tgt_rect, Qt.AlignmentFlag.AlignCenter, self.text)
