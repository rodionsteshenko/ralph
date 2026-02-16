"""JSON output helpers and exit code constants for machine-consumable CLI output."""

import json
import sys
from dataclasses import asdict
from typing import Any, Dict, Union

# Exit codes
EXIT_SUCCESS = 0          # story/stories completed
EXIT_ERROR = 1            # error or crash
EXIT_MAX_FAILURES = 2     # max consecutive failures reached
EXIT_MAX_ITERATIONS = 3   # max iterations reached, stories remain
EXIT_NOTHING_TO_DO = 4    # all stories already complete


def json_output(data: Union[Dict[str, Any], list], exit_code: int = EXIT_SUCCESS) -> int:
    """Print JSON to stdout and return the exit code.

    Args:
        data: Dictionary or list to serialize as JSON.
        exit_code: Exit code to return.

    Returns:
        The exit code (for use with sys.exit).
    """
    # Handle dataclasses by converting to dict first
    if hasattr(data, '__dataclass_fields__'):
        data = asdict(data)  # type: ignore[call-overload]

    print(json.dumps(data, indent=2, default=str), file=sys.stdout)
    return exit_code


def json_error(message: str, exit_code: int = EXIT_ERROR) -> int:
    """Print a JSON error object to stdout and return the exit code.

    Args:
        message: Error message.
        exit_code: Exit code to return.

    Returns:
        The exit code (for use with sys.exit).
    """
    print(json.dumps({"error": message}, indent=2), file=sys.stdout)
    return exit_code
