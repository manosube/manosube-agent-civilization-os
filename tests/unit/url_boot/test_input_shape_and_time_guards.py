"""Malformed network/model input cannot become an observation or model identity."""

import pytest

from manosube_agent_civilization.model_runtime.engine import (
    require_valid_adapter_identity,
    require_valid_semantic_fingerprint,
    require_valid_timestamp as require_model_timestamp,
)
from manosube_agent_civilization.model_runtime.errors import ModelRuntimeRequirementError
from manosube_agent_civilization.runtime.deployment_declaration import (
    verify_runtime_deployment_declaration_signature,
)
from manosube_agent_civilization.runtime.root_admission import (
    verify_runtime_root_admission_signature,
)
from manosube_agent_civilization.url_boot.engine import (
    parse_utc_instant,
    require_valid_boundary,
    require_valid_source_identity,
    require_valid_timestamp,
)
from manosube_agent_civilization.url_boot.errors import UrlBootRequirementError


@pytest.mark.parametrize("validator", [require_valid_source_identity, require_valid_boundary])
@pytest.mark.parametrize("bad", [None, [], "not-a-mapping", {}])
def test_non_declared_source_and_boundary_shapes_are_refused(validator, bad):
    with pytest.raises(UrlBootRequirementError):
        validator(bad)


@pytest.mark.parametrize(
    "validator,error",
    [
        (require_valid_timestamp, UrlBootRequirementError),
        (require_model_timestamp, ModelRuntimeRequirementError),
    ],
)
@pytest.mark.parametrize("bad", [None, 0, "", "yesterday", "2026-09-10T00:00:00+02:00"])
def test_non_canonical_timestamps_cannot_replace_explicit_utc_time(validator, error, bad):
    with pytest.raises(error):
        validator(bad, "unit input")


@pytest.mark.parametrize("bad", ["not-a-time", "2026-02-30T00:00:00Z", "2026-09-10T00:00:00"])
def test_unreadable_or_naive_instants_are_refused(bad):
    with pytest.raises(UrlBootRequirementError):
        parse_utc_instant(bad, "unit input")


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {},
        {"adapter": "candidate", "version": ""},
        {"adapter": "candidate", "version": "1", "authority": "self-granted"},
    ],
)
def test_model_adapter_identity_requires_its_closed_declared_shape(bad):
    with pytest.raises(ModelRuntimeRequirementError):
        require_valid_adapter_identity(bad, "unit input")


@pytest.mark.parametrize("bad", [None, "sha256:unverified", {}, {"algorithm": "self-declared"}])
def test_an_unreadable_state_fingerprint_cannot_bind_model_work(bad):
    with pytest.raises(ModelRuntimeRequirementError):
        require_valid_semantic_fingerprint(bad, "unit input")


@pytest.mark.parametrize(
    "signature,key",
    [
        (None, {}),
        ([], {}),
        ({"algorithm": "hmac"}, {"algorithm": "hmac"}),
        (
            {"algorithm": "ed25519", "key_id": "foreign"},
            {"algorithm": "ed25519", "key_id": "trusted"},
        ),
        (
            {"algorithm": "ed25519", "key_id": "trusted", "value": []},
            {"algorithm": "ed25519", "key_id": "trusted", "public_key": "00" * 32},
        ),
        (
            {"algorithm": "ed25519", "key_id": "trusted", "value": "00" * 64},
            {"algorithm": "ed25519", "key_id": "trusted", "public_key": []},
        ),
    ],
)
def test_unverifiable_human_declaration_signature_is_false_before_payload_trust(signature, key):
    assert (
        verify_runtime_deployment_declaration_signature({"signature": signature}, signing_key=key)
        is False
    )


@pytest.mark.parametrize(
    "signature,anchor",
    [
        (None, "00" * 32),
        ([], "00" * 32),
        ({"algorithm": "hmac"}, "00" * 32),
        ({"algorithm": "ed25519", "value": []}, "00" * 32),
        ({"algorithm": "ed25519", "value": "00" * 64}, []),
    ],
)
def test_unverifiable_root_signature_cannot_admit_a_trust_anchor(signature, anchor):
    assert (
        verify_runtime_root_admission_signature(
            {"signature": signature}, trust_anchor_public_key_hex=anchor
        )
        is False
    )
