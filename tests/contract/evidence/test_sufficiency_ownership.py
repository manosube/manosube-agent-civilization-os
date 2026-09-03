"""Evidence produces the sufficiency result. It does not become a second Difference.

```text
DIFFERENCE_OWNS_CLOSURE_POLICY_SCHEMA=true
DIFFERENCE_OWNS_SUFFICIENCY_RESULT_SCHEMA=true
EVIDENCE_OWNS_SUFFICIENCY_PRODUCTION=true
EVIDENCE_OWNS_DIFFERENCE_CLOSURE=false
```

The frozen tree already said this and nobody had written the producer: the two schemas are
Difference's, ``difference/engine.py`` carries sufficiency results without minting one, and
``ADR-0009`` records the section as ``NOT CLAIMED — LATER PHASE``. What this module holds is
that filling the gap did not widen it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.evidence_guards import clock_read_sites, emitted_strings, module_paths
from tests.evidence_helpers import EVALUATED_AT, closure_policy, sufficiency_request

from manosube_agent_civilization.evidence import (
    NOT_EVALUATED_HERE,
    EvidenceError,
    evaluate_sufficiency,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPOSITORY_ROOT / "01_SCHEMA"
EVIDENCE_PACKAGE = REPOSITORY_ROOT / "src" / "manosube_agent_civilization" / "evidence"

#: Difference's closure vocabulary. Quoting one to explain the boundary is documentation;
#: emitting one would be Evidence answering Difference's question.
FORBIDDEN_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"CLOSED", "REOPENED", "RETAINED", "SATISFIED", "NOT_SATISFIED"}
)

#: The two schemas Phase 6 consumes and must not re-declare.
DIFFERENCE_OWNED = ("closure_policy.schema.json", "evidence_sufficiency_result.schema.json")


def test_neither_difference_owned_schema_is_copied_into_the_evidence_family() -> None:
    """A second copy of either schema would be a second owner that can drift from the first."""

    evidence_schemas = {path.name for path in (SCHEMA_ROOT / "evidence").glob("*.schema.json")}
    assert evidence_schemas == {"evidence.schema.json"}
    for name in DIFFERENCE_OWNED:
        assert (SCHEMA_ROOT / "difference" / name).is_file()
        assert not (SCHEMA_ROOT / "evidence" / name).exists()


def test_the_produced_result_validates_against_differences_own_schema() -> None:
    result = evaluate_sufficiency(sufficiency_request())["evidence_sufficiency_result"]
    schema = json.loads(
        (SCHEMA_ROOT / "difference" / "evidence_sufficiency_result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(result) == set(schema["required"])
    assert schema["additionalProperties"] is False


def test_the_evidence_package_declares_no_closure_and_no_terminal_status() -> None:
    """Closure is Difference's word. The check is over the package's own source, so a future
    module that starts emitting one is caught rather than assumed not to exist."""

    found: dict[str, set[str]] = {}
    for path in module_paths(EVIDENCE_PACKAGE):
        hits = emitted_strings(path) & FORBIDDEN_TERMINAL_STATUSES
        if hits:
            found[path.name] = hits
    assert found == {}


def test_the_terminal_status_guard_is_not_vacuous(tmp_path: Path) -> None:
    """The control. A guard that reports nothing must be shown capable of reporting."""

    injected = tmp_path / "injected.py"
    injected.write_text(
        '"""A docstring naming CLOSED, which must not be reported."""\nTERMINAL = "CLOSED"\n',
        encoding="utf-8",
    )
    assert "CLOSED" in emitted_strings(injected)

    quoted = tmp_path / "quoted.py"
    quoted.write_text('"""Evidence never emits CLOSED."""\n', encoding="utf-8")
    assert "CLOSED" not in emitted_strings(quoted)


def test_the_package_declares_what_it_does_not_evaluate() -> None:
    """ "Sufficiency passed" must never be readable as "closure passed"."""

    policy_fields = set(
        json.loads(
            (SCHEMA_ROOT / "difference" / "closure_policy.schema.json").read_text(encoding="utf-8")
        )["required"]
    )
    assert set(NOT_EVALUATED_HERE) <= policy_fields
    assert evaluate_sufficiency(sufficiency_request())["not_evaluated_here"] == list(
        NOT_EVALUATED_HERE
    )


def test_independence_is_neither_produced_nor_permitted_here() -> None:
    """``CLOSURE_POLICY.md`` pins ``independent_verification_required`` to ``false`` in v0.1,
    and Phase 6 produces no independence record at all. The refusal is Difference's schema
    doing its own job -- this asserts Evidence did not route around it."""

    schema = json.loads(
        (SCHEMA_ROOT / "difference" / "closure_policy.schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["independent_verification_required"] == {"const": False}

    policy = closure_policy("D-" + "0" * 64)
    policy["independent_verification_required"] = True
    with pytest.raises(EvidenceError):
        evaluate_sufficiency(sufficiency_request(difference_id="D-" + "0" * 64, policy=policy))

    emitted: set[str] = set()
    for path in module_paths(EVIDENCE_PACKAGE):
        emitted |= emitted_strings(path)
    assert "verification_independence_ref" not in emitted


def test_a_policy_rewritten_after_it_was_addressed_is_refused() -> None:
    """The gap ``difference/conformance.py`` names, closed on this route too.

    Without recomputing the address from the Policy's content, a caller could lower
    ``minimum_evidence_level``, keep the stored digest and identity, and have sufficiency
    evaluate a floor nobody ratified.
    """

    identity = "D-" + "1" * 64
    policy: dict[str, Any] = closure_policy(identity, minimum_evidence_level="E3")
    policy["minimum_evidence_level"] = "E0"
    with pytest.raises(EvidenceError) as raised:
        evaluate_sufficiency(sufficiency_request(difference_id=identity, policy=policy))
    # The refusal is Difference's own Closure Policy owner, called rather than reimplemented.
    assert "does not recompute" in str(raised.value)


def test_a_policy_for_another_difference_is_refused() -> None:
    other = closure_policy("D-" + "2" * 64)
    with pytest.raises(EvidenceError) as raised:
        evaluate_sufficiency(sufficiency_request(difference_id="D-" + "3" * 64, policy=other))
    assert "governs a different Difference" in str(raised.value)


def test_the_evaluation_instant_is_admitted_and_never_read() -> None:
    result = evaluate_sufficiency(sufficiency_request())["evidence_sufficiency_result"]
    assert result["evaluated_at"] == EVALUATED_AT

    assert clock_read_sites(EVIDENCE_PACKAGE) == {}


def test_the_scale_source_must_address_the_scale_being_applied() -> None:
    request = sufficiency_request()
    request["completion_semantics_ref"]["evidence_level_scale_sha256"] = "f" * 64
    with pytest.raises(EvidenceError) as raised:
        evaluate_sufficiency(request)
    assert "different Evidence Level scale" in str(raised.value)


def test_the_scale_source_must_be_the_canonical_document() -> None:
    request = sufficiency_request()
    request["completion_semantics_ref"]["path"] = "docs/notes.md"
    with pytest.raises(EvidenceError) as raised:
        evaluate_sufficiency(request)
    assert "canonical Evidence Level source" in str(raised.value)


def test_a_policy_whose_identity_was_rewritten_is_refused() -> None:
    """The half Difference's Policy owner does not check, and this module therefore does.

    ``closure_policy_semantic_errors`` recomputes the *fingerprint* and refuses a rewritten
    requirement; it does not recompute the ``CP-`` address. Both halves are needed and
    neither is duplicated -- a second fingerprint comparison here could never fail.
    """

    from manosube_agent_civilization.difference.policy import closure_policy_semantic_errors

    identity = "D-" + "4" * 64
    policy = closure_policy(identity)
    policy["closure_policy_id"] = "CP-" + "A" * 64

    assert closure_policy_semantic_errors(policy, "closure_policy") == []

    with pytest.raises(EvidenceError) as raised:
        evaluate_sufficiency(sufficiency_request(difference_id=identity, policy=policy))
    assert "identity does not match" in str(raised.value)
