"""Configuration dialog for application settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable

    from ..config import AppConfig


class ConfigDialog(QDialog):
    """Modal dialog for editing application configuration."""

    def __init__(self, config: AppConfig, parent: object = None) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(400)
        self._config = config
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._use_real_data_cb = QCheckBox()
        self._use_real_data_cb.setChecked(self._config.use_real_data)
        form.addRow("Use Real Data:", self._use_real_data_cb)

        self._base_url_edit = QLineEdit(self._config.tradier_base_url)
        self._base_url_edit.setPlaceholderText("https://api.tradier.com")
        self._base_url_edit.setMinimumWidth(300)
        form.addRow("Tradier Base URL:", self._base_url_edit)

        self._token_edit = QLineEdit(self._config.tradier_token)
        self._token_edit.setPlaceholderText("Enter your Tradier API token")
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setMinimumWidth(300)
        form.addRow("Tradier Token:", self._token_edit)

        self._max_expiries_spin = QSpinBox()
        self._max_expiries_spin.setMinimum(1)
        self._max_expiries_spin.setMaximum(365)
        self._max_expiries_spin.setValue(self._config.max_expiries)
        self._max_expiries_spin.setToolTip(
            "Maximum number of expiration dates to display"
        )
        form.addRow("Max Expiries:", self._max_expiries_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        connect_accept: TCallable[..., object] = cast(
            "TCallable[..., object]", buttons.accepted.connect
        )
        connect_accept(self._on_accept)
        connect_reject: TCallable[..., object] = cast(
            "TCallable[..., object]", buttons.rejected.connect
        )
        connect_reject(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        self._config.use_real_data = self._use_real_data_cb.isChecked()
        self._config.tradier_base_url = self._base_url_edit.text().strip()
        self._config.tradier_token = self._token_edit.text()
        self._config.max_expiries = self._max_expiries_spin.value()
        self._config.save()
        self.accept()

    def get_config(self) -> AppConfig:
        """Return the (possibly updated) configuration."""
        return self._config
