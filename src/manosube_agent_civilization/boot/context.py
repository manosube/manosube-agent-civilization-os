"""The one immutable, non-authoritative Boot Context (Phase 10, Issue #45).

``BootContext`` is an ephemeral in-memory projection -- never a second canonical record,
never persisted, grants no Authority and closes no Difference (frozen semantic decision 7).
Its mapping fields are wrapped in ``types.MappingProxyType`` so a caller holding a
``BootContext`` cannot mutate what :func:`~manosube_agent_civilization.boot.route.boot_project`
verified and mistake the mutated copy for a re-verified one; the dataclass itself is
``frozen=True`` so no field can be reassigned either.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _frozen(body: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(body))


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
        object.__setattr__(self, "project_binding", _frozen(self.project_binding))
        object.__setattr__(self, "objective_revision", _frozen(self.objective_revision))
        object.__setattr__(self, "authority_rule", _frozen(self.authority_rule))
        object.__setattr__(self, "current_state", _frozen(self.current_state))
        object.__setattr__(self, "human_authority_ref", _frozen(self.human_authority_ref))
