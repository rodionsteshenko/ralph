"""Test package structure and basic imports."""
import importlib.util
from pathlib import Path


def test_package_structure() -> None:
    """Verify the package directory structure exists."""
    src_ralph = Path("src/ralph")
    assert src_ralph.exists(), "src/ralph/ directory should exist"
    assert src_ralph.is_dir(), "src/ralph/ should be a directory"


def test_init_file_exists() -> None:
    """Verify __init__.py exists."""
    init_file = Path("src/ralph/__init__.py")
    assert init_file.exists(), "src/ralph/__init__.py should exist"


def test_version_defined() -> None:
    """Verify __version__ is defined in __init__.py."""
    import sys
    from pathlib import Path

    # Add src to path temporarily
    src_path = str(Path(__file__).parent.parent / "src")
    sys.path.insert(0, src_path)

    try:
        import ralph
        assert hasattr(ralph, "__version__"), "__version__ should be defined"
        assert ralph.__version__ == "0.1.0", "__version__ should be '0.1.0'"
    finally:
        sys.path.remove(src_path)


def test_module_files_exist() -> None:
    """Verify all required module files exist."""
    expected_modules = ["cli.py", "detect.py", "prd.py", "gates.py", "loop.py", "utils.py"]
    src_ralph = Path("src/ralph")

    for module in expected_modules:
        module_path = src_ralph / module
        assert module_path.exists(), f"{module} should exist"
        assert module_path.is_file(), f"{module} should be a file"


def test_modules_are_importable() -> None:
    """Verify all modules can be imported (basic syntax check)."""
    import sys
    from pathlib import Path

    # Add src to path temporarily
    src_path = str(Path(__file__).parent.parent / "src")
    sys.path.insert(0, src_path)

    try:
        # These imports will fail if there are syntax errors
        import ralph.cli
        import ralph.detect
        import ralph.prd
        import ralph.gates
        import ralph.loop
        import ralph.utils

        # Verify they're actually module objects
        assert hasattr(ralph.cli, "__file__")
        assert hasattr(ralph.detect, "__file__")
        assert hasattr(ralph.prd, "__file__")
        assert hasattr(ralph.gates, "__file__")
        assert hasattr(ralph.loop, "__file__")
        assert hasattr(ralph.utils, "__file__")
    finally:
        sys.path.remove(src_path)
