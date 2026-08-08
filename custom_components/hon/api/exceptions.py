"""Typed exceptions raised by the hOn API client."""

from __future__ import annotations


class HonError(Exception):
    """Base exception for hOn errors."""


class HonAuthenticationError(HonError):
    """Raised when the hOn credentials are invalid or expired."""


class HonPasswordChangeRequiredError(HonAuthenticationError):
    """Raised when the hOn account requires a password change.

    hOn redirects the OAuth authorize step to a ``ChangePassword`` page when
    the credentials are valid but a password reset is mandatory. Surfacing
    this instead of a generic "wrong password" error tells the user to reset
    their password.
    """


class HonConnectionError(HonError):
    """Raised when the hOn API is unreachable."""


class HonRateLimitError(HonError):
    """Raised when the hOn API throttles the request (HTTP 429)."""
