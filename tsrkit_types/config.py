from __future__ import annotations

import os

# Environment-driven defaults
FAST_MODE = os.environ.get("TSRKIT_TYPES_FAST_MODE", "0") == "1"
STRICT_VALIDATE = os.environ.get("TSRKIT_TYPES_STRICT_VALIDATE", "1") != "0"
DICT_ORDER = os.environ.get("TSRKIT_TYPES_DICT_ORDER", "sorted")


def set_fast_mode(enabled: bool) -> None:
    """Enable or disable fast/unsafe paths."""
    global FAST_MODE
    FAST_MODE = bool(enabled)


def set_strict_validate(enabled: bool) -> None:
    """Enable or disable strict validation checks."""
    global STRICT_VALIDATE
    STRICT_VALIDATE = bool(enabled)


def set_dict_order(mode: str) -> None:
    """Set dictionary encoding order: 'sorted' or 'insertion'."""
    if mode not in ("sorted", "insertion"):
        raise ValueError("DICT_ORDER must be 'sorted' or 'insertion'")
    global DICT_ORDER
    DICT_ORDER = mode


def is_unsafe() -> bool:
    """True when unsafe fast paths are allowed."""
    return FAST_MODE or not STRICT_VALIDATE
