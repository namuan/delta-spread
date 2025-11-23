from __future__ import annotations

from datetime import date, timedelta
import hashlib


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
