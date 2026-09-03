"""Fail-closed development-binding errors.

A policy that cannot be read is not a policy that permits. Every failure here is a refusal,
never a pass-through: the guard exists because a permissive default is exactly how the
incident it prevents happened.
"""


class DevelopmentBindingError(ValueError):
    """Base error for a development-binding policy that cannot be read or trusted."""


class PolicyIntegrityError(DevelopmentBindingError):
    """The policy artifact is absent, unreadable, or not the closed shape declared."""
