"""UI panels package.

This package contains reusable panel components for the main window.
"""

from .footer_controls_panel import FooterControlsPanel
from .instrument_info_panel import InstrumentInfoPanel
from .metrics_panel import MetricsPanel
from .strikes_panel import StrikesPanel

__all__ = [
    "FooterControlsPanel",
    "InstrumentInfoPanel",
    "MetricsPanel",
    "StrikesPanel",
]
