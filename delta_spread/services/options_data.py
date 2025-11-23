from collections.abc import Iterable
from datetime import date
from typing import Protocol


class OptionsDataService(Protocol):
    def get_expiries(self) -> Iterable[date]: ...

    def get_strikes(self, symbol: str, expiry: date) -> Iterable[float]: ...
