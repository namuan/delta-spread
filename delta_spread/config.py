"""Application configuration management."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path

_APP_NAME = "DeltaSpread"
logger = logging.getLogger(__name__)


def _get_config_dir() -> Path:
    """Return platform-appropriate config directory."""
    if os.name == "nt":
        base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        return Path(base) / _APP_NAME
    if os.uname().sysname == "Darwin":
        return Path.home() / "Library" / "Application Support" / _APP_NAME
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
            "tradier_token": "***" if self.tradier_token else "",
            "max_expiries": self.max_expiries,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(
            "Config saved → %s (use_real_data=%s, max_expiries=%d)",
            path,
            self.use_real_data,
            self.max_expiries,
        )

    @classmethod
    def load(cls) -> AppConfig:
        """Load configuration from disk, or return defaults if missing."""
        path = _get_config_path()
        if not path.exists():
            logger.info("No config file at %s — using defaults", path)
            return cls()
        try:
            raw = path.read_text(encoding="utf-8")
            data: dict[str, object] = json.loads(raw)  # type: ignore[misc]
            config = cls(
                use_real_data=bool(data.get("use_real_data")),
                tradier_base_url=str(
                    data.get("tradier_base_url", "https://api.tradier.com")
                ),
                tradier_token=str(data.get("tradier_token", "")),
                max_expiries=int(data.get("max_expiries", 30)),  # type: ignore[arg-type]
            )
            logger.info(
                "Config loaded ← %s (use_real_data=%s)", path, config.use_real_data
            )
            return config
        except (json.JSONDecodeError, OSError):
            logger.warning(
                "Failed to load config from %s — using defaults", path, exc_info=True
            )
            return cls()
