from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class OptionType(Enum):
    CALL = "CALL"
    PUT = "PUT"


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Underlier(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    spot: float
    multiplier: int
    currency: str

    @field_validator("multiplier")
    @classmethod
    def _multiplier_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("multiplier must be positive")
        return v

    @field_validator("spot")
    @classmethod
    def _spot_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("spot must be non-negative")
        return v


class OptionContract(BaseModel):
    model_config = ConfigDict(frozen=True)
    underlier: Underlier
    expiry: date
    strike: float
    type: OptionType

    @field_validator("strike")
    @classmethod
    def _strike_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("strike must be positive")
        return v


class OptionLeg(BaseModel):
    model_config = ConfigDict(frozen=True)
    contract: OptionContract
    side: Side
    quantity: int
    entry_price: float | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def _quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v

    @field_validator("entry_price")
    @classmethod
    def _entry_price_non_negative(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("entry_price must be non-negative")
        return v


class StrategyConstraints(BaseModel):
    model_config = ConfigDict(frozen=True)
    same_expiry: bool = True
    same_underlier: bool = True
    max_total_short_qty: int | None = None


class OptionQuote(BaseModel):
    model_config = ConfigDict(frozen=True)
    bid: float
    ask: float
    mid: float
    iv: float
    last_updated: datetime

    @model_validator(mode="after")
    def _validate_ranges(self) -> Self:
        if self.bid < 0 or self.ask < 0 or self.mid < 0:
            raise ValueError("quote prices must be non-negative")
        if not (self.bid <= self.mid <= self.ask):
            raise ValueError("enforce bid <= mid <= ask")
        if self.iv < 0:
            raise ValueError("iv must be non-negative")
        return self


class Strategy(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    underlier: Underlier
    legs: list[OptionLeg]
    created_at: datetime = datetime.now()
    tags: list[str] | None = None
    constraints: StrategyConstraints = StrategyConstraints()

    @model_validator(mode="after")
    def _validate_invariants(self) -> Self:
        if not self.legs:
            raise ValueError("strategy must contain at least one leg")
        if self.constraints.same_underlier:
            for leg in self.legs:
                if leg.contract.underlier.symbol != self.underlier.symbol:
                    raise ValueError("all legs must share strategy underlier")
        if self.constraints.same_expiry:
            base_exp = self.legs[0].contract.expiry
            for leg in self.legs[1:]:
                if leg.contract.expiry != base_exp:
                    raise ValueError("all legs must share same expiry")
        if self.constraints.max_total_short_qty is not None:
            total_short = sum(
                leg.quantity for leg in self.legs if leg.side is Side.SELL
            )
            if total_short > self.constraints.max_total_short_qty:
                raise ValueError("exceeds max total short quantity constraint")
        return self


class LegMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float


class AggregationGrid(BaseModel):
    model_config = ConfigDict(frozen=True)
    prices: list[float]
    pnls: list[float]


class StrategyMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    net_debit_credit: float
    max_profit: float
    max_loss: float
    break_evens: list[float]
    delta: float
    gamma: float
    theta: float
    vega: float
    margin_estimate: float
    grid: AggregationGrid | None = None


class StrategySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    strategy: Strategy
    spot: float
    quotes: Mapping[tuple[date, float, OptionType], OptionQuote]
