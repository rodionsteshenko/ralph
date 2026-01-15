"""
Configuration system for Cody assistant.

Loads settings from .cody/config.yaml with sensible defaults and environment variable overrides.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required settings."""

    pass


@dataclass
class CodyConfig:
    """
    Configuration for Cody assistant.

    Attributes:
        user_timezone: User's timezone (e.g., "America/Los_Angeles")
        assistant_name: Name of the assistant (default: "Cody")
        context_window_size: Number of messages to keep in context (default: 40)
        paths: Dictionary of paths for data storage
        api_key: Anthropic API key (from env var ANTHROPIC_API_KEY)
    """

    user_timezone: str
    assistant_name: str = "Cody"
    context_window_size: int = 40
    paths: dict[str, Path] = field(default_factory=dict)
    api_key: str | None = None

    @classmethod
    def load(cls, config_path: Path | None = None) -> "CodyConfig":
        """
        Load configuration from YAML file with defaults and env var overrides.

        Args:
            config_path: Path to config.yaml file. Defaults to .cody/config.yaml

        Returns:
            CodyConfig instance with loaded settings

        Raises:
            ConfigurationError: If required settings are missing or invalid
        """
        if config_path is None:
            config_path = Path.cwd() / ".cody" / "config.yaml"

        # Load YAML config if it exists
        config_data: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path) as f:
                loaded_data = yaml.safe_load(f)
                if loaded_data is not None:
                    config_data = loaded_data

        # Extract settings with defaults
        user_timezone = config_data.get("user_timezone", "")
        assistant_name = config_data.get("assistant_name", "Cody")
        context_window_size = config_data.get("context_window_size", 40)

        # Load paths with defaults
        paths_config = config_data.get("paths", {})
        default_base = Path.cwd() / ".cody" / "data"
        paths = {
            "memory": Path(paths_config.get("memory", default_base / "memory")),
            "state": Path(paths_config.get("state", default_base / "state")),
            "skills": Path(paths_config.get("skills", default_base / "skills")),
            "journal": Path(paths_config.get("journal", default_base / "journal")),
        }

        # Environment variable overrides for secrets
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key_from_config := config_data.get("api_key"):
            # Allow config file override only if env var not set
            if api_key is None:
                api_key = api_key_from_config

        # Validation
        errors: list[str] = []

        if not user_timezone:
            errors.append("user_timezone is required (e.g., 'America/Los_Angeles')")

        if not isinstance(context_window_size, int) or context_window_size <= 0:
            errors.append(
                f"context_window_size must be a positive integer, got: {context_window_size}"
            )

        if not assistant_name or not isinstance(assistant_name, str):
            errors.append(f"assistant_name must be a non-empty string, got: {assistant_name}")

        # Validate paths are Path objects
        for path_name, path_value in paths.items():
            if not isinstance(path_value, Path):
                errors.append(f"paths.{path_name} must be a valid path, got: {path_value}")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigurationError(error_msg)

        return cls(
            user_timezone=user_timezone,
            assistant_name=assistant_name,
            context_window_size=context_window_size,
            paths=paths,
            api_key=api_key,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary format.

        Returns:
            Dictionary representation of config
        """
        return {
            "user_timezone": self.user_timezone,
            "assistant_name": self.assistant_name,
            "context_window_size": self.context_window_size,
            "paths": {k: str(v) for k, v in self.paths.items()},
        }

    def save(self, config_path: Path | None = None) -> None:
        """
        Save configuration to YAML file.

        Args:
            config_path: Path to save config.yaml. Defaults to .cody/config.yaml

        Note:
            Does not save api_key to file (should be in env var only)
        """
        if config_path is None:
            config_path = Path.cwd() / ".cody" / "config.yaml"

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            yaml.safe_dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
