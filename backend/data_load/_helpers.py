"""Shared safe-parsing helpers for CSV loaders."""

from __future__ import annotations


def safe_int(value: str, default: int = 0) -> int:
    """Parse int, treating 'null' / empty as default."""
    v = value.strip().lower() if isinstance(value, str) else str(value).lower()
    if v in ("", "null", "none", "-", "nan"):
        return default
    try:
        return int(float(v))
    except (ValueError, TypeError):
        raise ValueError(f"cannot convert to int: {value!r}")


def safe_float(value: str, default: float = 0.0) -> float:
    """Parse float, treating 'null' / empty as default."""
    v = value.strip().lower() if isinstance(value, str) else str(value).lower()
    if v in ("", "null", "none", "-", "nan"):
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        raise ValueError(f"cannot convert to float: {value!r}")
