"""Validate the canonical schema registry and contract fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from difference_contract_validator import validate_fixture_suite as validate_difference_fixtures
from jsonschema import Draft202012Validator, FormatChecker
from observation_contract_validator import validate_fixture_suite
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "01_SCHEMA"
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "schema"
OBSERVATION_FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "observation"
DIFFERENCE_FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "difference"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture_cases(directory: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        document = load_json(path)
        if not isinstance(document, list):
            raise SystemExit(f"fixture case file must contain an array: {path}")
        cases.extend(document)
    names = [case.get("name") for case in cases]
    if None in names or len(names) != len(set(names)):
        raise SystemExit(f"fixture names must be present and unique: {directory}")
    return cases


def iter_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("$ref"), str):
            refs.append(value["$ref"])
        for child in value.values():
            refs.extend(iter_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(iter_refs(child))
    return refs


def main() -> int:
    paths = sorted(SCHEMA_ROOT.rglob("*.schema.json"))
    schemas = [load_json(path) for path in paths]
    ids = [schema.get("$id") for schema in schemas]
    # 33 before the Authority family; the four Authority schemas make 37, the one Change
    # schema makes 38, the one Evidence schema makes 39, the one Reflow schema
    # (material_contradiction) makes 40, R6-F4's kernel_source_witness makes 41, and
    # R6-F1a's source_snapshot makes 42. Phase 9's own four Product Binding schemas
    # (project_binding, boundary, source_registration, command_policy -- Issue #43,
    # KERNEL_ELEMENT=NONE_PRODUCT_BINDING_LAYER, not a ninth Kernel element) make 46. The
    # count is asserted rather than derived so a schema added without being reconciled
    # here fails the gate instead of silently widening the inventory. Phase 9 Completion
    # Repair 5's own genesis institution receipt (P9-C5-F1) adds one more, making 47.
    # Phase 13 Structural Review Round 3's own Authority extension (P13-R3-F1,
    # verifier_selection_grant and verifier_selection_decision) adds two more, making 49.
    # Phase 13 Structural Review Round 5's own Binding extension (P13-R5,
    # human_grant_declaration) adds one more, making 50. Phase 14's own Projection Envelope
    # (Issue #62, projection_envelope) adds one more, making 51. Phase 14 Structural Review
    # Round 1's own Authority extension (P14-R1-F1, github_projection_grant and
    # github_projection_decision) adds two more, making 53. Phase 14 Structural Review
    # Round 2's own signed-declaration and atomic-claim extensions (P14-R2-F1's
    # github_projection_grant_declaration, and P14-R2-F2's projection_intent and
    # projection_materialize_attempt) add three more, making 56. Phase 15's own Runtime
    # Observation Envelope (Issue #64, runtime_observation_envelope) adds one more, making 57.
    # Phase 15 Structural Review Round 1's own Store-anchored deployment identity
    # (P15-R1-F6, runtime_deployment_declaration -- the canonical, content-addressed,
    # Human-Authority-declared record a target's own claimed deployment_fingerprint must now
    # match, closing the circular "the endpoint echoed the expected string" verification)
    # adds one more, making 58. Phase 15 Structural Review Round 2 adds no schema file at all
    # (it added required `status`/`signature` fields to that existing one), so the count stayed
    # at 58 through that round. Phase 15 Structural Review Round 3's own externally anchored
    # root admission (P15-R3-F1, runtime_root_admission -- the canonical, content-addressed,
    # trust-anchor-signed record that admits one specific project/Project Binding, and without
    # which possessing a TrustedRuntimeRoot grants nothing at all) adds one more, making 59.
    # Round 3's own second finding (P15-R3-F2) adds required valid_from/valid_until fields to
    # the existing runtime_deployment_declaration schema, again with no new file. Phase 15
    # Structural Review Round 4 (P15-R4-F1/F2) likewise adds no schema file: it adds required
    # generation/predecessor_ref fields to *both* existing Runtime schemas
    # (runtime_deployment_declaration and runtime_root_admission), so each record kind's own
    # place in its monotonic transition chain is covered by its content address and its
    # signature. The count therefore stays at 59, verified against what is on disk rather than
    # assumed. Phase 16's own Multi-Model Replaceability delivery (Issue #66) adds seven more,
    # making 66: five owned by the new `model_runtime` package (`model_execution_boundary` --
    # the Human-declared Boundary bounding what a model's output may be used for;
    # `model_work_unit` -- the immutable, State-bound Work Unit the whole proof hangs from;
    # `model_execution_envelope` -- the committed model result; `model_swap_receipt` and
    # `session_recovery_receipt` -- the two committed continuity facts P16-C4/P16-C5 require),
    # and two owned by the existing Authority element (`model_execution_grant`, the
    # Human-Authority-signed capability grant, and `model_execution_decision`, the
    # content-addressed decision `evaluate_model_execution_authorization` mints). No existing
    # schema file is replaced or removed. Phase 17's own Read-only URL Boot delivery (Issue #69)
    # adds one more, `url_boot/url_source_observation_envelope` -- the committed URL Source
    # Observation Envelope -- making 67. Phase 18's own Controlled Autonomous Change delivery
    # (Issue #73) adds five more, all owned by the new `change_executor` package:
    # `execution_boundary` (the closed, low-risk Execution Boundary schema), `execution_intent`
    # and `execution_attempt` (the two durable idempotency-slot claim records P18-C5's own
    # replay/conflict/reconciliation state machine is built on), `execution_receipt` (the
    # immutable `change_execution_receipt` P18-C6 requires), and `change_executor_kill_switch`
    # (the signed, monotonic ACTIVE/REVOKED Human kill-switch chain P18-C8 requires) -- making
    # 72. Phase 19's own Multi-Agent Dynamic Execution delivery (Issue #77) adds six more, all
    # owned by the new `multi_agent` package: `multi_agent_dynamic_execution_plan` (the
    # immutable, content-addressed plan P19-C2 requires), `multi_agent_slot_output` (one per
    # slot's own attempt, P19-C5), `multi_agent_agent_release_receipt` (P19-C8),
    # `multi_agent_conflict_set` (P19-C6), `multi_agent_evidence_aggregation_input` (P19-C7),
    # and `multi_agent_orchestration_receipt` (the terminal fact P19-C8/P19-C9 describe) --
    # making 78. Phase 19 Structural Review Round 3's own crash-recovery extension (P19-R3-F3,
    # `multi_agent_slot_attempt_envelope_claim` -- the durable claim naming a slot's own already-
    # committed Model Execution Envelope, committed before that slot's own terminal
    # slot_output/release_receipt pair, so a coordinator crash between the two never causes a
    # duplicate adapter call on recovery) adds one more, making 79.
    if len(paths) != 79 or len(set(ids)) != len(paths) or None in ids:
        raise SystemExit("schema inventory or unique $id gate failed")

    for schema in schemas:
        Draft202012Validator.check_schema(schema)

    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    schema_by_id = {schema["$id"]: schema for schema in schemas}
    unresolved_refs: list[str] = []
    for schema in schemas:
        resolver = registry.resolver(schema["$id"])
        for reference in iter_refs(schema):
            try:
                resolver.lookup(reference)
            except Exception:
                unresolved_refs.append(f"{schema['$id']} -> {reference}")

    valid_cases = load_fixture_cases(FIXTURE_ROOT / "valid")
    invalid_cases = load_fixture_cases(FIXTURE_ROOT / "invalid")
    valid_failures: list[str] = []
    invalid_escapes: list[str] = []

    for case in valid_cases:
        validator = Draft202012Validator(
            schema_by_id[case["schema_id"]], registry=registry, format_checker=FormatChecker()
        )
        errors = list(validator.iter_errors(case["instance"]))
        if errors:
            valid_failures.append(case["name"])

    for case in invalid_cases:
        validator = Draft202012Validator(
            schema_by_id[case["schema_id"]], registry=registry, format_checker=FormatChecker()
        )
        if not list(validator.iter_errors(case["instance"])):
            invalid_escapes.append(case["name"])

    print(f"SCHEMA_COUNT={len(paths)}")
    print(f"UNIQUE_SCHEMA_ID_COUNT={len(set(ids))}")
    print(f"UNRESOLVED_REF_COUNT={len(unresolved_refs)}")
    print(f"VALID_FIXTURE_COUNT={len(valid_cases)}")
    print(f"INVALID_FIXTURE_COUNT={len(invalid_cases)}")
    print(f"VALID_FIXTURE_FAILURE_COUNT={len(valid_failures)}")
    print(f"INVALID_FIXTURE_ESCAPE_COUNT={len(invalid_escapes)}")
    # R6-F1a: source_snapshot.schema.json makes 8.
    print("OBSERVATION_SCHEMA_COUNT=8")
    (
        observation_valid_count,
        observation_invalid_count,
        observation_valid_errors,
        observation_invalid_escapes,
    ) = validate_fixture_suite(OBSERVATION_FIXTURE_ROOT)
    print(f"OBSERVATION_CONFORMANCE_VALID_FIXTURE_COUNT={observation_valid_count}")
    print(f"OBSERVATION_CONFORMANCE_INVALID_FIXTURE_COUNT={observation_invalid_count}")
    print(f"OBSERVATION_CONFORMANCE_VALID_FAILURE_COUNT={len(observation_valid_errors)}")
    print(f"OBSERVATION_CONFORMANCE_INVALID_ESCAPE_COUNT={len(observation_invalid_escapes)}")
    (
        difference_valid_count,
        difference_invalid_count,
        difference_valid_errors,
        difference_invalid_escapes,
    ) = validate_difference_fixtures(DIFFERENCE_FIXTURE_ROOT)
    difference_schema_count = len(list((SCHEMA_ROOT / "difference").glob("*.schema.json")))
    print(f"DIFFERENCE_SCHEMA_COUNT={difference_schema_count}")
    authority_schema_count = len(list((SCHEMA_ROOT / "authority").glob("*.schema.json")))
    print(f"AUTHORITY_SCHEMA_COUNT={authority_schema_count}")
    change_schema_count = len(list((SCHEMA_ROOT / "change").glob("*.schema.json")))
    print(f"CHANGE_SCHEMA_COUNT={change_schema_count}")
    evidence_schema_count = len(list((SCHEMA_ROOT / "evidence").glob("*.schema.json")))
    print(f"EVIDENCE_SCHEMA_COUNT={evidence_schema_count}")
    reflow_schema_count = len(list((SCHEMA_ROOT / "reflow").glob("*.schema.json")))
    print(f"REFLOW_SCHEMA_COUNT={reflow_schema_count}")
    print(f"DIFFERENCE_CONFORMANCE_VALID_FIXTURE_COUNT={difference_valid_count}")
    print(f"DIFFERENCE_CONFORMANCE_INVALID_FIXTURE_COUNT={difference_invalid_count}")
    print(f"DIFFERENCE_CONFORMANCE_VALID_FAILURE_COUNT={len(difference_valid_errors)}")
    print(f"DIFFERENCE_CONFORMANCE_INVALID_ESCAPE_COUNT={len(difference_invalid_escapes)}")
    if (
        unresolved_refs
        or valid_failures
        or invalid_escapes
        or observation_valid_errors
        or observation_invalid_escapes
        or difference_valid_errors
        or difference_invalid_escapes
    ):
        print(f"UNRESOLVED_REFS={unresolved_refs}")
        print(f"VALID_FAILURES={valid_failures}")
        print(f"INVALID_ESCAPES={invalid_escapes}")
        print(f"OBSERVATION_VALID_ERRORS={observation_valid_errors}")
        print(f"OBSERVATION_INVALID_ESCAPES={observation_invalid_escapes}")
        print(f"DIFFERENCE_VALID_ERRORS={difference_valid_errors}")
        print(f"DIFFERENCE_INVALID_ESCAPES={difference_invalid_escapes}")
        return 1
    print("SCHEMA_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
