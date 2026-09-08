"""Phase 14 (Issue #62), Structural Review Round 6 (P14-R6-F2): genuine, verified SHUKOU/
Human Authority for V3 live-write execution -- entirely offline, zero network access, zero
Store/adapter dependency. Structural Review Round 7 (P14-R7-F1): the live trust anchor
(:data:`~tests.fixtures.v3_live_write_authority.V3_LIVE_TRUST_ANCHOR`) has no matching private
key anywhere in this repository; every genuinely signed record this file constructs uses the
dedicated, structurally separate test-only signer
(:mod:`tests.fixtures.v3_live_write_authority_test_signer`), and every
:func:`~tests.fixtures.v3_live_write_authority.v3_live_write_authorized` call below passes its
own explicit, test-only ``trust_anchor`` -- never the live one -- proving the pure verification
logic itself, not the (structurally separate, see
``tests/contract/projection/test_v3_live_write_authority_static_conformance.py``) trust-anchor
boundary.

Every negative control here proves :func:`v3_live_write_authorized` fails closed (returns
``False``, never raises) before any network access could ever occur -- a caller-computable
configuration digest, a bare credential, or an environment-variable's mere presence never
grants this authority; only a genuine Ed25519 signature over the exact bound fields, verified
against the caller's own explicitly supplied trust anchor, does. No test in this file
constructs a ``RealGitHubAdapter`` or touches ``urllib``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from tests.fixtures.v3_live_write_authority import (
    V3_LIVE_TRUST_ANCHOR,
    V3_LIVE_WRITE_AUTHORITY_RECORD_ENV,
    V3_LIVE_WRITE_PERMITTED_ACTION,
    V3LiveWriteAuthorityError,
    load_v3_live_write_authority_record,
    v3_live_write_authority_signing_payload,
    v3_live_write_authorized,
)
from tests.fixtures.v3_live_write_authority_test_signer import (
    V3_TEST_TRUST_ANCHOR,
    assemble_v3_live_write_authority_for_test,
    sign_v3_live_write_authority_for_test,
)
from tests.fixtures.v3_target_configuration import V3TargetConfiguration

_CONFIG = V3TargetConfiguration(
    owner="acme",
    repo="widget",
    token="test-token-not-a-real-secret",  # noqa: S106
    change_head_ref="agent/frozen-v3-branch",
    change_base_ref="main",
    evidence_head_sha="0123456789abcdef0123456789abcdef01234567",
    artifact_naming_prefix="MANOSUBE V3 proof (do not merge)",
    cleanup_confirmed=True,
    no_merge_confirmed=True,
    authorized_artifact_kinds=frozenset({"issue", "pull_request", "check_run"}),
    authorized_artifact_count=3,
)

_EVALUATION_TIME = "2026-09-08T12:00:00Z"


def _genuine_record(**overrides: object) -> dict[str, Any]:
    kwargs = {
        "configuration_fingerprint": _CONFIG.configuration_fingerprint,
        "target_repository": _CONFIG.target_repository,
        "authorized_artifact_kinds": _CONFIG.authorized_artifact_kinds,
        "authorized_artifact_count": _CONFIG.authorized_artifact_count,
        "valid_from": "2026-09-08T00:00:00Z",
        "valid_until": "2026-09-09T00:00:00Z",
    }
    kwargs.update(overrides)
    return assemble_v3_live_write_authority_for_test(**kwargs)  # type: ignore[arg-type]


def _authorized(
    config: V3TargetConfiguration | None,
    record: object,
    *,
    evaluation_time: str = _EVALUATION_TIME,
) -> bool:
    """Call :func:`v3_live_write_authorized` with the test-only trust anchor, the one every
    test in this file exercises the pure verification logic against -- never the live one."""

    return v3_live_write_authorized(
        config,
        record,  # type: ignore[arg-type]
        evaluation_time=evaluation_time,
        trust_anchor=V3_TEST_TRUST_ANCHOR,
    )


# ---------------------------------------------------------------------------
# Positive route
# ---------------------------------------------------------------------------


def test_genuine_record_authorizes_the_exact_configuration_it_was_signed_for() -> None:
    record = _genuine_record()
    assert _authorized(_CONFIG, record) is True


def test_config_none_or_record_none_refuses_immediately() -> None:
    record = _genuine_record()
    assert _authorized(None, record) is False
    assert _authorized(_CONFIG, None) is False
    assert _authorized(None, None) is False


# ---------------------------------------------------------------------------
# Structural Review Round 7 (P14-R7-F1): the live trust anchor has no matching private key --
# a record genuinely signed by the test-only signer must never verify under it, and the pure
# verifier must require an explicit trust anchor rather than silently defaulting to one.
# ---------------------------------------------------------------------------


def test_record_signed_by_the_test_signer_never_verifies_under_the_live_trust_anchor() -> None:
    """The exact regression Round 7 corrects: even a byte-for-byte genuine, fully valid,
    correctly bound record is refused once verified against the live trust anchor, because no
    signature the test signer ever produces can validate against a public key it holds no
    matching private key for."""

    record = _genuine_record()
    assert (
        v3_live_write_authorized(
            _CONFIG, record, evaluation_time=_EVALUATION_TIME, trust_anchor=V3_LIVE_TRUST_ANCHOR
        )
        is False
    )


def test_trust_anchor_is_a_required_keyword_only_argument() -> None:
    """No default trust anchor exists to silently fall back to -- omitting ``trust_anchor``
    entirely is a ``TypeError``, not a quietly-accepted call."""

    record = _genuine_record()
    with pytest.raises(TypeError):
        v3_live_write_authorized(_CONFIG, record, evaluation_time=_EVALUATION_TIME)  # type: ignore[call-arg]


def test_live_and_test_trust_anchors_are_structurally_distinct() -> None:
    assert V3_LIVE_TRUST_ANCHOR["key_id"] != V3_TEST_TRUST_ANCHOR["key_id"]
    assert V3_LIVE_TRUST_ANCHOR["public_key"] != V3_TEST_TRUST_ANCHOR["public_key"]


# ---------------------------------------------------------------------------
# Required negative controls (Structural Review Round 6, P14-R6-F2): fabricated, stale,
# wrong-fingerprint, wrong-target, wrong-action, widened-boundary.
# ---------------------------------------------------------------------------


def test_fabricated_unsigned_record_refuses() -> None:
    record = _genuine_record()
    record = {
        **record,
        "signature": {
            "algorithm": "ed25519",
            "key_id": V3_TEST_TRUST_ANCHOR["key_id"],
            "value": "00" * 64,
        },
    }
    assert _authorized(_CONFIG, record) is False


def test_fabricated_record_missing_signature_entirely_refuses() -> None:
    record = _genuine_record()
    del record["signature"]
    assert _authorized(_CONFIG, record) is False


def test_fabricated_record_with_tampered_field_after_signing_refuses() -> None:
    """The signature covers the record's own content -- altering any bound field *after*
    signing, even without touching the signature bytes themselves, must invalidate it."""

    record = dict(_genuine_record())
    record["authorized_artifact_count"] = 999
    assert _authorized(_CONFIG, record) is False


def test_stale_record_past_its_own_valid_until_refuses() -> None:
    record = _genuine_record(valid_until="2026-09-08T11:00:00Z")
    assert _authorized(_CONFIG, record) is False


def test_record_not_yet_valid_refuses() -> None:
    record = _genuine_record(valid_from="2026-09-08T13:00:00Z")
    assert _authorized(_CONFIG, record) is False


def test_wrong_fingerprint_refuses() -> None:
    record = _genuine_record(configuration_fingerprint="sha256:" + "0" * 64)
    assert _authorized(_CONFIG, record) is False


def test_wrong_target_repository_refuses() -> None:
    record = _genuine_record(
        target_repository={"host": "github", "owner": "acme", "repo": "a-different-widget"}
    )
    assert _authorized(_CONFIG, record) is False


def test_wrong_action_refuses() -> None:
    record = _genuine_record(permitted_action="MATERIALIZE_SOMETHING_ELSE")
    assert _authorized(_CONFIG, record) is False


def test_widened_artifact_count_boundary_refuses() -> None:
    """A genuinely signed record naming a *larger* authorized count than this configuration's
    own bound value must never be treated as authorizing this configuration -- exact equality
    only, never "at least"."""

    record = _genuine_record(authorized_artifact_count=10)
    assert _authorized(_CONFIG, record) is False


def test_widened_artifact_kinds_boundary_refuses() -> None:
    record = _genuine_record(authorized_artifact_kinds=frozenset({"issue"}))
    assert _authorized(_CONFIG, record) is False


def test_unconfirmed_cleanup_boundary_refuses() -> None:
    record = _genuine_record(cleanup_confirmed=False)
    assert _authorized(_CONFIG, record) is False


def test_unconfirmed_no_merge_boundary_refuses() -> None:
    record = _genuine_record(no_merge_confirmed=False)
    assert _authorized(_CONFIG, record) is False


def test_revoked_status_refuses() -> None:
    record = _genuine_record(status="REVOKED")
    assert _authorized(_CONFIG, record) is False


def test_signed_by_a_different_key_id_refuses() -> None:
    record = dict(_genuine_record())
    record["signature"] = {**record["signature"], "key_id": "SOME-OTHER-KEY"}
    assert _authorized(_CONFIG, record) is False


def test_wrong_signature_algorithm_refuses() -> None:
    record = dict(_genuine_record())
    record["signature"] = {**record["signature"], "algorithm": "hmac-sha256"}
    assert _authorized(_CONFIG, record) is False


@pytest.mark.parametrize("malformed_signature", [None, "not-a-dict", 12345, []])
def test_malformed_signature_shape_refuses(malformed_signature: object) -> None:
    record = dict(_genuine_record())
    record["signature"] = malformed_signature
    assert _authorized(_CONFIG, record) is False


def test_authorized_artifact_kinds_not_a_list_refuses() -> None:
    record = dict(_genuine_record())
    record["authorized_artifact_kinds"] = "issue,pull_request,check_run"
    assert _authorized(_CONFIG, record) is False


# ---------------------------------------------------------------------------
# A caller-computable configuration digest alone is not authority (Structural Review Round 6,
# distinguishing this correction from Round 5's own superseded mechanism).
# ---------------------------------------------------------------------------


def test_the_bare_configuration_fingerprint_string_alone_is_not_a_valid_authority_record() -> None:
    """The exact regression this finding corrects: a caller who can compute
    ``config.configuration_fingerprint`` (a value derivable from the frozen configuration
    alone, no Human Authority required) must not be able to construct anything resembling an
    authority record from that digest alone -- it is not even a mapping, let alone signed."""

    bare_digest = _CONFIG.configuration_fingerprint
    assert _authorized(_CONFIG, bare_digest) is False


def test_a_hand_built_record_naming_every_correct_field_but_never_signed_refuses() -> None:
    """Getting every bound field byte-for-byte correct is still not authority without the one
    thing this whole mechanism actually requires: a genuine signature by the trusted key."""

    unsigned = {
        "schema_version": "0.1",
        "configuration_fingerprint": _CONFIG.configuration_fingerprint,
        "target_repository": _CONFIG.target_repository,
        "permitted_action": V3_LIVE_WRITE_PERMITTED_ACTION,
        "authorized_artifact_kinds": sorted(_CONFIG.authorized_artifact_kinds),
        "authorized_artifact_count": _CONFIG.authorized_artifact_count,
        "cleanup_confirmed": True,
        "no_merge_confirmed": True,
        "status": "ACTIVE",
        "valid_from": "2026-09-08T00:00:00Z",
        "valid_until": "2026-09-09T00:00:00Z",
    }
    assert _authorized(_CONFIG, unsigned) is False


# ---------------------------------------------------------------------------
# Signing/assembly helpers (test-only signer) and the public verification key
# ---------------------------------------------------------------------------


def test_signing_payload_is_deterministic_and_excludes_the_signature_itself() -> None:
    record = _genuine_record()
    payload_a = v3_live_write_authority_signing_payload(record)
    payload_b = v3_live_write_authority_signing_payload(
        {**record, "signature": {"different": True}}
    )
    assert payload_a == payload_b


def test_signing_payload_raises_on_a_missing_required_field() -> None:
    record = dict(_genuine_record())
    del record["status"]
    with pytest.raises(V3LiveWriteAuthorityError):
        v3_live_write_authority_signing_payload(record)


def test_sign_v3_live_write_authority_uses_the_test_only_trust_anchors_key_id() -> None:
    record = _genuine_record()
    assert record["signature"]["key_id"] == V3_TEST_TRUST_ANCHOR["key_id"]
    assert record["signature"]["algorithm"] == "ed25519"


def test_assemble_defaults_to_the_one_closed_permitted_action() -> None:
    record = _genuine_record()
    assert record["permitted_action"] == V3_LIVE_WRITE_PERMITTED_ACTION


def test_two_records_signed_for_the_identical_fields_carry_the_identical_signature() -> None:
    record_a = _genuine_record()
    record_b = _genuine_record()
    assert record_a["signature"]["value"] == record_b["signature"]["value"]


def test_sign_v3_live_write_authority_for_test_is_a_standalone_re_signable_helper() -> None:
    record = dict(_genuine_record())
    resigned = sign_v3_live_write_authority_for_test(record)
    assert resigned == record["signature"]


# ---------------------------------------------------------------------------
# load_v3_live_write_authority_record: the one I/O boundary this module has -- an
# environment-variable read, never a network call.
# ---------------------------------------------------------------------------


def test_load_returns_none_when_unset() -> None:
    assert load_v3_live_write_authority_record(env={}) is None


def test_load_returns_none_on_malformed_json() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_RECORD_ENV: "{not valid json"}
    assert load_v3_live_write_authority_record(env=env) is None


def test_load_returns_none_when_json_is_not_an_object() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_RECORD_ENV: "[1, 2, 3]"}
    assert load_v3_live_write_authority_record(env=env) is None


def test_load_returns_the_decoded_record_when_well_formed() -> None:
    import json

    record = _genuine_record()
    env = {V3_LIVE_WRITE_AUTHORITY_RECORD_ENV: json.dumps(record)}
    loaded = load_v3_live_write_authority_record(env=env)
    assert loaded == record


def test_load_default_env_source_is_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    record = _genuine_record()
    monkeypatch.setenv(V3_LIVE_WRITE_AUTHORITY_RECORD_ENV, json.dumps(record))
    assert load_v3_live_write_authority_record() == record


def test_end_to_end_load_then_authorize_round_trips_through_json() -> None:
    import json

    record = _genuine_record()
    env = {V3_LIVE_WRITE_AUTHORITY_RECORD_ENV: json.dumps(record)}
    loaded = load_v3_live_write_authority_record(env=env)
    assert _authorized(_CONFIG, loaded) is True


def test_a_configuration_field_change_invalidates_a_previously_genuine_record() -> None:
    """The same binding proof Round 5 already established for the (now superseded) digest
    mechanism, re-proven here for the genuine signed record: changing any one bound
    configuration field invalidates an authority record that was genuine for the original."""

    record = _genuine_record()
    assert _authorized(_CONFIG, record) is True

    changed_config = replace(_CONFIG, repo="a-different-widget")
    assert _authorized(changed_config, record) is False
