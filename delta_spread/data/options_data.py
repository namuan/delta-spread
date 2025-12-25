"""Contracts for fetching option market data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import date

    from delta_spread.domain.models import OptionQuote, OptionType


class OptionsDataService(Protocol):
    def get_expiries(self) -> list[date]: ...

    def get_strikes(self, symbol: str, expiry: date) -> list[float]: ...

    def get_chain(self, symbol: str, expiry: date) -> list[OptionQuote]: ...

    def get_quote(
        self, symbol: str, expiry: date, strike: float, type: OptionType
    ) -> OptionQuote: ...
