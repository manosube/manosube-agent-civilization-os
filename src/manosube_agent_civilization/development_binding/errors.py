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


class ExecutorSelectionError(DevelopmentBindingError):
    """An Executor Selection Record is absent, unreadable, or not the closed shape declared.

    Raised for an *unreadable* record only, following the same grammar as
    :class:`AdoptionRecordError`. A record that is readable but does not admit (an unknown
    provider, a scope or SHA mismatch, a missing read-back) is never an exception; see
    :func:`.executor_selection.evaluate_executor_selection`.
    """


class ReviewSelectionError(DevelopmentBindingError):
    """A Bounded Review Grant is absent, unreadable, or not the closed shape declared
    (Decision 0004, Issue #109).

    Raised for an *unreadable* record only, following the identical grammar as
    :class:`ExecutorSelectionError` and :class:`AdoptionRecordError`. A record that is
    readable but does not admit (expired, revoked, a scope mismatch, an unsupported CLI/model
    fingerprint, a missing read-back) is never an exception; see
    :func:`.review_selection.evaluate_review_selection`.
    """


class ReviewAdapterError(DevelopmentBindingError):
    """The one external-effect adapter (Decision 0004, Issue #109) was asked to do something
    its own boundary refuses: name a credential-shaped environment variable as allowed, copy
    an unsafe or non-existent inspection path into a temporary workspace, or any other
    programming-error-shaped misuse of :mod:`.review_adapter`'s own functions. Never raised
    for an ordinary process outcome (non-zero exit, timeout, truncated output) -- those are
    the adapter's own result fields, not exceptions.
    """


class ReviewControlError(DevelopmentBindingError):
    """The Bounded Review Control ledger is unreadable, corrupt, or was asked to record an
    operation its own state machine does not recognise (Decision 0004, Issue #109).

    Unlike :class:`ReviewSelectionError`, this is raised for operational-ledger integrity
    failures, never for an ordinary claim refusal (duplicate identity, concurrency, daily
    ceiling) -- those are :func:`.review_control.claim_review_launch`'s own
    ``REVIEW_CLAIM_REFUSED`` decision, with reason codes, exactly as an inadmissible grant is
    never an exception in :mod:`.review_selection`.
    """
