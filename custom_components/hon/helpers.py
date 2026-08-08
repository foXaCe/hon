"""Pure helper functions shared across the hOn integration."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


def snake_case(value: str) -> str:
    """Convert a camelCase string to snake_case.

    >>> snake_case("tempSelZ1")
    "temp_sel_z1"
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def get_key(
    dictionary: dict[str, str], val: str, default: str | None = None
) -> str | None:
    """Return the first key of ``dictionary`` whose value equals ``val``.

    Used to reverse API value → HA option mappings.
    """
    for key, value in dictionary.items():
        if value == val:
            return key
    return default


def minutes_until(target: datetime, now: datetime) -> int:
    """Return the number of whole minutes until the target time."""
    return max(0, int((target - now).total_seconds() / 60))
