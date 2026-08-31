"""Fail-closed Difference Engine errors."""


class DifferenceError(ValueError):
    """Base error for rejected Difference derivation inputs or outputs."""


class UnsupportedProfileError(DifferenceError):
    """A declared identity, comparison or normalization profile is not implemented."""


class BoundaryViolationError(DifferenceError):
    """A subject, source or reference escaped the declared effective boundary."""


class SecurityRejectionError(DifferenceError):
    """A secret-bearing field or a moving reference was supplied."""


class IdentityCollisionError(DifferenceError):
    """The same canonical identity was presented with a different semantic payload."""


class DifferenceValidationError(DifferenceError):
    """Generated Difference records failed canonical schema or conformance validation."""
