"""Errors raised when a domain command violates a business invariant."""


class DomainError(Exception):
    """Base class for expected commercial rule rejections."""


class InvariantViolation(DomainError):
    """The requested state would violate a domain invariant."""


class InvalidTransition(DomainError):
    """The aggregate cannot make the requested lifecycle transition."""

