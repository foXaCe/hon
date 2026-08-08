"""Typed exceptions raised by the hOn API client."""

from __future__ import annotations


class HonError(Exception):
    """Base exception for hOn errors."""


class HonAuthenticationError(HonError):
    """Raised when the hOn credentials are invalid or expired."""


class HonConnectionError(HonError):
    """Raised when the hOn API is unreachable."""


class HonRateLimitError(HonError):
    """Raised when the hOn API throttles the request (HTTP 429)."""
