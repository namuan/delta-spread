# Delta Spread - Copilot Instructions

## Architecture Overview

Delta Spread is a **PyQt6 desktop application** for options strategy visualization. It follows a layered architecture:

```
delta_spread/
├── domain/models.py      # Immutable Pydantic models (frozen=True)
├── data/                 # Data layer (Tradier API, mock services)
├── services/             # Business logic (aggregation, pricing, strategy management)
└── ui/                   # PyQt6 widgets and controllers
    ├── controllers/      # MainWindowController handles business logic
    ├── panels/           # Reusable UI panel components
    └── menus/            # Menu bar components
```

**Key pattern**: UI components are "dumb" - the `MainWindowController` coordinates between panels and services.

## Domain Models

All domain models in `delta_spread/domain/models.py` use **Pydantic with `frozen=True`**. They are immutable:
- `Underlier`, `OptionContract`, `OptionLeg`, `Strategy`, `StrategyMetrics`
- Never mutate models; create new instances instead
- Models have built-in validators (e.g., `quantity > 0`, `strike > 0`)

## Service Layer Patterns

**Protocol-based services**: Use Python `Protocol` for service interfaces (see `services/pricing.py`).

**Mock/Real implementations**:
- Mock services live in `/mocks/` directory (e.g., `MockPricingService`, `MockOptionsDataService`)
- Real implementations in `/delta_spread/data/` (e.g., `TradierOptionsDataService`)
- Selection controlled by `AppConfig.use_real_data`

**Key services**:
- `AggregationService`: Computes strategy metrics, PnL curves, Greeks
- `StrategyManager`: Manages strategy state (add/remove legs)
- `QuoteService`: Fetches option quotes from data service

## UI/Controller Pattern

The `MainWindowController` is the central coordinator:
- Receives events from panels
- Calls services to compute metrics
- Uses `ChartPresenter` and `MetricsPresenter` to format data for display
- Updates panels via their public methods

## Development Commands

```bash
make run              # Run the application
make check            # Run ruff + basedpyright + pre-commit
make test             # Run all tests
make test-single TEST=test_services.py  # Run specific test
make format           # Auto-format and fix linting issues
make package          # Build macOS .app bundle
```

## Code Quality Requirements

**Ultra-strict typing**: Uses `basedpyright` in strict mode. All functions need type annotations.

**Ruff rules enforced**:
- No `print()` statements (use `logging`)
- Max cyclomatic complexity: 10
- Max nested blocks: 3
- No boolean positional arguments (`FBT`)

**Qt naming exception**: PyQt6 event handlers like `paintEvent` follow Qt conventions (not `snake_case`).

## Testing Patterns

Tests live in `/tests/`. Use pytest with `PYTHONPATH=.`:
```python
from delta_spread.domain.models import Strategy, OptionLeg, ...
from mocks.pricing_mock import MockPricingService
```

Test files follow `test_<module>.py` naming. Create domain objects directly using Pydantic models.

## Configuration

User config stored at `~/Library/Application Support/DeltaSpread/config.json` (macOS).
Access via `AppConfig.load()` / `config.save()`.

## Adding New Features

1. **New domain model**: Add to `models.py` with `frozen=True` and validators
2. **New service**: Create protocol in `services/`, implement in same file or `mocks/`
3. **New UI panel**: Create in `ui/panels/`, wire in `MainWindow`, add logic to controller
4. **New chart feature**: Update `ChartWidget` and `ChartPresenter.prepare()`
