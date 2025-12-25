"""Footer controls panel component.

This module provides a panel for footer controls including
date slider, range slider, IV controls, and marker labels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..styles import (
    AVERAGE_BUTTON_STYLE,
    DATE_SLIDER_QSS,
    IV_LABEL_STYLE,
    MARKER_LABEL_STYLE,
    RANGE_SLIDER_QSS,
    REFRESH_LABEL_STYLE,
)

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable


class FooterControlsPanel(QWidget):
    """Panel for footer controls.

    This widget contains date slider, range slider,
    IV controls, and marker labels.
    """

    # Signals
    date_changed = pyqtSignal(int)
    range_changed = pyqtSignal(int)
    iv_preset_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the footer controls panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        # Initialize instance variables (will be properly set by _setup_ui)
        self.lbl_date: QLabel = QLabel()
        self.lbl_remain: QLabel = QLabel()
        self.date_slider: QSlider = QSlider()
        self.lbl_range: QLabel = QLabel()
        self.btn_avg: QPushButton = QPushButton()
        self.lbl_iv: QLabel = QLabel()
        self.range_slider: QSlider = QSlider()
        self.m1: QLabel = QLabel()
        self.m2: QLabel = QLabel()
        self.m3: QLabel = QLabel()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(self._build_date_row())
        layout.addWidget(self._build_date_slider())
        layout.addLayout(self._build_iv_row())
        layout.addWidget(self._build_range_slider())
        layout.addLayout(self._build_markers_layout())

    def _build_date_row(self) -> QHBoxLayout:
        """Build the date row layout.

        Returns:
            Layout containing date controls.
        """
        row = QHBoxLayout()

        self.lbl_date = QLabel("DATE: <b>Now</b>")
        self.lbl_date.setStyleSheet("font-size: 12px;")

        self.lbl_remain = QLabel("(14d remaining)")
        self.lbl_remain.setStyleSheet("color: #555; font-size: 12px;")

        row.addWidget(self.lbl_date)
        row.addStretch()
        row.addWidget(self.lbl_remain)

        return row

    def _build_date_slider(self) -> QSlider:
        """Build the date slider.

        Returns:
            The date slider widget.
        """
        self.date_slider = QSlider(Qt.Orientation.Horizontal)
        self.date_slider.setStyleSheet(DATE_SLIDER_QSS)

        connect_slider: TCallable[..., object] = cast(
            "TCallable[..., object]", self.date_slider.valueChanged.connect
        )
        connect_slider(self._on_date_slider_changed)

        return self.date_slider

    def _on_date_slider_changed(self, value: int) -> None:
        """Handle date slider value change.

        Args:
            value: New slider value.
        """
        self.date_changed.emit(value)

    def _build_iv_row(self) -> QHBoxLayout:
        """Build the IV controls row.

        Returns:
            Layout containing IV controls.
        """
        row = QHBoxLayout()
        row.setContentsMargins(0, 10, 0, 0)

        self.lbl_range = QLabel("RANGE: <b>±3.6%</b>")

        lbl_refresh = QLabel("↺")
        lbl_refresh.setStyleSheet(REFRESH_LABEL_STYLE)

        row.addWidget(self.lbl_range)
        row.addStretch()
        row.addWidget(lbl_refresh)

        iv_widget = QWidget()
        iv_layout = QHBoxLayout(iv_widget)
        iv_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_avg = QPushButton("AVERAGE ▼")
        self.btn_avg.setStyleSheet(AVERAGE_BUTTON_STYLE)

        self.lbl_iv = QLabel("IMPLIED VOLATILITY: <b>18.8%</b>")
        self.lbl_iv.setStyleSheet(IV_LABEL_STYLE)

        iv_layout.addWidget(self.btn_avg)
        iv_layout.addSpacing(5)
        iv_layout.addWidget(self.lbl_iv)

        row.addSpacing(20)
        row.addWidget(iv_widget)

        return row

    def _build_range_slider(self) -> QSlider:
        """Build the range slider.

        Returns:
            The range slider widget.
        """
        self.range_slider = QSlider(Qt.Orientation.Horizontal)
        self.range_slider.setValue(30)
        self.range_slider.setStyleSheet(RANGE_SLIDER_QSS)

        connect_slider: TCallable[..., object] = cast(
            "TCallable[..., object]", self.range_slider.valueChanged.connect
        )
        connect_slider(self._on_range_slider_changed)

        return self.range_slider

    def _on_range_slider_changed(self, value: int) -> None:
        """Handle range slider value change.

        Args:
            value: New slider value.
        """
        self.range_changed.emit(value)

    def _build_markers_layout(self) -> QHBoxLayout:
        """Build the markers layout.

        Returns:
            Layout containing marker labels.
        """
        markers = QHBoxLayout()

        self.m1 = QLabel("x1")
        self.m2 = QLabel("x2")
        self.m3 = QLabel("x3")

        for m in [self.m1, self.m2, self.m3]:
            m.setStyleSheet(MARKER_LABEL_STYLE)

        markers.addWidget(self.m1)
        markers.addStretch()
        markers.addWidget(self.m2)
        markers.addStretch()
        markers.addWidget(self.m3)

        return markers

    def update_date_label(self, text: str) -> None:
        """Update the date label text.

        Args:
            text: New text for the date label.
        """
        self.lbl_date.setText(text)

    def update_remaining_label(self, text: str) -> None:
        """Update the remaining days label.

        Args:
            text: New text for the remaining label.
        """
        self.lbl_remain.setText(text)

    def update_range_label(self, text: str) -> None:
        """Update the range label text.

        Args:
            text: New text for the range label.
        """
        self.lbl_range.setText(text)

    def update_iv_label(self, text: str) -> None:
        """Update the IV label text.

        Args:
            text: New text for the IV label.
        """
        self.lbl_iv.setText(text)
