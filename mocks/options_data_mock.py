from datetime import date, datetime, timedelta
import hashlib

from delta_spread.domain.models import OptionQuote, OptionType


class MockOptionsDataService:
    def __init__(self, today: date | None = None) -> None:
        super().__init__()
        self._today = today or date.today()

    def get_expiries(self) -> list[date]:
        base = self._today
        target = 4
        offset = (target - base.weekday()) % 7
        if offset == 0:
            offset = 7
        first = base + timedelta(days=offset)
        return [first + timedelta(days=7 * i) for i in range(6)]

    @staticmethod
    def get_strikes(symbol: str, expiry: date) -> list[float]:
        strike_base_low_threshold = 100
        strike_base_medium_threshold = 200
        seed_bytes = hashlib.sha256(f"{symbol}|{expiry.isoformat()}".encode()).digest()
        seed = int.from_bytes(seed_bytes[:4], "big")
        base = 50 + (seed % 250)
        if base < strike_base_low_threshold:
            step = 1
        elif base < strike_base_medium_threshold:
            step = 5
        else:
            step = 10
        count = 11
        mid = count // 2
        return [round(base + (i - mid) * step, 2) for i in range(count)]

    def get_chain(self, symbol: str, expiry: date) -> list[OptionQuote]:
        strikes = self.get_strikes(symbol, expiry)
        return [
            self.get_quote(symbol, expiry, s, t)
            for t in (OptionType.CALL, OptionType.PUT)
            for s in strikes
        ]

    @staticmethod
    def get_quote(
        symbol: str, expiry: date, strike: float, type: OptionType
    ) -> OptionQuote:
        seed_bytes = hashlib.sha256(
            f"{symbol}|{expiry.isoformat()}|{strike:.2f}|{type.value}".encode()
        ).digest()
        seed = int.from_bytes(seed_bytes[:4], "big")
        base = (seed % 1000) / 100.0
        spread = 0.2 + ((seed >> 8) % 50) / 100.0
        bid = max(base - spread / 2, 0.0)
        ask = base + spread / 2
        mid = round((bid + ask) / 2, 2)
        iv = round(0.1 + ((seed >> 16) % 200) / 1000.0, 4)
        return OptionQuote(
            bid=round(bid, 2),
            ask=round(ask, 2),
            mid=mid,
            iv=iv,
            last_updated=datetime.now(),
        )
