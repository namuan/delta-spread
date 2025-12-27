"""Save trade dialog.

Dialog for saving the current positions as a named trade.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..styles import (
    BUTTON_PRIMARY_STYLE,
    COLOR_DANGER_RED,
    COLOR_GRAY_600,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from ...domain.models import Strategy
    from ...services.trade_service import TradeServiceProtocol

_MAX_NAME_LENGTH = 100


class SaveTradeDialog(QDialog):
    """Dialog for saving the current positions as a trade.

    Allows user to:
    - Enter trade name
    - Add optional notes
    - Confirm or cancel save
    """

    def __init__(
        self,
        trade: Strategy,
        trade_service: TradeServiceProtocol,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the save trade dialog.

        Args:
            trade: The strategy/positions to save.
            trade_service: Service for checking name uniqueness.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._trade = trade
        self._trade_service = trade_service

        self.setWindowTitle("Save Trade")
        self.setMinimumWidth(400)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Trade summary
        summary_label = QLabel(
            f"<b>{self._trade.underlier.symbol}</b> - {len(self._trade.legs)} leg(s)"
        )
        layout.addWidget(summary_label)

        # Form layout for inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        # Name input
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter trade name...")
        self._name_input.setText(self._trade.name)
        self._name_input.selectAll()
        self._name_input.textChanged.connect(  # pyright: ignore[reportUnknownMemberType]
            self._validate_name
        )
        form_layout.addRow("Name:", self._name_input)

        # Name validation label
        self._name_error = QLabel()
        self._name_error.setStyleSheet(f"color: {COLOR_DANGER_RED}; font-size: 11px;")
        self._name_error.hide()
        form_layout.addRow("", self._name_error)

        # Notes input
        self._notes_input = QPlainTextEdit()
        self._notes_input.setPlaceholderText("Optional notes about this trade...")
        self._notes_input.setMaximumHeight(80)
        form_layout.addRow("Notes:", self._notes_input)

        layout.addLayout(form_layout)

        # Legs summary
        legs_label = QLabel(self._format_legs_summary())
        legs_label.setStyleSheet(f"color: {COLOR_GRAY_600}; font-size: 11px;")
        legs_label.setWordWrap(True)
        layout.addWidget(legs_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_button:
            save_button.setStyleSheet(BUTTON_PRIMARY_STYLE)
            self._save_button = save_button

        button_box.accepted.connect(  # pyright: ignore[reportUnknownMemberType]
            self._on_save
        )
        button_box.rejected.connect(  # pyright: ignore[reportUnknownMemberType]
            self.reject
        )
        layout.addWidget(button_box)

        # Initial validation
        self._validate_name()

    def _format_legs_summary(self) -> str:
        """Format a summary of the trade legs."""
        parts: list[str] = []
        for leg in self._trade.legs:
            side = leg.side.value
            opt_type = leg.contract.type.value
            strike = leg.contract.strike
            expiry = leg.contract.expiry.strftime("%b %d")
            parts.append(f"{side} {leg.quantity}x {strike} {opt_type} ({expiry})")
        return " | ".join(parts)

    def _validate_name(self) -> None:
        """Validate the trade name."""
        name = self._name_input.text().strip()

        if not name:
            self._name_error.setText("Name is required")
            self._name_error.show()
            self._save_button.setEnabled(False)
            return

        if len(name) > _MAX_NAME_LENGTH:
            self._name_error.setText(
                f"Name must be {_MAX_NAME_LENGTH} characters or less"
            )
            self._name_error.show()
            self._save_button.setEnabled(False)
            return

        if self._trade_service.trade_name_exists(name):
            self._name_error.setText("A trade with this name already exists")
            self._name_error.show()
            self._save_button.setEnabled(False)
            return

        self._name_error.hide()
        self._save_button.setEnabled(True)

    def _on_save(self) -> None:
        """Handle save button click."""
        name = self._name_input.text().strip()
        if not name:
            return
        self.accept()

    def get_save_data(self) -> tuple[str, str | None]:
        """Get the name and notes entered by user.

        Returns:
            Tuple of (name, notes). Notes may be None if empty.
        """
        name = self._name_input.text().strip()
        notes = self._notes_input.toPlainText().strip() or None
        return name, notes
