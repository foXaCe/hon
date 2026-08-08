"""Tests for the pure helper functions."""

from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.hon.helpers import get_key, minutes_until, snake_case


def test_snake_case_basic() -> None:
    """camelCase is converted to snake_case."""
    assert snake_case("tempSelZ1") == "temp_sel_z1"
    assert snake_case("onOffStatus") == "on_off_status"
    assert snake_case("prCode") == "pr_code"


def test_snake_case_already_snake() -> None:
    """Already-lowercase strings are unchanged."""
    assert snake_case("temperature") == "temperature"


def test_snake_case_acronyms() -> None:
    """Every capital letter before a word boundary gets an underscore."""
    assert snake_case("MACAddress") == "m_a_c_address"
    assert snake_case("PM2p5Value") == "p_m2p5_value"


def test_snake_case_empty() -> None:
    """An empty string stays empty."""
    assert snake_case("") == ""


def test_get_key_found() -> None:
    """get_key returns the key matching the value."""
    mapping = {"a": "1", "b": "2"}
    assert get_key(mapping, "2") == "b"


def test_get_key_not_found() -> None:
    """get_key returns the default when the value is missing."""
    mapping = {"a": "1"}
    assert get_key(mapping, "9", "fallback") == "fallback"
    assert get_key(mapping, "9") is None


def test_get_key_first_match() -> None:
    """get_key returns the first key matching a duplicated value."""
    mapping = {"a": "1", "c": "1"}
    assert get_key(mapping, "1") == "a"


def test_minutes_until_future() -> None:
    """A future target returns the whole minutes remaining."""
    now = datetime(2026, 1, 1, 10, 0, 0)
    target = now + timedelta(minutes=5, seconds=30)
    assert minutes_until(target, now) == 5


def test_minutes_until_past() -> None:
    """A past target clamps to zero."""
    now = datetime(2026, 1, 1, 10, 0, 0)
    target = now - timedelta(minutes=10)
    assert minutes_until(target, now) == 0


def test_minutes_until_under_one_minute() -> None:
    """Less than one minute clamps to zero."""
    now = datetime(2026, 1, 1, 10, 0, 0)
    target = now + timedelta(seconds=45)
    assert minutes_until(target, now) == 0


def test_minutes_until_exact() -> None:
    """An exact number of minutes is returned as-is."""
    now = datetime(2026, 1, 1, 10, 0, 0)
    target = now + timedelta(minutes=30)
    assert minutes_until(target, now) == 30
