"""Fail-closed Authority errors.

Two kinds of failure are distinct here, and the distinction is ADR-0013's.

An input that cannot be *read* is not a permission question: there is nothing to decide, so
it raises. An input that is readable and *wrong* -- a stale approval, a scope that widens, a
rule that does not match -- is a permission question with a canonical answer, so it produces
a decision rather than an exception. Collapsing the two would let an unreadable request look
like a refusal, and a refusal look like a crash.
"""


class AuthorityError(ValueError):
    """Base error for a raw Authority input that cannot be read at all."""


class AuthorityValidationError(AuthorityError):
    """A record failed its canonical schema."""


class BoundaryViolationError(AuthorityError):
    """An input belongs to a different project than the one being evaluated."""


class StaleAuthorityInputError(AuthorityError):
    """The Difference is bound to a State the request no longer describes.

    Not a decision. The request describes a world that has moved, so re-observation and a
    fresh evaluation are required rather than a permission answer over stale facts --
    ``AUTHORITY_CONTRACT.md`` §5.
    """
