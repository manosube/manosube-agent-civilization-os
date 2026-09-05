"""Fail-closed Reflow errors.

The same shape Change and Evidence use, for the same reason: a raw input Reflow cannot
*read* is not a Reflow question, and a Reflow that would not be *permitted* is not a
malformed input. Reflow has no third answer -- a request either produces the one canonical
Reflow decision, or it is refused.
"""


class ReflowError(ValueError):
    """Base error for a raw Reflow input that cannot be read, or a Reflow that may not be."""


class ReflowValidationError(ReflowError):
    """A record failed its canonical schema."""


class StaleReflowError(ReflowError):
    """The bound State/Difference/Evidence inputs no longer describe the current head.

    ``KERNEL_INVARIANTS.md`` R-003: a Reflow whose expected revision is not the State
    Store's current revision, whose Closure Evaluation has passed its
    ``evaluation_expires_at``, or whose lifecycle event head has moved is stale and is
    blocked rather than silently rebased onto the new head.
    """


class UnauthorizedReflowError(ReflowError):
    """A Change-bound route's Authority decision does not permit the Change it cites."""
