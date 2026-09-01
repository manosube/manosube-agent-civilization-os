"""Change and Reflow are opaque structural provenance in Phase 3, and nothing more.

v0.1 defines no canonical schema for a Change or a Reflow transaction. The Difference
auditor nevertheless read `committed_at`, `event_type`, `project_id`, `after_state`,
`from_revision`, `to_revision`, two fingerprints and `evidence_refs` off a Reflow record,
and parsed two timestamps out of it. That was a Reflow field contract authored here by
assumption -- an undeclared rule that could not be satisfied, argued with, or versioned,
because no schema stated it. It was also unsound in the ordinary way: the first fixture to
actually populate the section reached `fromisoformat` on a field nothing had validated.

The boundary this file pins:

```text
REFLOW_FIELD_SEMANTICS_CLAIMED=false
UNSCHEMATIZED_REFLOW_PARSED_BY_DIFFERENCE_AUDITOR=false
OPAQUE_REFLOW_STRUCTURAL_VALIDATION=true
POPULATED_CHANGE_REFLOW_COVERAGE=true
```

This is a **phase-bounded non-claim, not a permanent rejection of a Reflow contract**. The
Reflow phase owns those fields and must state them as a canonical schema with its own
validation. Until it does, Phase 3 must not become their owner by default -- which is what
happens when a reader is added and no one notices it implied a contract.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.unit.difference.test_auditor_totality_sweep import BUILT

from manosube_agent_civilization.difference.conformance import (
    EMITTED_SECTIONS,
    RECORD_TYPES,
    UNSCHEMATIZED_SECTIONS,
)

pytestmark = pytest.mark.contract

VALIDATOR_SOURCE = (
    Path(__file__).resolve().parents[3] / "scripts" / "difference_contract_validator.py"
)

#: Fields the auditor used to read off a Reflow transaction. No canonical schema declares
#: any of them, so reading one is this phase claiming a contract it does not own.
UNOWNED_REFLOW_FIELDS = (
    "committed_at",
    "event_type",
    "from_revision",
    "to_revision",
    "before_fingerprint",
    "after_fingerprint",
    "after_state",
)


def test_reflow_field_semantics_are_not_claimed() -> None:
    """`REFLOW_FIELD_SEMANTICS_CLAIMED=false`, asserted against the source.

    Source-level and deliberately coarse: a reader re-added anywhere in the validator fails
    this, whether or not anyone remembered it implied a contract.
    """

    tree = ast.parse(VALIDATOR_SOURCE.read_text(encoding="utf-8"))
    offenders = [
        f"{node.lineno}: {ast.unparse(node)[:90]}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id in {"transition", "reflow_transition", "change"}
        and isinstance(node.slice, ast.Constant)
        and node.slice.value in UNOWNED_REFLOW_FIELDS
    ]
    assert offenders == [], (
        "the Difference auditor reads Reflow fields no canonical schema declares, which "
        f"makes this phase their owner by assumption: {offenders}"
    )


def test_the_auditor_does_not_parse_an_unschematized_record() -> None:
    """`UNSCHEMATIZED_REFLOW_PARSED_BY_DIFFERENCE_AUDITOR=false`.

    An opaque payload may carry anything at all -- including values that are not timestamps
    where a later phase might one day put one. Nothing here may interpret them.
    """

    bundle = deepcopy(BUILT["unschematized"])
    for section in UNSCHEMATIZED_SECTIONS:
        assert bundle[section], section
        key = RECORD_TYPES[EMITTED_SECTIONS[section]].key
        identity = bundle[section][0][key]
        bundle[section] = [
            {
                key: identity,
                "kind": bundle[section][0].get("kind", "opaque"),
                "committed_at": {"not": "a timestamp"},
                "event_type": ["not", "a", "string"],
                "after_state": 7,
                "an_unknown_later_phase_field": None,
            }
        ]
    assert validate_bundle(bundle) == [], (
        "an opaque Change/Reflow payload was interpreted rather than carried"
    )


def test_opaque_provenance_is_still_structurally_validated() -> None:
    """`OPAQUE_REFLOW_STRUCTURAL_VALIDATION=true`. Opaque is not unchecked.

    Identity, object shape and same-identity/different-payload remain enforced -- they are
    owned structurally by this phase and need no Reflow contract to state them.
    """

    for section in UNSCHEMATIZED_SECTIONS:
        key = RECORD_TYPES[EMITTED_SECTIONS[section]].key
        base = deepcopy(BUILT["unschematized"])
        record = deepcopy(base[section][0])

        missing = deepcopy(base)
        missing[section] = [{k: v for k, v in record.items() if k != key}]
        assert validate_bundle(missing), f"{section}: absent identity was accepted"

        unhashable = deepcopy(base)
        unhashable[section] = [{**record, key: {"a": 1}}]
        assert validate_bundle(unhashable), f"{section}: unhashable identity was accepted"

        not_an_object = deepcopy(base)
        not_an_object[section] = ["not a record"]
        assert validate_bundle(not_an_object), f"{section}: non-object record was accepted"

        conflicting = deepcopy(base)
        conflicting[section] = [record, {**record, "an_extra_field": "conflict"}]
        assert validate_bundle(conflicting), (
            f"{section}: one identity named two payloads and was accepted"
        )


def test_populated_change_reflow_coverage_exists() -> None:
    """`POPULATED_CHANGE_REFLOW_COVERAGE=true`. An empty section exercises nothing."""

    bundle: dict[str, Any] = BUILT["unschematized"]
    for section in UNSCHEMATIZED_SECTIONS:
        assert bundle.get(section), (
            f"{section} is empty in the fixture that exists to populate it; an absent "
            f"section generates no case and cannot cover its record type"
        )
    assert validate_bundle(deepcopy(bundle)) == []
