"""Observation scope and source-locator enforcement."""

from __future__ import annotations

import re
from typing import Any

from .errors import ScopeViolationError

_SECRET = re.compile(r"(?:password|token|secret|credential)", re.IGNORECASE)


def validate_scope(scope: dict[str, Any], project_id: str, target_identity: str) -> None:
    if scope.get("project_id") != project_id:
        raise ScopeViolationError("scope project_id does not match Observation project")
    if scope.get("target_identity") != target_identity:
        raise ScopeViolationError("scope target_identity does not match Observation target")
    if scope.get("scope_status") not in {
        "COMPLETE",
        "INCOMPLETE",
        "UNOBSERVED",
        "BLOCKED",
        "INVALID",
        "CONFLICTED",
    }:
        raise ScopeViolationError("scope status is unknown")


def subject_in_scope(subject: str, scope: dict[str, Any]) -> bool:
    included = set(scope["included_subjects"])
    excluded = set(scope["excluded_subjects"])
    return subject in included and subject not in excluded


def validate_source_locator(locator: str) -> None:
    if not locator or locator.startswith("/") or "://" in locator:
        raise ScopeViolationError("source locator must be a non-empty relative locator")
    if ".." in locator.split("/"):
        raise ScopeViolationError("source locator escapes the declared boundary")
    if _SECRET.search(locator):
        raise ScopeViolationError("source locator may expose secret-bearing material")
    if "\n" in locator or "\r" in locator:
        raise ScopeViolationError("source locator contains a line break")
