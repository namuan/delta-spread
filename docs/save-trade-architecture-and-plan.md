# Save Trade Feature — Architecture & Plan

## Overview

Implement persistent storage for trades using SQLite database. A **Trade** represents a saved trading position consisting of one or more option legs. The feature allows users to save current positions and retrieve them later. The design follows the existing application patterns with modular, testable components.

## Goals

- **Persistence**: Save trades with all legs/positions to SQLite database
- **Modularity**: Repository pattern with protocol-based interfaces
- **Testability**: Easy to mock database layer for unit tests
- **Integration**: Seamless integration with existing `StrategyManager` and `MainWindowController`
- **Type Safety**: Full type annotations compatible with basedpyright strict mode

## Scope & Assumptions

- Single local SQLite database stored in the app's config directory
- One-to-many relationship: Trade → Legs (positions)
- No user authentication (single-user desktop app)
- Saved trades can be listed, loaded, updated, and deleted (full CRUD)
- Trade names must be unique for identification

## Database Location

Following the existing `AppConfig` pattern in [config.py](../delta_spread/config.py):

```
macOS:   ~/Library/Application Support/DeltaSpread/trades.db
Windows: %APPDATA%/DeltaSpread/trades.db
Linux:   ~/.config/deltaspread/trades.db
```

## Database Schema

### Tables

```sql
-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    underlier_symbol TEXT NOT NULL,
    underlier_spot REAL NOT NULL,
    underlier_multiplier INTEGER NOT NULL,
    underlier_currency TEXT NOT NULL,
    created_at TEXT NOT NULL,  -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,  -- ISO 8601 timestamp
    notes TEXT
);

-- Trade legs/positions table
CREATE TABLE IF NOT EXISTS trade_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    expiry TEXT NOT NULL,      -- ISO 8601 date (YYYY-MM-DD)
    strike REAL NOT NULL,
    option_type TEXT NOT NULL, -- 'CALL' or 'PUT'
    side TEXT NOT NULL,        -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    entry_price REAL,
    notes TEXT,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_trades_name ON trades(name);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(underlier_symbol);
CREATE INDEX IF NOT EXISTS idx_trade_legs_trade ON trade_legs(trade_id);
```

## Architecture Overview

```
delta_spread/
├── data/
│   ├── __init__.py
│   ├── database.py           # DatabaseConnection: connection management
│   └── trade_repository.py   # TradeRepository: CRUD operations
├── services/
│   └── trade_service.py      # TradeService: business logic layer
└── ui/
    ├── menus/
    │   └── file_menu.py      # File menu with Save/Load actions
    └── dialogs/
        ├── save_trade_dialog.py   # Dialog for saving trades
        └── load_trade_dialog.py   # Dialog for loading trades
```

## Component Design

### 1. DatabaseConnection (`delta_spread/data/database.py`)

Manages SQLite connection lifecycle and schema initialization.

```python
from typing import Protocol
from pathlib import Path
import sqlite3

class DatabaseConnectionProtocol(Protocol):
    """Protocol for database connection management."""
    
    def get_connection(self) -> sqlite3.Connection: ...
    def close(self) -> None: ...
    def initialize_schema(self) -> None: ...


class DatabaseConnection:
    """SQLite database connection manager.
    
    Handles connection pooling, schema initialization,
    and proper resource cleanup.
    """
    
    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize database connection.
        
        Args:
            db_path: Path to database file. If None, uses default app location.
        """
        ...
    
    def get_connection(self) -> sqlite3.Connection:
        """Get the SQLite connection (creates if needed)."""
        ...
    
    def close(self) -> None:
        """Close the database connection."""
        ...
    
    def initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        ...
```

### 2. TradeRepository (`delta_spread/data/trade_repository.py`)

Repository pattern for CRUD operations on trades.

```python
from typing import Protocol
from datetime import datetime
from dataclasses import dataclass

from ..domain.models import Strategy, OptionLeg, Underlier

class TradeRepositoryProtocol(Protocol):
    """Protocol for trade persistence operations."""
    
    def save(self, trade: Strategy, name: str, notes: str | None = None) -> int: ...
    def update(self, trade_id: int, trade: Strategy) -> None: ...
    def delete(self, trade_id: int) -> None: ...
    def get_by_id(self, trade_id: int) -> Strategy | None: ...
    def get_by_name(self, name: str) -> Strategy | None: ...
    def list_all(self) -> list[TradeSummary]: ...
    def list_by_symbol(self, symbol: str) -> list[TradeSummary]: ...


@dataclass
class TradeSummary:
    """Lightweight trade summary for list views."""
    
    id: int
    name: str
    underlier_symbol: str
    leg_count: int
    created_at: datetime
    updated_at: datetime
    notes: str | None


class TradeRepository:
    """SQLite implementation of trade repository.
    
    Handles serialization/deserialization of Strategy domain
    models to/from SQLite database as trades.
    """
    
    def __init__(self, db: DatabaseConnection) -> None:
        """Initialize repository with database connection."""
        ...
    
    def save(self, trade: Strategy, name: str, notes: str | None = None) -> int:
        """Save a trade to the database.
        
        Args:
            trade: The strategy/positions to save as a trade.
            name: Name for the trade.
            notes: Optional notes about the trade.
            
        Returns:
            The database ID of the saved trade.
            
        Raises:
            ValueError: If trade name already exists.
        """
        ...
    
    def update(self, trade_id: int, trade: Strategy) -> None:
        """Update an existing trade.
        
        Args:
            trade_id: Database ID of trade to update.
            trade: New trade data.
            
        Raises:
            ValueError: If trade_id not found.
        """
        ...
    
    def delete(self, trade_id: int) -> None:
        """Delete a trade and its legs.
        
        Args:
            trade_id: Database ID of trade to delete.
        """
        ...
    
    def get_by_id(self, trade_id: int) -> Strategy | None:
        """Retrieve a trade by its database ID.
        
        Args:
            trade_id: Database ID to look up.
            
        Returns:
            The trade as Strategy if found, None otherwise.
        """
        ...
    
    def get_by_name(self, name: str) -> Strategy | None:
        """Retrieve a trade by its name.
        
        Args:
            name: Trade name to look up.
            
        Returns:
            The trade as Strategy if found, None otherwise.
        """
        ...
    
    def list_all(self) -> list[TradeSummary]:
        """List all saved trades.
        
        Returns:
            List of trade summaries, ordered by updated_at descending.
        """
        ...
    
    def list_by_symbol(self, symbol: str) -> list[TradeSummary]:
        """List trades for a specific symbol.
        
        Args:
            symbol: Underlier symbol to filter by.
            
        Returns:
            List of trade summaries for the symbol.
        """
        ...
```

### 3. TradeService (`delta_spread/services/trade_service.py`)

Business logic layer that coordinates between UI and repository.

```python
from typing import Protocol

class TradeServiceProtocol(Protocol):
    """Protocol for trade management service."""
    
    def save_trade(
        self,
        trade: Strategy,
        name: str,
        notes: str | None = None,
    ) -> int: ...
    
    def load_trade(self, trade_id: int) -> Strategy | None: ...
    def delete_trade(self, trade_id: int) -> None: ...
    def get_saved_trades(self) -> list[TradeSummary]: ...
    def trade_name_exists(self, name: str) -> bool: ...


class TradeService:
    """Service for managing saved trades.
    
    Provides high-level operations for saving and loading
    trades, with validation and business rules.
    """
    
    def __init__(self, repository: TradeRepositoryProtocol) -> None:
        """Initialize service with repository dependency."""
        ...
    
    def save_trade(
        self,
        trade: Strategy,
        name: str,
        notes: str | None = None,
    ) -> int:
        """Save the current positions as a trade.
        
        Args:
            trade: Strategy containing positions to save.
            name: Name for the trade.
            notes: Optional notes about the trade.
            
        Returns:
            Database ID of saved trade.
            
        Raises:
            ValueError: If name already exists or trade invalid.
        """
        ...
    
    def load_trade(self, trade_id: int) -> Strategy | None:
        """Load a saved trade.
        
        Args:
            trade_id: ID of trade to load.
            
        Returns:
            The trade as Strategy if found, None otherwise.
        """
        ...
    
    def delete_trade(self, trade_id: int) -> None:
        """Delete a saved trade.
        
        Args:
            trade_id: ID of trade to delete.
        """
        ...
    
    def get_saved_trades(self) -> list[TradeSummary]:
        """Get list of all saved trades.
        
        Returns:
            List of trade summaries.
        """
        ...
    
    def trade_name_exists(self, name: str) -> bool:
        """Check if a trade name is already in use.
        
        Args:
            name: Name to check.
            
        Returns:
            True if name exists, False otherwise.
        """
        ...
```

### 4. UI Components

#### SaveTradeDialog (`delta_spread/ui/dialogs/save_trade_dialog.py`)

```python
class SaveTradeDialog(QDialog):
    """Dialog for saving the current positions as a trade.
    
    Allows user to:
    - Enter trade name
    - Add optional notes
    - Confirm or cancel save
    """
    
    def __init__(
        self,
        trade: Strategy,
        trade_service: TradeServiceProtocol,
        parent: QWidget | None = None,
    ) -> None: ...
    
    def get_save_data(self) -> tuple[str, str | None]:
        """Get the name and notes entered by user."""
        ...
```

#### LoadTradeDialog (`delta_spread/ui/dialogs/load_trade_dialog.py`)

```python
class LoadTradeDialog(QDialog):
    """Dialog for loading a saved trade.
    
    Shows a list of saved trades with:
    - Name, symbol, leg count, dates
    - Search/filter capabilities
    - Load and Delete actions
    """
    
    def __init__(
        self,
        trade_service: TradeServiceProtocol,
        parent: QWidget | None = None,
    ) -> None: ...
    
    def get_selected_trade_id(self) -> int | None:
        """Get the ID of the selected trade."""
        ...
```

#### FileMenu (`delta_spread/ui/menus/file_menu.py`)

```python
def build_file_menu(
    menu_bar: QMenuBar,
    on_save: Callable[[], None],
    on_load: Callable[[], None],
    on_new: Callable[[], None],
) -> QMenu:
    """Build the File menu with Save/Load/New actions.
    
    Keyboard shortcuts:
    - Cmd+S / Ctrl+S: Save Trade
    - Cmd+O / Ctrl+O: Load Trade
    - Cmd+N / Ctrl+N: New Trade
    """
    ...
```

### 5. Controller Integration

Extend `MainWindowController` with trade persistence methods:

```python
class MainWindowController:
    def __init__(
        self,
        # ... existing params ...
        trade_service: TradeServiceProtocol | None = None,
    ) -> None:
        self.trade_service = trade_service
        ...
    
    def save_trade(self) -> None:
        """Show save dialog and persist current positions as a trade."""
        if not self.strategy_manager.has_strategy():
            self._show_error("No positions to save")
            return
        
        strategy = self.strategy_manager.strategy
        dialog = SaveTradeDialog(strategy, self.trade_service, self._main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, notes = dialog.get_save_data()
            try:
                self.trade_service.save_trade(strategy, name, notes)
                self._show_success(f"Trade '{name}' saved")
            except ValueError as e:
                self._show_error(str(e))
    
    def load_trade(self) -> None:
        """Show load dialog and restore selected trade."""
        dialog = LoadTradeDialog(self.trade_service, self._main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            trade_id = dialog.get_selected_trade_id()
            if trade_id is not None:
                strategy = self.trade_service.load_trade(trade_id)
                if strategy:
                    self.strategy_manager.strategy = strategy
                    self._refresh_ui_for_strategy(strategy)
```
```

## Data Flow

```
User Action: "Save Trade"
      │
      ▼
┌─────────────────┐
│ MainWindowController │
│ .save_current_trade() │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  SaveTradeDialog  │ ◄── User enters name/notes
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   TradeService     │ ◄── Validates, coordinates
│ .save_current_strategy() │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  TradeRepository   │ ◄── Serializes to SQL
│     .save()        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  DatabaseConnection │ ◄── Executes SQL
│  (SQLite)          │
└─────────────────┘
```

## Serialization Details

### Trade → Database

```python
def _serialize_trade(trade: Strategy, name: str) -> dict[str, Any]:
    return {
        "name": name,
        "underlier_symbol": trade.underlier.symbol,
        "underlier_spot": trade.underlier.spot,
        "underlier_multiplier": trade.underlier.multiplier,
        "underlier_currency": trade.underlier.currency,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

def _serialize_leg(leg: OptionLeg, trade_id: int) -> dict[str, Any]:
    return {
        "trade_id": trade_id,
        "expiry": leg.contract.expiry.isoformat(),
        "strike": leg.contract.strike,
        "option_type": leg.contract.type.value,
        "side": leg.side.value,
        "quantity": leg.quantity,
        "entry_price": leg.entry_price,
        "notes": leg.notes,
    }
```

### Database → Trade

```python
def _deserialize_trade(row: sqlite3.Row, legs: list[OptionLeg]) -> Strategy:
    underlier = Underlier(
        symbol=row["underlier_symbol"],
        spot=row["underlier_spot"],
        multiplier=row["underlier_multiplier"],
        currency=row["underlier_currency"],
    )
    return Strategy(
        name=row["name"],
        underlier=underlier,
        legs=legs,
        created_at=datetime.fromisoformat(row["created_at"]),
    )

def _deserialize_leg(row: sqlite3.Row, underlier: Underlier) -> OptionLeg:
    contract = OptionContract(
        underlier=underlier,
        expiry=date.fromisoformat(row["expiry"]),
        strike=row["strike"],
        type=OptionType(row["option_type"]),
    )
    return OptionLeg(
        contract=contract,
        side=Side(row["side"]),
        quantity=row["quantity"],
        entry_price=row["entry_price"],
        notes=row["notes"],
    )
```

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Duplicate trade name | Raise `ValueError`, show dialog to user |
| Database file not writable | Raise `IOError`, show error message |
| Corrupted data on load | Log error, return `None`, notify user |
| Trade not found | Return `None`, show appropriate message |
| Database schema mismatch | Run migrations or re-initialize |

## Testing Strategy

### Unit Tests (`tests/test_trade_repository.py`)

```python
def test_save_and_retrieve_trade():
    """Test round-trip save and load."""
    
def test_save_duplicate_name_raises():
    """Test unique name constraint."""
    
def test_delete_cascades_legs():
    """Test legs are deleted with trade."""
    
def test_list_trades_ordered_by_date():
    """Test listing returns newest first."""
```

### Mock Repository (`mocks/trade_repository_mock.py`)

```python
class MockTradeRepository:
    """In-memory mock for testing without SQLite."""
    
    def __init__(self) -> None:
        self._trades: dict[int, Strategy] = {}
        self._next_id = 1
```

### Integration Tests

- Test full flow from UI action to database write
- Test loading trade restores all legs correctly
- Test database survives app restart

## Implementation Plan

### Phase 1: Data Layer (Priority: High)
1. Create `delta_spread/data/database.py` with `DatabaseConnection`
2. Create `delta_spread/data/trade_repository.py` with `TradeRepository`
3. Add unit tests for repository operations
4. Create mock repository for testing

### Phase 2: Service Layer (Priority: High)
1. Create `delta_spread/services/trade_service.py`
2. Add validation and business logic
3. Wire up dependency injection in app initialization

### Phase 3: UI Integration (Priority: Medium)
1. Create `delta_spread/ui/dialogs/` directory
2. Implement `SaveTradeDialog`
3. Implement `LoadTradeDialog`
4. Create `delta_spread/ui/menus/file_menu.py`

### Phase 4: Controller Integration (Priority: Medium)
1. Add `trade_service` dependency to `MainWindowController`
2. Implement `save_current_trade()` and `load_trade()` methods
3. Wire File menu actions to controller methods
4. Add keyboard shortcuts (Cmd+S, Cmd+O)

### Phase 5: Polish (Priority: Low)
1. Add strategy notes editing
2. Add confirmation dialogs for delete/overwrite
3. Add search/filter in load dialog
4. Handle edge cases (empty strategies, very long names)

## File Changes Summary

### New Files
- `delta_spread/data/database.py`
- `delta_spread/data/trade_repository.py`
- `delta_spread/services/trade_service.py`
- `delta_spread/ui/dialogs/__init__.py`
- `delta_spread/ui/dialogs/save_trade_dialog.py`
- `delta_spread/ui/dialogs/load_trade_dialog.py`
- `delta_spread/ui/menus/file_menu.py`
- `mocks/trade_repository_mock.py`
- `tests/test_trade_repository.py`
- `tests/test_trade_service.py`

### Modified Files
- `delta_spread/data/__init__.py` - Export new components
- `delta_spread/services/__init__.py` - Export TradeService
- `delta_spread/ui/menus/__init__.py` - Export file_menu
- `delta_spread/ui/main_window.py` - Add File menu
- `delta_spread/ui/controllers/main_window_controller.py` - Add trade methods
- `delta_spread/app.py` - Initialize database and services

## Acceptance Criteria

- [ ] User can save current positions as a trade with a name via File → Save Trade (Cmd+S)
- [ ] User can load a saved trade via File → Load Trade (Cmd+O)
- [ ] User can delete saved trades from load dialog
- [ ] Saved trades persist across app restarts
- [ ] Duplicate trade names are prevented with clear error message
- [ ] All legs are preserved correctly on save/load round-trip
- [ ] Code passes `ruff` and `basedpyright` checks
- [ ] Unit tests cover repository and service layers
- [ ] Mock repository available for UI testing

## Future Enhancements

- Export/import trades as JSON files
- Cloud sync for trades
- Trade versioning/history
- Tags and categories for organization
- Bulk operations (delete multiple, export all)

## Risks & Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite over JSON files | Better for querying, concurrent access, and data integrity |
| Repository pattern | Enables testing with mocks, separates concerns |
| Protocol-based interfaces | Follows existing codebase patterns, improves testability |
| Unique name constraint | Simple identification without exposing database IDs to users |
| CASCADE delete | Simpler than manual cleanup, maintains referential integrity |
