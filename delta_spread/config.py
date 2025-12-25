"""Application configuration management."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

_APP_NAME = "DeltaSpread"


def _get_config_dir() -> Path:
    """Return platform-appropriate config directory."""
    if os.name == "nt":
        # Windows: %APPDATA%/DeltaSpread
        base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        return Path(base) / _APP_NAME
    if os.uname().sysname == "Darwin":
        # macOS: ~/Library/Application Support/DeltaSpread
        return Path.home() / "Library" / "Application Support" / _APP_NAME
    # Linux/Unix: ~/.config/deltaspread
    xdg = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    return Path(xdg) / _APP_NAME.lower()


def _get_config_path() -> Path:
    return _get_config_dir() / "config.json"


@dataclass
class AppConfig:
    """Stores user-editable application configuration."""

    use_real_data: bool = False
    tradier_base_url: str = "https://api.tradier.com"
    tradier_token: str = ""
    max_expiries: int = 30

    def save(self) -> None:
        """Persist configuration to disk."""
        path = _get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "use_real_data": self.use_real_data,
            "tradier_base_url": self.tradier_base_url,
            "tradier_token": self.tradier_token,
            "max_expiries": self.max_expiries,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> AppConfig:
        """Load configuration from disk, or return defaults if missing."""
        path = _get_config_path()
        if not path.exists():
            return cls()
        try:
            data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))  # type: ignore[misc]
            return cls(
                use_real_data=bool(data.get("use_real_data")),
                tradier_base_url=str(
                    data.get("tradier_base_url", "https://api.tradier.com")
                ),
                tradier_token=str(data.get("tradier_token", "")),
                max_expiries=int(data.get("max_expiries", 30)),  # type: ignore[arg-type]
            )
        except (json.JSONDecodeError, OSError):
            return cls()
