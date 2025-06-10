"""
ZMCP Configuration Module

Handles application configuration, settings persistence, and environment management.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class Config:
    """
    Manages ZMCP configuration settings.
    """
    DEFAULT_CONFIG = {
        "servers": {},
        "client": {
            "recent_connections": []
        },
        "ui": {
            "theme": "light",
            "layout": "default",
            "recent_files": []
        }
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory to store configuration files. If None, uses default location.
        """
        self.config_dir = config_dir or Path.home() / ".zmcp"
        self.config_file = self.config_dir / "config.json"
        self.ensure_config_dir()
        self.config = self.load_config()

    def ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        os.makedirs(self.config_dir, exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if not self.config_file.exists():
            return self.DEFAULT_CONFIG

        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If config file is corrupted, return default
            return self.DEFAULT_CONFIG

    def save_config(self) -> None:
        """Save current configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key path.

        Args:
            key: Dot-separated key path (e.g., "ui.theme")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split('.')
        current = self.config

        for part in parts:
            if part not in current:
                return default
            current = current[part]

        return current

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key path.

        Args:
            key: Dot-separated key path (e.g., "ui.theme")
            value: Value to set
        """
        parts = key.split('.')
        current = self.config

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value
        self.save_config()


# Global configuration instance
config = Config()
