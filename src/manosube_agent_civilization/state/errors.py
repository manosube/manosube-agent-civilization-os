"""Fail-closed errors for canonical state processing."""


class CanonicalizationError(ValueError):
    """Base class for values that cannot become canonical."""


class UnsupportedValueError(CanonicalizationError):
    """A value has no representation in the v0.1 profile."""


class NonStringKeyError(CanonicalizationError):
    """A mapping contains a non-string key."""


class InvalidUnicodeError(CanonicalizationError):
    """A string is not valid Unicode for UTF-8 serialization."""


class AmbiguousCollectionError(CanonicalizationError):
    """A set-like collection contains duplicate canonical elements."""


class SecretFieldError(CanonicalizationError):
    """A forbidden secret-bearing field is present."""


class SchemaValidationError(CanonicalizationError):
    """Input does not satisfy the canonical JSON Schema."""


class FingerprintProfileError(CanonicalizationError):
    """A fingerprint uses an unsupported profile."""


class FingerprintMismatchError(CanonicalizationError):
    """A recorded fingerprint differs from the recomputed digest."""
