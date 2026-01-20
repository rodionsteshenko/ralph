"""Utility functions."""

import json
from pathlib import Path
from typing import Any, Optional

# Try to import ASCII art display (optional dependency)
try:
    from ascii_image import display_ascii_image  # type: ignore[import-not-found]

    HAS_ASCII_ART = True
except ImportError:
    HAS_ASCII_ART = False


def load_prd(path: Path) -> Optional[dict[str, Any]]:
    """Load PRD from JSON file."""
    try:
        with open(path) as f:
            data: dict[str, Any] = json.load(f)
            return data
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def show_ralph_banner() -> bool:
    """Display the Ralph ASCII art banner.

    Returns:
        True if ASCII art was displayed, False otherwise
    """
    if HAS_ASCII_ART:
        ralph_image_path = Path(__file__).parent.parent.parent / "ralph.jpg"
        if ralph_image_path.exists():
            try:
                display_ascii_image(
                    str(ralph_image_path),
                    max_width=60,
                    dark_mode=True,
                    contrast_factor=1.5,
                )
                print()  # Add spacing after ASCII art
                return True
            except Exception:
                pass
    return False
