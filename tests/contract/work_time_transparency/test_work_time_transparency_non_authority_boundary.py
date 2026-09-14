"""Issue #22's own non-negotiable boundary, proved against the real production engines rather
than merely asserted in prose:

```text
TIMING_RECORD_NE_PROJECT_EVIDENCE=true
ESTIMATE_NE_AUTHORITY=true
ESTIMATE_NE_COMPLETION=true
HEARTBEAT_NE_HEALTH_PROOF=true
HEARTBEAT_NE_PHASE_COMPLETION=true
TERMINAL_NOTICE_NE_PROJECT_COMPLETION=true
TIMING_EVENT_CANNOT_CLOSE_DIFFERENCE=true
TIMING_EVENT_CANNOT_CLOSE_ISSUE=true
TIMING_EVENT_CANNOT_AUTHORIZE_MERGE=true
CANONICAL_TIMING_OWNER_COUNT=1
PARALLEL_TIMING_AUTHORITY_COUNT=0
```

A ``work_time_coordination_*`` record cannot become Difference/Evidence/Authority input
*structurally*, not merely by convention:

1. none of the three kinds are members of :data:`~manosube_agent_civilization.reflow.
   reference_registry.STORE_OWNED_REFERENCE_KINDS` -- the closed set Reflow's own Reference
   Closure gate recognizes as a resolvable target at all;
2. the real :func:`~manosube_agent_civilization.reflow.reference_registry.reference_edges`
   function refuses (fail-closed, before any Store resolution) a real ``closure_evaluation``
   body that names a ``work_time_coordination_terminal`` reference in a field whose closed kind
   set does not include it;
3. Evidence's own reference kind is a fixed module constant
   (:data:`~manosube_agent_civilization.evidence.engine.EVIDENCE_REFERENCE_KIND`, always
   ``"observation_evidence"``) -- there is no parameter through which a caller could substitute
   a ``work_time_coordination_*`` kind, so Evidence can never be built pointing at one;
4. this package's own production modules never import ``reflow``, ``evidence``, ``authority``,
   or ``difference.graph`` at all -- a real AST-level closure, not only a naming convention.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from manosube_agent_civilization.evidence.engine import EVIDENCE_REFERENCE_KIND
from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.reference_registry import (
    STORE_OWNED_REFERENCE_KINDS,
    reference_edges,
)
import manosube_agent_civilization.work_time_transparency.adapters as adapters_module
import manosube_agent_civilization.work_time_transparency.engine as engine_module
import manosube_agent_civilization.work_time_transparency.errors as errors_module
import manosube_agent_civilization.work_time_transparency.identity as identity_module
import manosube_agent_civilization.work_time_transparency.route as route_module
import manosube_agent_civilization.work_time_transparency.types as types_module

_WORK_TIME_TRANSPARENCY_KINDS = (
    "work_time_coordination_open",
    "work_time_coordination_update",
    "work_time_coordination_terminal",
)

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    adapters_module,
)


@pytest.mark.parametrize("kind", _WORK_TIME_TRANSPARENCY_KINDS)
def test_no_work_time_transparency_kind_is_a_store_owned_reference_target_for_reflow(
    kind: str,
) -> None:
    assert kind not in STORE_OWNED_REFERENCE_KINDS


def test_reference_edges_refuses_a_closure_evaluation_pointing_change_result_evidence_at_a_terminal_notice() -> (
    None
):
    body = {
        "kernel_source_witness_ref": None,
        "difference_event_head_ref": None,
        "after_state_candidate": None,
        "after_observation_refs": [],
        "change_result_evidence_refs": [
            {"kind": "work_time_coordination_terminal", "id": "WTC-TERMINAL-" + "0" * 64}
        ],
        "change_free_verification_evidence_refs": [],
        "evidence_sufficiency_ref": None,
        "terminal_reason_evidence_refs": [],
        "contradiction_refs": [],
        "candidate_invariant_evaluation_bindings": [],
        "candidate_claim_evaluation_bindings": [],
    }
    with pytest.raises(ReflowValidationError, match="not permitted here"):
        reference_edges("closure_evaluation", body)


def test_reference_edges_refuses_a_difference_event_pointing_evidence_refs_at_a_heartbeat_update() -> (
    None
):
    body = {
        "previous_event_id": None,
        "observation_refs": [],
        "evidence_refs": [
            {"kind": "work_time_coordination_update", "id": "WTC-UPDATE-" + "0" * 64}
        ],
        "closure_evaluation_ref": None,
        "revoked_evidence_refs": [],
        "invalid_evidence_refs": [],
        "contradiction_evidence_refs": [],
    }
    with pytest.raises(ReflowValidationError, match="not permitted here"):
        reference_edges("difference_event", body)


def test_evidence_reference_kind_is_a_fixed_constant_never_a_work_time_transparency_kind() -> None:
    assert EVIDENCE_REFERENCE_KIND == "observation_evidence"
    assert EVIDENCE_REFERENCE_KIND not in _WORK_TIME_TRANSPARENCY_KINDS


def test_no_work_time_transparency_module_imports_reflow_evidence_authority_or_difference_graph() -> (
    None
):
    forbidden_prefixes = (
        "manosube_agent_civilization.reflow",
        "manosube_agent_civilization.evidence",
        "manosube_agent_civilization.authority",
        "manosube_agent_civilization.difference.graph",
    )
    for module in _ALL_PACKAGE_MODULES:
        tree = ast.parse(inspect.getsource(module))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        offending = {
            name
            for name in imported
            if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
        }
        assert not offending, (
            f"{module.__name__} imports a Difference/Evidence/Authority module: {offending}"
        )
