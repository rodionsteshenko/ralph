"""
Unit tests for configuration system.
"""

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.config import CodyConfig, ConfigurationError


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary .cody directory."""
    config_dir = tmp_path / ".cody"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Sample valid configuration."""
    return {
        "user_timezone": "America/Los_Angeles",
        "assistant_name": "TestAssistant",
        "context_window_size": 50,
        "paths": {
            "memory": ".cody/data/memory",
            "state": ".cody/data/state",
            "skills": ".cody/data/skills",
            "journal": ".cody/data/journal",
        },
    }


@pytest.mark.unit
def test_load_config_with_all_settings(
    temp_config_dir: Path, sample_config: dict[str, Any]
) -> None:
    """Test loading configuration with all settings specified."""
    config_path = temp_config_dir / "config.yaml"

    with open(config_path, "w") as f:
        yaml.safe_dump(sample_config, f)

    # Change to temp directory
    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        config = CodyConfig.load(config_path)

        assert config.user_timezone == "America/Los_Angeles"
        assert config.assistant_name == "TestAssistant"
        assert config.context_window_size == 50
        assert "memory" in config.paths
        assert "state" in config.paths
        assert "skills" in config.paths
        assert "journal" in config.paths
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_load_config_with_defaults(temp_config_dir: Path) -> None:
    """Test loading configuration with only required settings (uses defaults)."""
    config_path = temp_config_dir / "config.yaml"
    minimal_config = {"user_timezone": "UTC"}

    with open(config_path, "w") as f:
        yaml.safe_dump(minimal_config, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        config = CodyConfig.load(config_path)

        assert config.user_timezone == "UTC"
        assert config.assistant_name == "Cody"  # Default
        assert config.context_window_size == 40  # Default
        assert "memory" in config.paths  # Default paths created
        assert "state" in config.paths
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_load_config_missing_file(temp_config_dir: Path) -> None:
    """Test loading configuration when file doesn't exist (should use all defaults)."""
    config_path = temp_config_dir / "nonexistent.yaml"

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        # Should fail due to missing required timezone
        with pytest.raises(ConfigurationError) as exc_info:
            CodyConfig.load(config_path)

        assert "user_timezone is required" in str(exc_info.value)
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_validation_missing_timezone(temp_config_dir: Path) -> None:
    """Test validation error when timezone is missing."""
    config_path = temp_config_dir / "config.yaml"

    # Empty config (no timezone)
    with open(config_path, "w") as f:
        yaml.safe_dump({}, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        with pytest.raises(ConfigurationError) as exc_info:
            CodyConfig.load(config_path)

        error_msg = str(exc_info.value)
        assert "user_timezone is required" in error_msg
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_validation_invalid_context_window_size(temp_config_dir: Path) -> None:
    """Test validation error when context_window_size is invalid."""
    config_path = temp_config_dir / "config.yaml"

    invalid_configs = [
        {"user_timezone": "UTC", "context_window_size": 0},
        {"user_timezone": "UTC", "context_window_size": -10},
        {"user_timezone": "UTC", "context_window_size": "not_a_number"},
    ]

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        for invalid_config in invalid_configs:
            with open(config_path, "w") as f:
                yaml.safe_dump(invalid_config, f)

            with pytest.raises(ConfigurationError) as exc_info:
                CodyConfig.load(config_path)

            error_msg = str(exc_info.value)
            assert "context_window_size must be a positive integer" in error_msg
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_validation_invalid_assistant_name(temp_config_dir: Path) -> None:
    """Test validation error when assistant_name is invalid."""
    config_path = temp_config_dir / "config.yaml"

    invalid_configs = [
        {"user_timezone": "UTC", "assistant_name": ""},
        {"user_timezone": "UTC", "assistant_name": None},
        {"user_timezone": "UTC", "assistant_name": 123},
    ]

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        for invalid_config in invalid_configs:
            with open(config_path, "w") as f:
                yaml.safe_dump(invalid_config, f)

            with pytest.raises(ConfigurationError) as exc_info:
                CodyConfig.load(config_path)

            error_msg = str(exc_info.value)
            assert "assistant_name must be a non-empty string" in error_msg
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_environment_variable_override_api_key(
    temp_config_dir: Path, sample_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that ANTHROPIC_API_KEY environment variable overrides config file."""
    config_path = temp_config_dir / "config.yaml"

    # Add api_key to config
    config_with_key = {**sample_config, "api_key": "config_key_123"}

    with open(config_path, "w") as f:
        yaml.safe_dump(config_with_key, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        # Set environment variable
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env_key_456")

        config = CodyConfig.load(config_path)

        # Environment variable should override config file
        assert config.api_key == "env_key_456"
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_api_key_from_config_when_env_not_set(
    temp_config_dir: Path, sample_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that api_key from config file is used when env var not set."""
    config_path = temp_config_dir / "config.yaml"

    config_with_key = {**sample_config, "api_key": "config_key_789"}

    with open(config_path, "w") as f:
        yaml.safe_dump(config_with_key, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        # Ensure env var is not set
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        config = CodyConfig.load(config_path)

        assert config.api_key == "config_key_789"
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_api_key_none_when_not_provided(
    temp_config_dir: Path, sample_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that api_key is None when not in config or env."""
    config_path = temp_config_dir / "config.yaml"

    with open(config_path, "w") as f:
        yaml.safe_dump(sample_config, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        # Ensure env var is not set
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        config = CodyConfig.load(config_path)

        assert config.api_key is None
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_to_dict(sample_config: dict[str, Any], temp_config_dir: Path) -> None:
    """Test converting config to dictionary."""
    config_path = temp_config_dir / "config.yaml"

    with open(config_path, "w") as f:
        yaml.safe_dump(sample_config, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        config = CodyConfig.load(config_path)
        config_dict = config.to_dict()

        assert config_dict["user_timezone"] == "America/Los_Angeles"
        assert config_dict["assistant_name"] == "TestAssistant"
        assert config_dict["context_window_size"] == 50
        assert "memory" in config_dict["paths"]
        # Paths should be strings in dict
        assert isinstance(config_dict["paths"]["memory"], str)
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_save_config(temp_config_dir: Path, sample_config: dict[str, Any]) -> None:
    """Test saving configuration to file."""
    config_path = temp_config_dir / "config.yaml"

    with open(config_path, "w") as f:
        yaml.safe_dump(sample_config, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        # Load config
        config = CodyConfig.load(config_path)

        # Modify and save
        config.assistant_name = "ModifiedAssistant"
        save_path = temp_config_dir / "saved_config.yaml"
        config.save(save_path)

        # Reload and verify
        reloaded = CodyConfig.load(save_path)
        assert reloaded.assistant_name == "ModifiedAssistant"
        assert reloaded.user_timezone == "America/Los_Angeles"
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_save_does_not_include_api_key(
    temp_config_dir: Path, sample_config: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that save() does not write api_key to file."""
    config_path = temp_config_dir / "config.yaml"

    with open(config_path, "w") as f:
        yaml.safe_dump(sample_config, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        # Set API key via env
        monkeypatch.setenv("ANTHROPIC_API_KEY", "secret_key")

        config = CodyConfig.load(config_path)
        assert config.api_key == "secret_key"

        # Save to new file
        save_path = temp_config_dir / "saved.yaml"
        config.save(save_path)

        # Verify api_key not in saved file
        with open(save_path) as f:
            saved_data = yaml.safe_load(f)

        assert "api_key" not in saved_data
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_paths_are_path_objects(temp_config_dir: Path, sample_config: dict[str, Any]) -> None:
    """Test that paths are loaded as Path objects."""
    config_path = temp_config_dir / "config.yaml"

    with open(config_path, "w") as f:
        yaml.safe_dump(sample_config, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        config = CodyConfig.load(config_path)

        for path_name, path_value in config.paths.items():
            assert isinstance(path_value, Path), f"paths.{path_name} should be a Path object"
    finally:
        os.chdir(original_cwd)


@pytest.mark.unit
def test_multiple_validation_errors(temp_config_dir: Path) -> None:
    """Test that multiple validation errors are reported together."""
    config_path = temp_config_dir / "config.yaml"

    # Config with multiple issues
    invalid_config = {
        "assistant_name": "",
        "context_window_size": -5,
        # Missing timezone
    }

    with open(config_path, "w") as f:
        yaml.safe_dump(invalid_config, f)

    original_cwd = Path.cwd()
    os.chdir(temp_config_dir.parent)

    try:
        with pytest.raises(ConfigurationError) as exc_info:
            CodyConfig.load(config_path)

        error_msg = str(exc_info.value)
        # Should report all errors
        assert "user_timezone is required" in error_msg
        assert "context_window_size must be a positive integer" in error_msg
        assert "assistant_name must be a non-empty string" in error_msg
    finally:
        os.chdir(original_cwd)
