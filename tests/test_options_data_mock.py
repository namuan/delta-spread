from datetime import date

from delta_spread.domain.models import OptionType
from mocks.options_data_mock import MockOptionsDataService


def test_mock_service_chain_and_quote() -> None:
    svc = MockOptionsDataService(today=date(2025, 11, 20))
    exps = svc.get_expiries()
    assert len(exps) >= 1
    expiry = exps[0]
    strikes = svc.get_strikes("SPX", expiry)
    assert strikes[0] == 6100.0
    assert strikes[-1] == 7100.0
    assert len(strikes) == 101
    assert all(
        round(strikes[i + 1] - strikes[i], 2) == 10.0 for i in range(len(strikes) - 1)
    )
    quotes = svc.get_chain("SPX", expiry)
    assert len(quotes) == len(strikes) * 2
    q = svc.get_quote("SPX", expiry, strikes[0], OptionType.CALL)
    assert q.bid <= q.mid <= q.ask
