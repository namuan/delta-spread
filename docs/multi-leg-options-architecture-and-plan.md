# Multi‑Leg Options Strategy Data Model — Architecture & Plan

## Overview
- Build strict, composable domain models to represent multi‑leg options strategies (calls/puts across strikes and expiries) for a single underlying.
- Use Pydantic v2 for validation/serialization, enums for canonical types, and keep pricing logic behind interfaces for testability and separation of concerns.
- Integrate with existing UI for expiries/strikes and the Add menu to create legs, aggregate metrics for display, and feed chart curves.

## Scope & Assumptions
- Underlier focus: single symbol per strategy; multi‑underlier portfolios are out of scope.
- Expiry policy: start with “same expiry per strategy” then allow mixed expiries via constraints.
- Pricing: phase 1 uses a mock pricing service; real‑time quotes can replace it later.
- UI: wire new models into `MainWindow` and existing widgets without large UI redesign.

## Current Integration Points
- Expiries and strikes come from `OptionsDataService` (`delta_spread/services/options_data.py:6-9`).
- Mock expiries/strikes via `MockOptionsDataService` (`delta_spread/services/options_data_mock.py:11-18`, `21-35`).
- Add menu emits intent keys in `build_add_menu` (`delta_spread/ui/menus/add_menu.py:39-42`).
- `MainWindow.on_add_option` is the hook to create legs (`delta_spread/ui/main_window.py:282`).
- Metrics placeholders exist in `MainWindow.setup_metrics` (`delta_spread/ui/main_window.py:216-263`).
- Chart draws placeholder P&L curves (`delta_spread/ui/chart_widget.py:21-31`).
- Strike ruler renders strike ticks (`delta_spread/ui/strike_ruler.py:11-14`, `15-35`).

## Domain Model
- Underlier: `symbol`, `spot`, `multiplier` (e.g., `100`), `currency`.
- OptionType: enum `CALL | PUT`.
- Side: enum `BUY | SELL`.
- OptionContract: `underlier`, `expiry`, `strike`, `type`.
- OptionLeg: `contract`, `side`, `quantity`, `entry_price?`, `notes?`.
- Strategy: `name`, `underlier`, `legs: list[OptionLeg]`, `created_at`, `tags?`, `constraints`.
- StrategyConstraints: invariants such as “same expiry”, “same underlier”, limits on total short risk.
- OptionQuote: `bid`, `ask`, `mid`, `iv`, `last_updated`.
- StrategySnapshot: immutable snapshot of `Strategy` plus market inputs at a point in time.
- StrategyMetrics: aggregated outputs: `net_debit_credit`, `max_profit`, `max_loss`, `break_evens`, greeks, `margin_estimate`.

## Services Layer
- OptionsDataService (existing):
  - `get_expiries() -> Iterable[date]`
  - `get_strikes(symbol, expiry) -> Iterable[float]`
  - Extend with: `get_chain(symbol, expiry) -> Iterable[OptionQuote]`, `get_quote(symbol, expiry, strike, type) -> OptionQuote`.
- PricingService (protocol): price and greeks per leg using underlier spot, IV, and contract details.
- AggregationService: aggregate leg P&L and greeks into `StrategyMetrics`; compute break‑evens by scanning a price grid.
- Presentation adapter: map `StrategyMetrics` into UI strings/labels and curve points for `ChartWidget`.

## Data Flow
- Symbol/expiry selection → chain retrieval via `OptionsDataService` → Add menu creates `OptionLeg` → `Strategy` updated.
- PricingService computes leg prices/greeks from `Underlier.spot` and quotes/IV.
- AggregationService sums per‑leg data → `StrategyMetrics` → UI metrics panel and chart curves.

## Validation & Invariants
- Underlier consistency: all legs share `underlier.symbol`.
- Expiry policy: default enforce same expiry; configurable via `StrategyConstraints`.
- Quantity: positive integers; direction encoded by `Side`.
- Price sanity: `bid <= mid <= ask`, `iv >= 0`.
- Non‑empty strategy: at least one leg required.

## Metrics & Computation
- Net debit/credit: sum `quantity * entry_price * multiplier` with side sign.
- Max profit/loss: evaluate aggregated P&L at bounds and expiration using payoff formulas per leg type.
- Break‑evens: find roots on the price grid for aggregated P&L.
- Greeks: sum delta/gamma/theta/vega per leg at current state.
- Margin estimate (phase 1 heuristic): rule‑based per short exposures; broker‑specific margin in phase 2.

## Serialization
- Pydantic v2 models for strict validation; export strategies as JSON for persistence/sharing.
- Avoid coupling to UI; models live under a new `delta_spread/domain` package.

## Extensibility
- Strategy templates are optional; legs themselves fully describe the structure (verticals, straddles, condors, butterflies).
- Add path for futures/options on futures by extending `Underlier`.

## Implementation Plan
- Phase 1: Core models
  - Define `OptionType` and `Side` enums.
  - Implement `Underlier`, `OptionContract`, `OptionLeg`, `Strategy`, `StrategyConstraints` as Pydantic models.
  - Add `OptionQuote`, `StrategyMetrics`, `StrategySnapshot` models.
- Phase 2: Services
  - Define `PricingService` and `AggregationService` protocols.
  - Extend `OptionsDataService` with chain/quote methods; implement mock quotes in `options_data_mock`.
- Phase 3: UI Wiring
  - Handle `on_add_option` to create legs and mutate the current `Strategy` (`delta_spread/ui/main_window.py:282`).
  - Display `StrategyMetrics` in metrics panel (`delta_spread/ui/main_window.py:216-263`).
- Phase 4: Chart Integration
  - Provide aggregated P&L curve points to `ChartWidget`, replacing placeholders (`delta_spread/ui/chart_widget.py:21-31`).
  - Use `StrikeRuler` to highlight leg strikes (`delta_spread/ui/strike_ruler.py:15-35`).
- Phase 5: Polish
  - Serialization to/from JSON; add basic save/load actions.
  - Input validation messaging in UI; guardrails for invalid combinations.

## Acceptance Criteria
- Strategies with 2–4 legs (vertical, straddle, iron condor) validate and serialize.
- Deterministic metrics from mock pricing: net debit/credit, max profit/loss, break‑evens update in UI.
- Add/remove legs via Add menu without crashes; chart renders aggregated curve.
- `ruff` and `basedpyright` pass with no `Any` creep; strict type safety preserved.

## Risks & Decisions
- Margin estimation varies by broker; treat as heuristic initially.
- Mixed expiries increase UI complexity; gated behind `StrategyConstraints`.
- Pricing accuracy depends on IV source; mock should be clearly marked and replaceable.

## Next Steps
- Implement Phase 1 models under `delta_spread/domain`.
- Extend data service, then wire `on_add_option` in `MainWindow`.
- Add presenter to update metrics panel and chart.
