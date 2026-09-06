"""The one immutable, non-authoritative Boot Context (Phase 10, Issue #45).

``BootContext`` is an ephemeral in-memory projection -- never a second canonical record,
never persisted, grants no Authority and closes no Difference (frozen semantic decision 7).

Immutability covers the **full accepted graph**, not merely each field's own outer mapping
(Phase 10 Structural Review Round 1, P10-R1-F1): :func:`_deep_freeze` recursively rebuilds
every nested mapping as a new ``types.MappingProxyType`` and every nested list/tuple as a new
``tuple``, bottom-up, so the returned structure shares no mutable container with the body a
caller (or the Store) supplied -- a caller cannot mutate a nested field of a ``BootContext``
it holds, and mutating the original resolved body after boot cannot retroactively change a
``BootContext`` already returned. The dataclass itself is ``frozen=True`` so no field can be
reassigned either.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _deep_freeze(value: Any) -> Any:
    """Recursively rebuild *value* into an immutable, alias-free equivalent.

    ``mapping -> MappingProxyType`` over a freshly built ``dict`` of recursively frozen
    values; ``list``/``tuple`` -> a freshly built ``tuple`` of recursively frozen elements;
    anything else (``str``, ``int``, ``float``, ``bool``, ``None``) is returned as-is --
    every JSON-compatible scalar is already immutable. Every container along the way is a
    new object, never the caller's own, so no later mutation of the original body -- or of
    the frozen result, which mutation itself cannot succeed against -- crosses between them.
    """

    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(_deep_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class BootContext:
    """The verified, restored projection ``boot_project`` returns.

    Carries the reverified Project Binding, its resolved Objective Revision and Authority
    Rule, and current State reconstructed from canonical lineage -- exactly the references a
    caller needs to begin a Phase 8 Reflow cycle, and nothing this route itself mutated,
    minted, or persisted.
    """

    project_id: str
    project_binding: Mapping[str, Any]
    project_binding_id: str
    objective_revision: Mapping[str, Any]
    objective_revision_id: str
    authority_rule: Mapping[str, Any]
    authority_rule_id: str
    current_state: Mapping[str, Any]
    human_authority_ref: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_binding", _deep_freeze(self.project_binding))
        object.__setattr__(self, "objective_revision", _deep_freeze(self.objective_revision))
        object.__setattr__(self, "authority_rule", _deep_freeze(self.authority_rule))
        object.__setattr__(self, "current_state", _deep_freeze(self.current_state))
        object.__setattr__(self, "human_authority_ref", _deep_freeze(self.human_authority_ref))
