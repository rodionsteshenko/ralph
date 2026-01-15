"""
End-to-end tests for configuration system using real file system.
"""

from pathlib import Path

import pytest

from src.config import CodyConfig, ConfigurationError


@pytest.mark.e2e
def test_load_config_from_real_file() -> None:
    """
    E2E test: Load configuration from actual .cody/config.yaml file.

    This test verifies that the configuration system can read a real config file
    and properly parse all settings.
    """
    # Use the actual .cody/config.yaml in the project
    config_path = Path.cwd() / ".cody" / "config.yaml"

    if not config_path.exists():
        pytest.skip("No .cody/config.yaml file found")

    config = CodyConfig.load(config_path)

    # Verify required fields are loaded
    assert config.user_timezone is not None
    assert config.assistant_name is not None
    assert config.context_window_size > 0

    # Verify paths are Path objects
    assert isinstance(config.paths["memory"], Path)
    assert isinstance(config.paths["state"], Path)
    assert isinstance(config.paths["skills"], Path)
    assert isinstance(config.paths["journal"], Path)


@pytest.mark.e2e
def test_save_and_reload_config_roundtrip(tmp_path: Path) -> None:
    """
    E2E test: Save config to disk and reload it (roundtrip test).

    This verifies that configuration can be persisted to disk and reloaded
    without data loss.
    """
    config_path = tmp_path / ".cody" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create config
    original = CodyConfig(
        user_timezone="America/New_York",
        assistant_name="TestBot",
        context_window_size=60,
        paths={
            "memory": Path(tmp_path / "memory"),
            "state": Path(tmp_path / "state"),
            "skills": Path(tmp_path / "skills"),
            "journal": Path(tmp_path / "journal"),
        },
    )

    # Save to disk
    original.save(config_path)

    # Verify file exists
    assert config_path.exists()
    assert config_path.is_file()

    # Reload from disk
    reloaded = CodyConfig.load(config_path)

    # Verify all fields match
    assert reloaded.user_timezone == original.user_timezone
    assert reloaded.assistant_name == original.assistant_name
    assert reloaded.context_window_size == original.context_window_size
    assert len(reloaded.paths) == len(original.paths)

    # Verify paths are correct
    for key in original.paths:
        assert str(reloaded.paths[key]) == str(original.paths[key])


@pytest.mark.e2e
def test_environment_variable_override_with_real_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    E2E test: Verify ANTHROPIC_API_KEY from environment is used.

    This tests the real environment variable override behavior.
    """
    config_path = tmp_path / ".cody" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a config file without API key
    config = CodyConfig(
        user_timezone="UTC",
        paths={
            "memory": Path(tmp_path / "memory"),
            "state": Path(tmp_path / "state"),
            "skills": Path(tmp_path / "skills"),
            "journal": Path(tmp_path / "journal"),
        },
    )
    config.save(config_path)

    # Set real environment variable
    test_api_key = "sk-test-real-key-12345"
    monkeypatch.setenv("ANTHROPIC_API_KEY", test_api_key)

    # Load config
    loaded = CodyConfig.load(config_path)

    # Verify API key comes from environment
    assert loaded.api_key == test_api_key


@pytest.mark.e2e
def test_config_validation_with_real_file(tmp_path: Path) -> None:
    """
    E2E test: Verify validation errors with real file operations.

    This tests that validation works correctly when reading from actual files.
    """
    config_path = tmp_path / ".cody" / "invalid_config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write invalid config to file
    with open(config_path, "w") as f:
        f.write("assistant_name: ValidName\n")
        f.write("context_window_size: 40\n")
        # Missing user_timezone

    # Verify validation error is raised
    with pytest.raises(ConfigurationError) as exc_info:
        CodyConfig.load(config_path)

    assert "user_timezone is required" in str(exc_info.value)


@pytest.mark.e2e
def test_config_with_nonexistent_path() -> None:
    """
    E2E test: Verify behavior when config file doesn't exist.

    This tests graceful handling of missing files.
    """
    nonexistent_path = Path("/tmp/definitely_does_not_exist_12345/config.yaml")

    # Should fail due to missing required fields (not file not found)
    with pytest.raises(ConfigurationError) as exc_info:
        CodyConfig.load(nonexistent_path)

    assert "user_timezone is required" in str(exc_info.value)
