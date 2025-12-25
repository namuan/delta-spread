# Delta Spread

> Collapse the wave function of uncertainty.

**Delta Spread** is a modern, local-first desktop application for visualizing and analyzing options trading strategies. Built with Python and PyQt6, it provides an interactive interface to model complex option spreads, visualize payoff diagrams, and monitor real-time Greeks and risk metrics.

![](assets/intro.png)

## ✨ Features

- **Interactive Strategy Builder**: Easily construct strategies (Verticals, Iron Condors, etc.) by adding individual option legs.
- **Visual Payoff Diagrams**: Real-time charting of PnL profiles across different underlying prices.
- **Real-time Data**: Integrated with Tradier API for live options data (optional, uses mock data by default).
- **Risk Analysis**: Instant calculation of key metrics:
  - **PnL**: Max Profit, Max Loss, Net Debit/Credit.
  - **Breakevens**: Exact price points where the trade turns profitable.
  - **Greeks**: Portfolio-weighted Delta, Gamma, Theta, Vega, and Rho.
  - **Probability of Profit (POP)**: Estimated success rate based on volatility.
- **Expiry Timeline**: Navigate through different expiration dates with a specialized timeline view.
- **Visual Badge System**: Intuitive "badges" on the strike ruler to visualize active Buy/Sell positions for Calls and Puts.
- **Local-First**: No cloud dependencies; runs entirely on your machine.

## 🛠 Tech Stack

- **Language**: Python 3.12+
- **GUI Framework**: PyQt6
- **Data Validation**: Pydantic v2
- **Dependency Management**: `uv` (modern Python package installer)
- **Packaging**: PyInstaller (builds standalone `.app` bundles)
- **Code Quality**: `ruff` (linting/formatting), `basedpyright` (strict type checking)

## 🚀 Getting Started

### Prerequisites

- **Python 3.12** or higher.
- **uv**: A fast Python package and project manager. [Install uv](https://github.com/astral-sh/uv).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/delta-spread.git
   cd delta-spread
   ```

2. **Install dependencies:**
   ```bash
   make install
   ```
   This will create a virtual environment and install all required packages and pre-commit hooks.

### Running the Application

To start the application in development mode:

```bash
make run
```

### Using Real Market Data (Tradier API)

By default, DeltaSpread uses mock data for testing. To use real-time options data:

1. Sign up for a [Tradier account](https://tradier.com) and obtain an API token
2. Launch DeltaSpread
3. Go to **DeltaSpread → Preferences** (or press `Cmd+,`)
4. Enable "Use Real Data" and enter your Tradier API token
5. Click OK - the app will immediately start using live data

## 📦 Packaging

To build a standalone macOS application bundle (`DeltaSpread.app`):

```bash
make package
```

The artifact will be available in the `dist/` directory.

To install it directly to your Applications folder (macOS only):

```bash
make install-macosx
```

## 💻 Development

This project enforces strict code quality standards.

### Commands

| Command | Description |
|---------|-------------|
| `make check` | Run all quality checks: formatting, linting, and type checking. |
| `make test` | Run the full unit test suite. |
| `make test-single TEST=...` | Run a specific test file. |
| `make format` | Auto-format code and fix fixable linting issues. |
| `make clean` | Remove build artifacts and cache directories. |

### Project Structure

- `delta_spread/`
  - `domain/`: Core business logic and Pydantic models.
  - `services/`: Calculation engines (Pricing, Aggregation, Data).
  - `ui/`: PyQt6 widgets and window management.
- `tests/`: Pytest suite matching the source structure.
- `main.spec`: PyInstaller configuration.

## 📄 License

MIT License
