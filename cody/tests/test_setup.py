"""
Test to verify project setup and configuration.
"""


def test_python_version() -> None:
    """Verify Python version is 3.10 or higher."""
    import sys

    assert sys.version_info >= (3, 10)


def test_imports() -> None:
    """Verify core dependencies can be imported."""
    import rich
    import yaml

    # These should not raise ImportError
    assert yaml is not None
    assert rich is not None


def test_project_structure() -> None:
    """Verify project directories exist."""
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    # Check that required directories exist
    assert (project_root / "src").exists()
    assert (project_root / "tests").exists()
    assert (project_root / ".cody").exists()
    assert (project_root / ".cody" / "data").exists()

    # Check that required files exist
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "README.md").exists()
    assert (project_root / "Makefile").exists()
    assert (project_root / ".gitignore").exists()
