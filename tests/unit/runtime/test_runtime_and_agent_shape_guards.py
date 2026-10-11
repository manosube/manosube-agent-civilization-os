"""Unverified runtime/agent bodies must fail canonical preflight admission."""

import pytest

from manosube_agent_civilization.multi_agent import engine as multi_engine
from manosube_agent_civilization.multi_agent.errors import MultiAgentRequirementError
from manosube_agent_civilization.runtime import engine as runtime_engine
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError


@pytest.mark.parametrize(
    "validator,error",
    [
        (runtime_engine.require_valid_target_identity, RuntimeRequirementError),
        (runtime_engine.require_valid_boundary, RuntimeRequirementError),
        (runtime_engine.require_valid_deployment_declaration, RuntimeRequirementError),
        (runtime_engine.require_valid_root_admission, RuntimeRequirementError),
        (multi_engine.require_valid_multi_agent_dynamic_execution_plan, MultiAgentRequirementError),
        (multi_engine.require_valid_multi_agent_slot_output, MultiAgentRequirementError),
        (
            multi_engine.require_valid_multi_agent_slot_attempt_envelope_claim,
            MultiAgentRequirementError,
        ),
        (multi_engine.require_valid_multi_agent_agent_release_receipt, MultiAgentRequirementError),
        (multi_engine.require_valid_multi_agent_conflict_set, MultiAgentRequirementError),
        (
            multi_engine.require_valid_multi_agent_evidence_aggregation_input,
            MultiAgentRequirementError,
        ),
        (multi_engine.require_valid_multi_agent_orchestration_receipt, MultiAgentRequirementError),
    ],
)
@pytest.mark.parametrize("bad", [None, [], {}, {"authority": "self-granted"}])
def test_lookup_bodies_require_their_full_canonical_schema(validator, error, bad):
    with pytest.raises(error):
        validator(bad)


@pytest.mark.parametrize(
    "validator,error",
    [
        (runtime_engine.require_valid_timestamp, RuntimeRequirementError),
        (multi_engine.require_valid_timestamp, MultiAgentRequirementError),
        (multi_engine.require_valid_semantic_fingerprint, MultiAgentRequirementError),
        (multi_engine.require_valid_adapter_identity, MultiAgentRequirementError),
    ],
)
@pytest.mark.parametrize("bad", [None, [], {}, "unverified"])
def test_preflight_refuses_unreadable_bindings(validator, error, bad):
    with pytest.raises(error):
        validator(bad, "unit preflight")


@pytest.mark.parametrize("bad", ["not-a-time", "2026-02-30T00:00:00Z", "2026-09-10T00:00:00"])
def test_window_comparison_requires_a_real_utc_instant(bad):
    with pytest.raises(RuntimeRequirementError):
        runtime_engine.parse_utc_instant(bad, "unit preflight")
