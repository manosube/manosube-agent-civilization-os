"""Fail-closed Change errors.

The distinction ADR-0013 draws for Difference, and ``authority/errors.py`` for Authority,
holds here too. An input that cannot be *read* is not a Change question: there is nothing to
derive, so it raises. And a Change that is not *authorized* is not a malformed input -- it is
a correctly-formed request that Authority did not permit, which is equally a refusal because
Change has no third answer. A Change record is emitted only when one may be.
"""


class ChangeError(ValueError):
    """Base error for a raw Change input that cannot be read, or a Change that may not be."""


class ChangeValidationError(ChangeError):
    """A record failed its canonical schema."""


class UnauthorizedChangeError(ChangeError):
    """The bound Authority decision does not permit this Change.

    ``HUMAN_APPROVAL_REQUIRED`` and ``PROHIBITED`` both land here. Neither is a defect in the
    request: both are Authority's answer, and deriving a Change from either would be Change
    overruling the evaluator it is supposed to obey (``KERNEL_CONSTITUTION.md`` 第21条).
    """


class StaleChangeError(ChangeError):
    """The bound inputs describe a State the request no longer describes.

    ``KERNEL_CONSTITUTION.md`` 第26条: a Change whose expected revision is not the revision it
    was authorized against is stale, and a stale Change is blocked rather than adjusted.
    """


class ChangeBoundaryViolationError(ChangeError):
    """Two supplied inputs disagree about what this Change is bound to."""
