"""Typed errors for the Long-Running Proof Artifact Bundle package (Issue #86, P87-R1-F8)."""

from __future__ import annotations


class ArtifactBundleError(Exception):
    """Base class for every error this package raises."""


class ArtifactBundleValidationError(ArtifactBundleError):
    """A caller-supplied value is malformed, out of range, or fails the bundle's own schema."""


__all__ = ["ArtifactBundleError", "ArtifactBundleValidationError"]
