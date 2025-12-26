"""Tests for Tradier options data service."""

from datetime import date
from unittest.mock import MagicMock, patch

from dotmap import DotMap
import pytest
import requests

from delta_spread.data.tradier_data import TradierOptionsDataService


@pytest.fixture
def mock_tradier_service():
    """Create a Tradier service with mocked requests."""
    return TradierOptionsDataService(
        symbol="SPY",
        base_url="https://api.tradier.com",
        token="test-token",
    )


@pytest.fixture
def mock_expirations_response():
    """Mock response for expirations endpoint."""
    return DotMap({"expirations": {"date": ["2025-12-31", "2026-01-15", "2026-01-30"]}})


@pytest.fixture
def mock_chain_response():
    """Mock response for options chain endpoint."""
    return DotMap({
        "options": {
            "option": [
                {
                    "symbol": "SPY251231C00600000",
                    "strike": 600.0,
                    "option_type": "call",
                    "bid": 5.50,
                    "ask": 5.60,
                    "greeks": {"mid_iv": 0.18},
                },
                {
                    "symbol": "SPY251231P00600000",
                    "strike": 600.0,
                    "option_type": "put",
                    "bid": 4.30,
                    "ask": 4.40,
                    "greeks": {"mid_iv": 0.19},
                },
            ]
        }
    })


class TestTradierOptionsDataService:
    """Test suite for Tradier options data service."""

    @staticmethod
    def test_initialization(mock_tradier_service):
        """Test service initializes correctly."""
        assert mock_tradier_service.symbol == "SPY"
        assert mock_tradier_service.base_url == "https://api.tradier.com"
        assert mock_tradier_service.token == "test-token"  # noqa: S105
        assert mock_tradier_service._expiries_cache is None
        assert mock_tradier_service._chain_cache == {}

    @staticmethod
    @patch("delta_spread.data.tradier_data.requests.get")
    def test_get_expiries(mock_get, mock_tradier_service, mock_expirations_response):
        """Test fetching expiration dates."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_expirations_response.toDict()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        expiries = mock_tradier_service.get_expiries()

        assert len(expiries) == 3
        assert all(isinstance(exp, date) for exp in expiries)
        assert expiries[0] == date(2025, 12, 31)
        assert expiries[1] == date(2026, 1, 15)
        assert expiries[2] == date(2026, 1, 30)

    @staticmethod
    @patch("delta_spread.data.tradier_data.requests.get")
    def test_get_expiries_caching(
        mock_get, mock_tradier_service, mock_expirations_response
    ):
        """Test that expiries are cached."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_expirations_response.toDict()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # First call
        expiries1 = mock_tradier_service.get_expiries()
        # Second call should use cache
        expiries2 = mock_tradier_service.get_expiries()

        assert expiries1 == expiries2
        # Should only call API once
        assert mock_get.call_count == 1

    @staticmethod
    @patch("delta_spread.data.tradier_data.requests.get")
    def test_get_chain(mock_get, mock_tradier_service, mock_chain_response):
        """Test fetching option chain."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_chain_response.toDict()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        expiry = date(2025, 12, 31)
        chain = mock_tradier_service.get_chain("SPY", expiry)

        assert len(chain) == 2
        assert all(hasattr(quote, "bid") for quote in chain)
        assert all(hasattr(quote, "ask") for quote in chain)
        assert all(hasattr(quote, "iv") for quote in chain)

    @staticmethod
    @patch("delta_spread.data.tradier_data.requests.get")
    def test_parse_option_quote(_mock_get, mock_tradier_service):
        """Test parsing option quote from raw data."""
        option_data = DotMap({
            "symbol": "SPY251231C00600000",
            "strike": 600.0,
            "option_type": "call",
            "bid": 5.50,
            "ask": 5.60,
            "greeks": {"mid_iv": 0.18},
        })

        quote = mock_tradier_service._parse_option_quote(option_data)

        assert quote is not None
        assert quote.bid == 5.50
        assert quote.ask == 5.60
        assert quote.mid == 5.55
        assert quote.iv == 0.18

    @staticmethod
    def test_extract_strike_from_symbol():
        """Test extracting strike from option symbol."""
        # SPY Jan 17, 2025 $600 Call = SPY250117C00600000
        strike = TradierOptionsDataService._extract_strike_from_symbol(
            "SPY250117C00600000"
        )
        assert strike == 600.0

        # SPY Jan 17, 2025 $595.50 Put = SPY250117P00595500
        strike = TradierOptionsDataService._extract_strike_from_symbol(
            "SPY250117P00595500"
        )
        assert strike == 595.5

    @staticmethod
    @patch("delta_spread.data.tradier_data.requests.get")
    def test_api_error_handling(mock_get, mock_tradier_service):
        """Test handling of API errors."""
        mock_get.side_effect = requests.RequestException("API Error")

        expiries = mock_tradier_service.get_expiries()

        # Should return empty list on error
        assert expiries == []

    @staticmethod
    @patch("delta_spread.data.tradier_data.requests.get")
    def test_empty_response_handling(mock_get, mock_tradier_service):
        """Test handling of empty API responses."""
        mock_response = MagicMock()
        mock_response.json.return_value = DotMap({"expirations": None})
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        expiries = mock_tradier_service.get_expiries()

        assert expiries == []
