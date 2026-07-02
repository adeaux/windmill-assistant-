"""Value parsing helpers (Blynk returns numbers or strings interchangeably)."""

from __future__ import annotations

from typing import Any


def as_float(value: Any) -> float | None:
    """Best-effort conversion of a pin value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    """Best-effort conversion of a pin value to int."""
    number = as_float(value)
    return None if number is None else int(number)


def as_bool(value: Any) -> bool | None:
    """Best-effort conversion of a pin value to bool (0/1, true/false)."""
    if value is None:
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "on"):
            return True
        if lowered in ("false", "off"):
            return False
    number = as_float(value)
    return None if number is None else number != 0
