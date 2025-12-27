"""Load trade dialog.

Dialog for loading a saved trade from the database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..styles import (
    BUTTON_PRIMARY_STYLE,
    COLOR_DANGER_RED,
    COLOR_GRAY_600,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from ...data.trade_repository import TradeSummary
    from ...services.trade_service import TradeServiceProtocol


class LoadTradeDialog(QDialog):
    """Dialog for loading a saved trade.

    Shows a list of saved trades with:
    - Name, symbol, leg count, dates
    - Load and Delete actions
    """

    def __init__(
        self,
        trade_service: TradeServiceProtocol,
        parent: QWidget | None = None,
        *,
        current_trade_id: int | None = None,
    ) -> None:
        """Initialize the load trade dialog.

        Args:
            trade_service: Service for loading trades.
            parent: Parent widget.
            current_trade_id: ID of the currently loaded trade (cannot be deleted).
        """
        super().__init__(parent)
        self._trade_service = trade_service
        self._current_trade_id = current_trade_id
        self._selected_trade_id: int | None = None

        self.setWindowTitle("Load Trade")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        self._setup_ui()
        self._load_trades()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        header_label = QLabel("Select a trade to load:")
        layout.addWidget(header_label)

        # Trades table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(  # pyright: ignore[reportUnknownMemberType]
            ["Name", "Symbol", "Legs", "Created", "Updated"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        vh = self._table.verticalHeader()
        if vh is not None:
            vh.setVisible(False)
        self._table.setAlternatingRowColors(True)

        # Configure column sizing
        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self._table.itemSelectionChanged.connect(  # pyright: ignore[reportUnknownMemberType]
            self._on_selection_changed
        )
        self._table.itemDoubleClicked.connect(  # pyright: ignore[reportUnknownMemberType]
            self._on_double_click
        )
        layout.addWidget(self._table)

        # Empty state label
        self._empty_label = QLabel("No saved trades found.")
        self._empty_label.setStyleSheet(f"color: {COLOR_GRAY_600}; font-size: 12px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        # Button row
        button_layout = QHBoxLayout()

        # Delete button
        self._delete_button = QPushButton("Delete")
        self._delete_button.setStyleSheet(f"color: {COLOR_DANGER_RED};")
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(  # pyright: ignore[reportUnknownMemberType]
            self._on_delete
        )
        button_layout.addWidget(self._delete_button)

        button_layout.addStretch()

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open
            | QDialogButtonBox.StandardButton.Cancel
        )
        open_button = button_box.button(QDialogButtonBox.StandardButton.Open)
        if open_button:
            open_button.setStyleSheet(BUTTON_PRIMARY_STYLE)
            open_button.setEnabled(False)
            self._open_button = open_button

        button_box.accepted.connect(  # pyright: ignore[reportUnknownMemberType]
            self._on_load
        )
        button_box.rejected.connect(  # pyright: ignore[reportUnknownMemberType]
            self.reject
        )
        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

    def _load_trades(self) -> None:
        """Load trades from the service into the table."""
        trades = self._trade_service.get_saved_trades()
        self._table.setRowCount(len(trades))

        if not trades:
            self._table.hide()
            self._empty_label.show()
            return

        self._empty_label.hide()
        self._table.show()

        for row, trade in enumerate(trades):
            self._populate_row(row, trade)

    def _populate_row(self, row: int, trade: TradeSummary) -> None:
        """Populate a table row with trade data.

        Args:
            row: Row index.
            trade: Trade summary to display.
        """
        # Store trade ID in first column
        name_item = QTableWidgetItem(trade.name)
        name_item.setData(Qt.ItemDataRole.UserRole, trade.id)
        self._table.setItem(row, 0, name_item)

        self._table.setItem(row, 1, QTableWidgetItem(trade.underlier_symbol))
        self._table.setItem(row, 2, QTableWidgetItem(str(trade.leg_count)))
        self._table.setItem(
            row, 3, QTableWidgetItem(trade.created_at.strftime("%Y-%m-%d %H:%M"))
        )
        self._table.setItem(
            row, 4, QTableWidgetItem(trade.updated_at.strftime("%Y-%m-%d %H:%M"))
        )

    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        selected_rows = self._table.selectedItems()
        has_selection = len(selected_rows) > 0

        self._open_button.setEnabled(has_selection)

        if has_selection:
            row = self._table.currentRow()
            name_item = self._table.item(row, 0)
            if name_item:
                self._selected_trade_id = name_item.data(Qt.ItemDataRole.UserRole)
                # Disable delete if this is the currently loaded trade
                is_current = self._selected_trade_id == self._current_trade_id
                self._delete_button.setEnabled(not is_current)
            else:
                self._delete_button.setEnabled(False)
        else:
            self._selected_trade_id = None
            self._delete_button.setEnabled(False)

    def _on_double_click(self, item: QTableWidgetItem) -> None:
        """Handle double-click on a row.

        Args:
            item: Clicked item (unused, double-click loads the row).
        """
        _ = item  # Unused, double-click loads regardless of column
        self._on_load()

    def _on_load(self) -> None:
        """Handle load button click."""
        if self._selected_trade_id is not None:
            self.accept()

    def _on_delete(self) -> None:
        """Handle delete button click."""
        if self._selected_trade_id is None:
            return

        # Get trade name for confirmation
        row = self._table.currentRow()
        name_item = self._table.item(row, 0)
        trade_name = name_item.text() if name_item else "this trade"

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Trade",
            f"Are you sure you want to delete '{trade_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._trade_service.delete_trade(self._selected_trade_id)
            self._selected_trade_id = None
            self._load_trades()

    def get_selected_trade_id(self) -> int | None:
        """Get the ID of the selected trade.

        Returns:
            The database ID of the selected trade, or None if none selected.
        """
        return self._selected_trade_id
