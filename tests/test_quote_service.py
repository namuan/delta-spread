from datetime import date

import pytest

from delta_spread.data.tradier_data import TradierOptionsDataService
from delta_spread.domain.models import (
    OptionContract,
    OptionLeg,
    OptionQuote,
    OptionType,
    Side,
    Strategy,
    Underlier,
)
from delta_spread.services.quote_service import QuoteService
from mocks.options_data_mock import MockOptionsDataService


def test_quote_service_leg_mid_and_ivs() -> None:
    svc = QuoteService(MockOptionsDataService(today=date(2025, 11, 20)))

    u = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    expiry = date(2025, 12, 15)
    contract = OptionContract(
        underlier=u,
        expiry=expiry,
        strike=6600.0,
        type=OptionType.CALL,
    )
    leg = OptionLeg(contract=contract, side=Side.BUY, quantity=1, entry_price=10.0)

    quote = svc.get_quote_for_leg(leg, symbol=u.symbol)
    assert isinstance(quote, OptionQuote)
    assert quote.bid <= quote.mid <= quote.ask

    mid = svc.get_mid_price(u.symbol, expiry, 6600.0, OptionType.CALL)
    assert mid == svc.get_quote(u.symbol, expiry, 6600.0, OptionType.CALL).mid

    strategy = Strategy(name="One", underlier=u, legs=[leg])
    ivs = svc.get_ivs_for_strategy(strategy)
    assert ivs[6600.0, OptionType.CALL] == quote.iv


def test_quote_service_stock_quote_and_option_details_routing() -> None:
    expiry = date(2025, 12, 15)

    non_tradier = QuoteService(MockOptionsDataService(today=date(2025, 11, 20)))
    assert non_tradier.get_stock_quote("SPX") is None
    assert (
        non_tradier.get_option_details("SPX", expiry, 6600.0, OptionType.CALL) is None
    )

    class FakeTradier(TradierOptionsDataService):
        def get_stock_quote(self):  # type: ignore[override]
            return {
                "last": 1.0,
                "change": 0.5,
                "change_percentage": 0.1,
                "prevclose": 0.5,
            }

        def get_option_details(self, *_args, **_kwargs):  # type: ignore[override]
            return {"bid": 1.0, "ask": 2.0, "mid": 1.5}

    tradier = QuoteService(
        FakeTradier(symbol="SPX", base_url="https://example.com", token="x")
    )

    assert tradier.get_stock_quote("SPX") == {
        "last": 1.0,
        "change": 0.5,
        "change_percentage": 0.1,
        "prevclose": 0.5,
    }

    assert tradier.get_option_details("SPX", expiry, 6600.0, OptionType.CALL) == {
        "bid": 1.0,
        "ask": 2.0,
        "mid": 1.5,
    }

    class FakeTradierError(TradierOptionsDataService):
        def get_stock_quote(self):  # type: ignore[override]
            raise ValueError("boom")

        def get_option_details(self, *_args, **_kwargs):  # type: ignore[override]
            raise TypeError("boom")

    failing = QuoteService(
        FakeTradierError(symbol="SPX", base_url="https://example.com", token="x")
    )
    assert failing.get_stock_quote("SPX") is None
    assert failing.get_option_details("SPX", expiry, 6600.0, OptionType.CALL) is None


def test_quote_service_data_service_property() -> None:
    mock1 = MockOptionsDataService(today=date(2025, 11, 20))
    mock2 = MockOptionsDataService(today=date(2025, 11, 21))
    service = QuoteService(mock1)
    assert service.data_service is mock1

    service.data_service = mock2
    assert service.data_service is mock2


def test_quote_service_get_expiries_and_strikes_are_lists() -> None:
    service = QuoteService(MockOptionsDataService(today=date(2025, 11, 20)))
    expiries = service.get_expiries()
    assert isinstance(expiries, list)

    strikes = service.get_strikes("SPX", expiries[0])
    assert isinstance(strikes, list)


def test_quote_service_get_quote_for_leg_calls_data_service() -> None:
    class RecordingDataService(MockOptionsDataService):
        def __init__(self):
            super().__init__(today=date(2025, 11, 20))
            self.calls: list[tuple[str, date, float, OptionType]] = []

        def get_quote(self, symbol: str, expiry: date, strike: float, type: OptionType):  # type: ignore[override]
            self.calls.append((symbol, expiry, strike, type))
            return super().get_quote(symbol, expiry, strike, type)

    ds = RecordingDataService()
    service = QuoteService(ds)

    u = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    expiry = date(2025, 12, 15)
    leg = OptionLeg(
        contract=OptionContract(
            underlier=u,
            expiry=expiry,
            strike=6600.0,
            type=OptionType.CALL,
        ),
        side=Side.BUY,
        quantity=1,
    )

    _quote = service.get_quote_for_leg(leg, symbol=u.symbol)

    assert ds.calls == [("SPX", expiry, 6600.0, OptionType.CALL)]


def test_quote_service_get_ivs_for_strategy_calls_data_service_for_each_leg() -> None:
    class RecordingDataService(MockOptionsDataService):
        def __init__(self):
            super().__init__(today=date(2025, 11, 20))
            self.calls: list[tuple[str, date, float, OptionType]] = []

        def get_quote(self, symbol: str, expiry: date, strike: float, type: OptionType):  # type: ignore[override]
            self.calls.append((symbol, expiry, strike, type))
            return super().get_quote(symbol, expiry, strike, type)

    ds = RecordingDataService()
    service = QuoteService(ds)

    u = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    expiry = date(2025, 12, 15)
    legs = [
        OptionLeg(
            contract=OptionContract(
                underlier=u,
                expiry=expiry,
                strike=6600.0,
                type=OptionType.CALL,
            ),
            side=Side.BUY,
            quantity=1,
        ),
        OptionLeg(
            contract=OptionContract(
                underlier=u,
                expiry=expiry,
                strike=6500.0,
                type=OptionType.PUT,
            ),
            side=Side.SELL,
            quantity=1,
        ),
    ]
    strategy = Strategy(name="Two", underlier=u, legs=legs)

    ivs = service.get_ivs_for_strategy(strategy)
    assert set(ivs.keys()) == {(6600.0, OptionType.CALL), (6500.0, OptionType.PUT)}

    assert ds.calls == [
        ("SPX", expiry, 6600.0, OptionType.CALL),
        ("SPX", expiry, 6500.0, OptionType.PUT),
    ]


def test_quote_service_get_quote_delegates() -> None:
    service = QuoteService(MockOptionsDataService(today=date(2025, 11, 20)))
    expiry = date(2025, 12, 15)
    quote = service.get_quote("SPX", expiry, 6600.0, OptionType.CALL)
    assert quote.bid <= quote.mid <= quote.ask


@pytest.mark.parametrize(
    ("symbol", "strike"),
    [
        ("SPX", 6600.0),
        ("AAPL", 170.0),
    ],
)
def test_quote_service_get_mid_price_is_non_negative(
    symbol: str, strike: float
) -> None:
    service = QuoteService(MockOptionsDataService(today=date(2025, 11, 20)))
    expiry = date(2025, 12, 15)

    mid = service.get_mid_price(symbol, expiry, strike, OptionType.CALL)
    assert mid >= 0
