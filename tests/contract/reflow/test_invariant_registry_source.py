"""The pinned v0.1 mandatory Invariant id union is the union the live Kernel declares.

``CLOSURE_POLICY.md``'s G19 section requires the expected id set to be resolved from
``00_KERNEL/KERNEL_INVARIANTS.md``'s ``# 16. v0.1 Mandatory Gate`` fenced block by content
address. A pure evaluator cannot open a file, so the obligation is split the same way
``tests/contract/evidence/test_evidence_level_scale_source.py`` already splits it for the
Evidence Level scale: :mod:`manosube_agent_civilization.reflow.invariant_registry` pins the
parsed id tuple and the section's own digest; this test re-parses the *live* document with
the same grammar the module exposes and proves neither pin has drifted from it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from manosube_agent_civilization.reflow.invariant_registry import (
    EXCLUDED_POST_REFLOW_IDS,
    KERNEL_INVARIANTS_BLOB_SHA,
    KERNEL_INVARIANTS_PATH,
    MANDATORY_GATE_HEADING,
    MANDATORY_GATE_SOURCE_SECTION_SHA256,
    NEXT_HEADING,
    REGISTRY_PROFILE,
    REGISTRY_REPOSITORY,
    REGISTRY_SCHEMA_VERSION,
    V0_1_INVARIANT_DEFINITION_DIGESTS,
    V0_1_MANDATORY_GATE_IDS,
    expected_g19_invariant_entries,
    expected_g19_invariant_ids,
    parse_invariant_definition_digests,
    parse_mandatory_gate_ids,
    registry_digest,
    registry_entries,
    registry_id,
    registry_semantic_fingerprint,
    section_sha256,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
KERNEL_INVARIANTS = REPOSITORY_ROOT / KERNEL_INVARIANTS_PATH


def _live_section() -> str:
    text = KERNEL_INVARIANTS.read_text(encoding="utf-8")
    start = text.index(MANDATORY_GATE_HEADING)
    end = text.index(NEXT_HEADING)
    return text[start:end]


def _live_document() -> str:
    return KERNEL_INVARIANTS.read_text(encoding="utf-8")


def test_the_pinned_ids_are_the_ids_the_live_document_declares() -> None:
    assert parse_mandatory_gate_ids(_live_section()) == V0_1_MANDATORY_GATE_IDS


def test_the_pinned_section_digest_matches_the_live_document() -> None:
    assert section_sha256(_live_section()) == MANDATORY_GATE_SOURCE_SECTION_SHA256


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}".encode() + b"\0"
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324 - git's object name


def test_the_pinned_blob_is_the_live_kernel_invariants_document() -> None:
    assert _git_blob_sha(KERNEL_INVARIANTS) == KERNEL_INVARIANTS_BLOB_SHA


def test_ids_are_unique_source_ordered_and_nonempty() -> None:
    assert len(V0_1_MANDATORY_GATE_IDS) == len(set(V0_1_MANDATORY_GATE_IDS))
    assert V0_1_MANDATORY_GATE_IDS  # the positive control: an empty tuple would pass above


def test_p_003_is_excluded_from_the_g19_expected_set_but_stays_in_the_source_set() -> None:
    assert "P-003" in V0_1_MANDATORY_GATE_IDS
    assert frozenset({"P-003"}) == EXCLUDED_POST_REFLOW_IDS
    assert "P-003" not in expected_g19_invariant_ids()
    assert expected_g19_invariant_ids() == frozenset(V0_1_MANDATORY_GATE_IDS) - {"P-003"}


def test_parser_rejects_an_unrecognized_line() -> None:
    corrupted = _live_section().replace("K-001 PASS", "K-001 MAYBE")
    with pytest.raises(ValueError, match="unrecognized line"):
        parse_mandatory_gate_ids(corrupted)


def test_parser_rejects_a_duplicate_id() -> None:
    corrupted = _live_section().replace("K-002 PASS", "K-001 PASS")
    with pytest.raises(ValueError, match="duplicate invariant id"):
        parse_mandatory_gate_ids(corrupted)


def test_parser_rejects_a_second_fenced_candidate_block() -> None:
    corrupted = _live_section() + "\n```text\nK-001 PASS\n```\n"
    with pytest.raises(ValueError, match="more than one fenced"):
        parse_mandatory_gate_ids(corrupted)


def test_parser_rejects_a_missing_fenced_block() -> None:
    with pytest.raises(ValueError, match="no id-shaped fenced"):
        parse_mandatory_gate_ids("# 16. v0.1 Mandatory Gate\n\nno block here.\n")


# --- R2-G19: per-invariant definition digests + registry identity fields ---


def test_the_pinned_definition_digests_are_a_fresh_parse_of_the_live_document() -> None:
    assert parse_invariant_definition_digests(_live_document()) == V0_1_INVARIANT_DEFINITION_DIGESTS


def test_every_mandatory_id_has_exactly_one_pinned_definition_digest() -> None:
    assert set(V0_1_INVARIANT_DEFINITION_DIGESTS) == set(V0_1_MANDATORY_GATE_IDS)
    assert all(
        isinstance(digest, str) and len(digest) == 64
        for digest in V0_1_INVARIANT_DEFINITION_DIGESTS.values()
    )


def test_definition_digests_are_pairwise_distinct() -> None:
    digests = list(V0_1_INVARIANT_DEFINITION_DIGESTS.values())
    assert len(digests) == len(set(digests))


def test_parser_rejects_a_duplicate_definition_heading() -> None:
    corrupted = _live_document().replace(
        "## A-001 —", "## K-001 —", 1
    )
    with pytest.raises(ValueError, match="duplicate '## K-001"):
        parse_invariant_definition_digests(corrupted)


def test_registry_entries_cover_the_full_source_set_including_p_003() -> None:
    entries = registry_entries()
    assert tuple(entry["invariant_id"] for entry in entries) == V0_1_MANDATORY_GATE_IDS
    for entry in entries:
        expected = "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS[entry["invariant_id"]]
        assert entry["invariant_definition_sha256"] == expected


def test_expected_g19_invariant_entries_exclude_p_003_only() -> None:
    entries = expected_g19_invariant_entries()
    ids = {entry[1] for entry in entries}
    assert ids == expected_g19_invariant_ids()
    assert "P-003" not in ids
    for kind, invariant_id, digest in entries:
        assert kind == "kernel_invariant"
        assert digest == "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS[invariant_id]


def test_registry_digest_is_deterministic_and_domain_dependent_on_its_payload() -> None:
    first = registry_digest()
    second = registry_digest()
    assert first == second
    assert len(first) == 64
    assert registry_semantic_fingerprint() == "sha256:" + first
    assert registry_id() == "V01-MANDATORY-INV-REG-" + first.upper()


def test_registry_digest_changes_if_any_pinned_definition_digest_changes() -> None:
    import manosube_agent_civilization.reflow.invariant_registry as invariant_registry_module

    original = dict(V0_1_INVARIANT_DEFINITION_DIGESTS)
    baseline = registry_digest()
    tampered = dict(original)
    tampered["K-001"] = "0" * 64
    invariant_registry_module.V0_1_INVARIANT_DEFINITION_DIGESTS = tampered
    try:
        assert registry_digest() != baseline
    finally:
        invariant_registry_module.V0_1_INVARIANT_DEFINITION_DIGESTS = original


def test_registry_identity_fields_match_the_closure_policy_profile() -> None:
    assert REGISTRY_PROFILE == "MANOSUBE-V0_1-MANDATORY-INVARIANT-REGISTRY-0.1"
    assert REGISTRY_SCHEMA_VERSION == "0.1"
    assert REGISTRY_REPOSITORY == "manosube/manosube-agent-civilization-os"
