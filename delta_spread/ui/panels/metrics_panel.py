"""Metrics panel component.

This module provides a panel for displaying strategy metrics
including primary metrics (net debit, max loss/profit, etc.)
and Greeks (delta, theta, gamma, vega, rho).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..styles import (
    COLOR_DANGER_RED,
    COLOR_GRAY_900,
    COLOR_SUCCESS_GREEN,
    METRIC_ICON_STYLE,
    METRIC_SUBTEXT_STYLE,
    METRIC_TITLE_STYLE,
)

if TYPE_CHECKING:
    from ...domain.models import StrategyMetrics
    from ...services.presenter import PanelMetrics


class MetricsPanel(QWidget):
    """Panel for displaying strategy metrics and Greeks.

    This widget displays primary metrics (net debit/credit, max loss,
    max profit, probability of profit, breakevens) and Greek values
    (delta, theta, gamma, vega, rho).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the metrics panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        # Initialize instance variables (will be properly set by _setup_ui)
        self.metric_net_lbl: QLabel = QLabel()
        self.metric_max_loss_lbl: QLabel = QLabel()
        self.metric_max_profit_lbl: QLabel = QLabel()
        self.metric_pop_lbl: QLabel = QLabel()
        self.metric_breakevens_lbl: QLabel = QLabel()
        self.metric_delta_lbl: QLabel = QLabel()
        self.metric_theta_lbl: QLabel = QLabel()
        self.metric_gamma_lbl: QLabel = QLabel()
        self.metric_vega_lbl: QLabel = QLabel()
        self.metric_rho_lbl: QLabel = QLabel()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        primary = self._build_primary_metrics_row()
        greeks = self._build_greeks_row()

        layout.addWidget(primary)
        layout.addWidget(greeks)

    def _build_primary_metrics_row(self) -> QWidget:
        """Build the primary metrics row.

        Returns:
            Widget containing the primary metrics.
        """
        metrics_frame = QFrame()
        layout = QHBoxLayout(metrics_frame)
        layout.setContentsMargins(10, 10, 10, 10)

        m1, m1_lbl = self._create_metric("NET DEBIT:", "$0", "#000", "🪙")
        m2, m2_lbl = self._create_metric("MAX LOSS:", "$0", "#000", "↘")
        m3, m3_lbl = self._create_metric("MAX PROFIT:", "$0", "#22C55E", "↗")
        m4, m4_lbl = self._create_metric("CHANCE OF PROFIT:", "-", "#000", "🎲")
        m5, m5_lbl = self._create_metric("BREAKEVENS:", "-", "#000", "→")

        self.metric_net_lbl = m1_lbl
        self.metric_max_loss_lbl = m2_lbl
        self.metric_max_profit_lbl = m3_lbl
        self.metric_pop_lbl = m4_lbl
        self.metric_breakevens_lbl = m5_lbl

        layout.addWidget(m1)
        layout.addWidget(m2)
        layout.addWidget(m3)
        layout.addWidget(m4)
        layout.addWidget(m5)
        layout.addStretch()

        return metrics_frame

    def _build_greeks_row(self) -> QWidget:
        """Build the Greeks metrics row.

        Returns:
            Widget containing the Greeks metrics.
        """
        greeks_frame = QFrame()
        g_layout = QHBoxLayout(greeks_frame)
        g_layout.setContentsMargins(10, 0, 10, 10)

        g1, g1_lbl = self._create_metric("DELTA:", "-", "#000", "Δ")
        g2, g2_lbl = self._create_metric("THETA:", "-", "#000", "Θ")
        g3, g3_lbl = self._create_metric("GAMMA:", "-", "#000", "Γ")
        g4, g4_lbl = self._create_metric("VEGA:", "-", "#000", "V")
        g5, g5_lbl = self._create_metric("RHO:", "-", "#000", "R")

        self.metric_delta_lbl = g1_lbl
        self.metric_theta_lbl = g2_lbl
        self.metric_gamma_lbl = g3_lbl
        self.metric_vega_lbl = g4_lbl
        self.metric_rho_lbl = g5_lbl

        g_layout.addWidget(g1)
        g_layout.addWidget(g2)
        g_layout.addWidget(g3)
        g_layout.addWidget(g4)
        g_layout.addWidget(g5)
        g_layout.addStretch()

        return greeks_frame

    @staticmethod
    def _create_metric(
        title: str,
        value: str,
        value_color: str,
        icon_char: str | None = None,
        subtext: str | None = None,
    ) -> tuple[QWidget, QLabel]:
        """Create a metric display widget.

        Args:
            title: Metric title text.
            value: Initial value text.
            value_color: Color for the value text.
            icon_char: Optional icon character.
            subtext: Optional subtext below the value.

        Returns:
            Tuple of (container widget, value label).
        """
        v_layout = QVBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(METRIC_TITLE_STYLE)

        val_layout = QHBoxLayout()
        if icon_char:
            icon = QLabel(icon_char)
            icon.setStyleSheet(METRIC_ICON_STYLE)
            val_layout.addWidget(icon)

        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(
            f"color: {value_color}; font-size: 14px; font-weight: bold;"
        )
        val_layout.addWidget(v_lbl)
        val_layout.addStretch()

        v_layout.addWidget(t_lbl)
        v_layout.addLayout(val_layout)

        if subtext:
            s_lbl = QLabel(subtext)
            s_lbl.setStyleSheet(METRIC_SUBTEXT_STYLE)
            v_layout.addWidget(s_lbl)

        container = QWidget()
        container.setLayout(v_layout)
        return container, v_lbl

    def update_metrics(self, prepared: PanelMetrics) -> None:
        """Update all metric displays with prepared metrics.

        Args:
            prepared: Prepared metrics data from MetricsPresenter.
        """
        self.metric_net_lbl.setText(prepared.net_text)
        self.metric_max_loss_lbl.setText(prepared.max_loss_text)
        self.metric_max_profit_lbl.setText(prepared.max_profit_text)
        self.metric_pop_lbl.setText(prepared.pop_text)
        self.metric_breakevens_lbl.setText(prepared.breakevens_text)

    def update_greeks(self, metrics: StrategyMetrics, prepared: PanelMetrics) -> None:
        """Update Greek metric displays.

        Args:
            metrics: Raw strategy metrics.
            prepared: Prepared metrics data from MetricsPresenter.
        """
        # Delta
        self.metric_delta_lbl.setText(prepared.delta_text)
        self.metric_delta_lbl.setStyleSheet(
            f"color: {COLOR_SUCCESS_GREEN if metrics.delta >= 0 else COLOR_DANGER_RED}; "
            + "font-size: 14px; font-weight: bold;"
        )

        # Theta
        self.metric_theta_lbl.setText(prepared.theta_text)
        self.metric_theta_lbl.setStyleSheet(
            f"color: {COLOR_SUCCESS_GREEN if metrics.theta >= 0 else COLOR_DANGER_RED}; "
            + "font-size: 14px; font-weight: bold;"
        )

        # Gamma
        self.metric_gamma_lbl.setText(prepared.gamma_text)
        self.metric_gamma_lbl.setStyleSheet(
            f"color: {COLOR_SUCCESS_GREEN if metrics.gamma >= 0 else COLOR_DANGER_RED}; "
            + "font-size: 14px; font-weight: bold;"
        )

        # Vega
        self.metric_vega_lbl.setText(prepared.vega_text)
        self.metric_vega_lbl.setStyleSheet(
            f"color: {COLOR_SUCCESS_GREEN if metrics.vega >= 0 else COLOR_DANGER_RED}; "
            + "font-size: 14px; font-weight: bold;"
        )

        # Rho
        self.metric_rho_lbl.setText(prepared.rho_text)
        self.metric_rho_lbl.setStyleSheet(
            f"color: {COLOR_GRAY_900}; font-size: 14px; font-weight: bold;"
        )

    def clear_metrics(self) -> None:
        """Clear all metric displays to default values."""
        for lbl, val in [
            (self.metric_net_lbl, "$0"),
            (self.metric_max_loss_lbl, "$0"),
            (self.metric_max_profit_lbl, "$0"),
            (self.metric_pop_lbl, "-"),
            (self.metric_breakevens_lbl, "-"),
            (self.metric_delta_lbl, "-"),
            (self.metric_theta_lbl, "-"),
            (self.metric_gamma_lbl, "-"),
            (self.metric_vega_lbl, "-"),
            (self.metric_rho_lbl, "-"),
        ]:
            if lbl:
                lbl.setText(val)
