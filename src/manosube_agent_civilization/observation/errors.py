"""Fail-closed Observation Engine errors."""


class ObservationError(ValueError):
    """Base error for rejected Observation inputs or outputs."""


class UnsupportedProfileError(ObservationError):
    """The requested normalization profile is not implemented."""


class ScopeViolationError(ObservationError):
    """A source occurrence escaped the declared Observation scope."""


class ObservationValidationError(ObservationError):
    """Generated Observation records failed canonical conformance."""
