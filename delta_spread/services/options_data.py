from datetime import date
from typing import Protocol

from ..domain.models import OptionQuote, OptionType


class OptionsDataService(Protocol):
    def get_expiries(self) -> list[date]: ...

    def get_strikes(self, symbol: str, expiry: date) -> list[float]: ...

    def get_chain(self, symbol: str, expiry: date) -> list[OptionQuote]: ...

    def get_quote(
        self, symbol: str, expiry: date, strike: float, type: OptionType
    ) -> OptionQuote: ...
