"""Fail-closed development-binding errors.

A policy that cannot be read is not a policy that permits. Every failure here is a refusal,
never a pass-through: the guard exists because a permissive default is exactly how the
incident it prevents happened.
"""


class DevelopmentBindingError(ValueError):
    """Base error for a development-binding policy that cannot be read or trusted."""


class PolicyIntegrityError(DevelopmentBindingError):
    """The policy artifact is absent, unreadable, or not the closed shape declared."""


class AdoptionRecordError(DevelopmentBindingError):
    """A Governance Adoption Record is absent, unreadable, or not the closed shape declared.

    Raised for an *unreadable* record only -- the wrong Python shape, an unknown key, a
    missing required key, or a field of the wrong type. A record that is readable but does
    not admit (an unverified URL, an unconfirmed read-back, a mismatched reviewed SHA) is
    never an exception; see :func:`.adoption_record.evaluate_adoption_record`.
    """
