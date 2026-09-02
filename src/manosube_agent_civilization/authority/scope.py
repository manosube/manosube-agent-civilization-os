"""Scope containment and overlap, with the asymmetry that makes fail-closed work.

Permission asks **containment**: a request is allowed only where it fits entirely inside the
scope that allows it. Prohibition asks **overlap**: a request is refused where it touches any
part of a refused scope. The two are deliberately different operators, and using one for the
other is how a partially-forbidden request becomes partially allowed.

```text
PERMISSION   requested ⊆ granted
PROHIBITION  requested ∩ forbidden ≠ ∅
```
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.admissibility import (
    require_collection,
    require_object,
    require_scalar_tag,
)

from .errors import AuthorityError

#: Every key a canonical scope carries. Closed: an unknown key is a scope this evaluator
#: cannot reason about, and a scope it cannot reason about is not one it may approve.
SCOPE_KEYS: tuple[str, ...] = ("repository", "branch", "paths", "subjects")

#: The two enumerated members. ``repository`` and ``branch`` are single tags.
SCOPE_COLLECTIONS: tuple[str, ...] = ("paths", "subjects")


def require_scope(value: Any, context: str) -> dict[str, Any]:
    """Return *value* once it can be read as a canonical scope; reject it otherwise.

    A scope that cannot be enumerated is not narrowed to something safe -- it is refused.
    ``AUTHORITY_CONTRACT.md`` §3: an unresolved glob, an unresolved symlink or an implicit
    recursive root is not a scope this evaluator accepts as an input.
    """

    scope = require_object(value, context)
    unknown = set(scope) - set(SCOPE_KEYS)
    if unknown:
        raise AuthorityError(f"{context} carries unknown scope keys: {sorted(unknown)}")
    missing = [key for key in SCOPE_KEYS if key not in scope]
    if missing:
        raise AuthorityError(f"{context} omits a required scope key: {missing[0]}")
    require_scalar_tag(scope["repository"], f"{context} repository")
    require_scalar_tag(scope["branch"], f"{context} branch")
    for key in SCOPE_COLLECTIONS:
        members = require_collection(scope[key], f"{context} {key}")
        for position, member in enumerate(members):
            require_scalar_tag(member, f"{context} {key}[{position}]")
    return scope


def _same_location(requested: dict[str, Any], other: dict[str, Any]) -> bool:
    return bool(
        requested["repository"] == other["repository"]
        and requested["branch"] == other["branch"]
    )


def is_contained(requested: dict[str, Any], granted: dict[str, Any]) -> bool:
    """Whether every member of *requested* lies inside *granted*.

    Membership is exact. A prefix is not containment: granting ``src/`` does not grant
    ``src/../etc``, and the evaluator does not resolve one into the other -- an unresolved
    path is refused upstream rather than interpreted here.
    """

    if not _same_location(requested, granted):
        return False
    if not requested["paths"] and not requested["subjects"]:
        return False
    return all(
        set(requested[key]) <= set(granted[key])
        for key in SCOPE_COLLECTIONS
    )


def overlaps(requested: dict[str, Any], forbidden: dict[str, Any]) -> bool:
    """Whether *requested* touches any part of *forbidden*.

    One shared path is enough. A request that reaches a forbidden location is refused whole,
    not trimmed to its permitted remainder -- ``PROHIBITION_CONTRACT.md`` §5.
    """

    if not _same_location(requested, forbidden):
        return False
    return any(
        set(requested[key]) & set(forbidden[key])
        for key in SCOPE_COLLECTIONS
    )
