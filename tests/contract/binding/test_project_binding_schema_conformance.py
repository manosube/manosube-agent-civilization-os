"""Phase 9 (Issue #43) Product Binding schema/contract conformance.

Proves the four ``01_SCHEMA/binding/`` schemas exist, register, and fail closed on every
required field and on any unknown field -- the same pattern
``tests/contract/binding/test_development_binding_conformance.py`` already uses for its own,
categorically different Binding, kept in a clearly separate file so neither suite is ever
mistaken for exercising the other's Binding.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.fixtures.product_binding import (
    authority_policy_ref,
    boundary,
    command_policy,
    human_authority_ref,
    objective_revision,
    secret_exclusion_policy,
    source_registrations,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding.engine import assemble_project_binding
from manosube_agent_civilization.binding.errors import BindingValidationError
from manosube_agent_civilization.binding.validation import (
    BINDING_SCHEMA_BASE,
    _validators,
    validate_record,
)

BOUND_AT = "2026-09-06T09:00:00Z"


def _assembled() -> dict[str, Any]:
    return assemble_project_binding(
        project_id="PRJ-CONFORM-0001",
        objective_revision_ref={
            "kind": "objective_revision",
            "id": objective_revision()["objective_revision_id"],
        },
        boundary=boundary(),
        authority_policy_ref=authority_policy_ref(),
        source_registrations=source_registrations(),
        command_policy=command_policy(),
        secret_exclusion_policy=secret_exclusion_policy(),
        human_authority_ref=human_authority_ref(),
        bound_at=BOUND_AT,
        schema_root=SCHEMA_ROOT,
    )


# --- schema registration ---------------------------------------------------------------- #


def test_all_four_binding_schemas_register_with_a_stable_id() -> None:
    validators = _validators(SCHEMA_ROOT)
    for name in (
        "project_binding.schema.json",
        "boundary.schema.json",
        "source_registration.schema.json",
        "command_policy.schema.json",
    ):
        assert BINDING_SCHEMA_BASE + name in validators


# --- positive controls ------------------------------------------------------------------- #


def test_a_real_boundary_source_registration_and_command_policy_validate_cleanly() -> None:
    validate_record(boundary(), "boundary.schema.json", schema_root=SCHEMA_ROOT)
    for registration in source_registrations():
        validate_record(registration, "source_registration.schema.json", schema_root=SCHEMA_ROOT)
    validate_record(command_policy(), "command_policy.schema.json", schema_root=SCHEMA_ROOT)


def test_a_real_assembled_project_binding_validates_against_its_own_schema() -> None:
    record = _assembled()
    validate_record(record, "project_binding.schema.json", schema_root=SCHEMA_ROOT)
    assert record["project_binding_id"].startswith("PROJBIND-")
    assert record["schema_version"] == "0.1"


# --- required-field negative controls ------------------------------------------------------ #


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "project_id",
        "objective_revision_ref",
        "boundary",
        "authority_policy_ref",
        "source_registrations",
        "command_policy",
        "secret_exclusion_policy",
        "human_authority_ref",
        "bound_at",
        "project_binding_id",
    ],
)
def test_project_binding_schema_rejects_a_missing_required_field(field: str) -> None:
    record = _assembled()
    del record[field]
    with pytest.raises(BindingValidationError):
        validate_record(record, "project_binding.schema.json", schema_root=SCHEMA_ROOT)


def test_project_binding_schema_rejects_an_unknown_field() -> None:
    record = _assembled()
    record["unexpected_extra_field"] = "not permitted"
    with pytest.raises(BindingValidationError):
        validate_record(record, "project_binding.schema.json", schema_root=SCHEMA_ROOT)


def test_project_binding_schema_rejects_a_malformed_project_binding_id() -> None:
    record = _assembled()
    record["project_binding_id"] = "NOT-CONTENT-ADDRESSED"
    with pytest.raises(BindingValidationError):
        validate_record(record, "project_binding.schema.json", schema_root=SCHEMA_ROOT)


@pytest.mark.parametrize(
    "field",
    ["schema_version", "root_paths", "include_patterns", "exclude_patterns"],
)
def test_boundary_schema_rejects_a_missing_required_field(field: str) -> None:
    record = boundary()
    del record[field]
    with pytest.raises(BindingValidationError):
        validate_record(record, "boundary.schema.json", schema_root=SCHEMA_ROOT)


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "source_id",
        "source_type",
        "locator",
        "include_patterns",
        "exclude_patterns",
    ],
)
def test_source_registration_schema_rejects_a_missing_required_field(field: str) -> None:
    record = source_registrations()[0]
    del record[field]
    with pytest.raises(BindingValidationError):
        validate_record(record, "source_registration.schema.json", schema_root=SCHEMA_ROOT)


def test_source_registration_schema_rejects_an_unknown_source_type() -> None:
    record = source_registrations()[0]
    record["source_type"] = "SHELL_COMMAND"
    with pytest.raises(BindingValidationError):
        validate_record(record, "source_registration.schema.json", schema_root=SCHEMA_ROOT)


@pytest.mark.parametrize(
    "field", ["schema_version", "allowed_command_classes", "max_commands_per_change"]
)
def test_command_policy_schema_rejects_a_missing_required_field(field: str) -> None:
    record = command_policy()
    del record[field]
    with pytest.raises(BindingValidationError):
        validate_record(record, "command_policy.schema.json", schema_root=SCHEMA_ROOT)


def test_command_policy_schema_rejects_an_unconstrained_wildcard() -> None:
    record = command_policy()
    record["allowed_command_classes"] = ["*"]
    with pytest.raises(BindingValidationError):
        validate_record(record, "command_policy.schema.json", schema_root=SCHEMA_ROOT)


def test_command_policy_schema_rejects_shell_text_as_a_command_class() -> None:
    record = command_policy()
    record["allowed_command_classes"] = ["rm -rf /"]
    with pytest.raises(BindingValidationError):
        validate_record(record, "command_policy.schema.json", schema_root=SCHEMA_ROOT)


def test_command_policy_schema_rejects_an_authority_grant_field() -> None:
    record = command_policy()
    record["authority_grant"] = True
    with pytest.raises(BindingValidationError):
        validate_record(record, "command_policy.schema.json", schema_root=SCHEMA_ROOT)


def test_command_policy_schema_rejects_an_execution_request_field() -> None:
    record = command_policy()
    record["execute_now"] = "BUILD"
    with pytest.raises(BindingValidationError):
        validate_record(record, "command_policy.schema.json", schema_root=SCHEMA_ROOT)


def test_secret_exclusion_policy_shape_never_accepts_a_free_text_secret_value() -> None:
    """The schema itself forecloses an actual secret value here: only field-name strings
    and a closed reference-kind enum are accepted, ``additionalProperties: false``."""

    record = deepcopy(_assembled())
    record["secret_exclusion_policy"]["a_forbidden_extra_field"] = "not-a-secret-just-a-string"
    with pytest.raises(BindingValidationError):
        validate_record(record, "project_binding.schema.json", schema_root=SCHEMA_ROOT)


# --- Development Binding / Phase 8 fixture non-substitution ------------------------------- #


def test_product_binding_never_imports_development_binding() -> None:
    """Product Binding (a canonical, Store-persisted, schema-validated record about a real
    bound project) and Development Binding (a pinned-in-code policy about this repository's
    own contributors) are categorically different -- neither substitutes for the other. A
    real AST walk over every ``import``/``from ... import`` statement in each of this
    domain's own modules, never a bare substring search."""

    import ast
    import inspect

    import manosube_agent_civilization.binding.engine as engine_module
    import manosube_agent_civilization.binding.route as route_module

    for module in (engine_module, route_module):
        tree = ast.parse(inspect.getsource(module))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        assert not any("development_binding" in name for name in imported_modules)


def test_product_binding_engine_has_no_development_binding_shaped_surface() -> None:
    import manosube_agent_civilization.binding as binding_module

    assert not hasattr(binding_module, "load_policy")
    assert not hasattr(binding_module, "evaluate")


def test_every_public_route_reaching_store_initialize_runs_the_full_admission_chain() -> None:
    """Issue #43 Phase 9 Round 1 §9.2, extended by Phase 9 Round 2 P9-R2-F5: a real
    call-graph scan of ``route.py``/``engine.py``/``admission.py``'s own module source --
    not a grep, not a hardcoded name list -- proving ``PUBLIC_COMMITTING_ROUTE_COUNT=1``
    (``bind_project``), ``CANONICAL_BINDING_PRECOMMIT_ADMISSION_OWNER_COUNT=1``
    (``admit_genesis_transaction``), and that this one route reaches, directly or through an
    intermediate helper, every required admission stage: schema validation
    (``validate_record``/``validate_against_schema_id``), cross-binding validation
    (``assemble_project_binding``), identity reverification (``rule_id``,
    ``verify_project_binding_identity``), the one shared pre-commit admission
    (``admit_genesis_transaction``, which itself performs whole-graph secret exclusion and
    reference-edge closure -- P9-R2-F1/F2/F3), and typed reference admission
    (``reject_wrong_kind_reference``). A future new route calling ``store.initialize``
    without reaching one of these would fail this test, structurally -- no update to a name
    list is what makes it pass or fail."""

    import ast
    import inspect

    import manosube_agent_civilization.binding.admission as admission_module
    import manosube_agent_civilization.binding.engine as engine_module
    import manosube_agent_civilization.binding.route as route_module

    calls: dict[str, set[str]] = {}
    for module in (route_module, engine_module, admission_module):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                called: set[str] = set()
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        if isinstance(sub.func, ast.Name):
                            called.add(sub.func.id)
                        elif isinstance(sub.func, ast.Attribute):
                            called.add(sub.func.attr)
                calls[node.name] = called

    def reaches(fn_name: str, target: str, seen: set[str]) -> bool:
        if fn_name in seen:
            return False
        seen.add(fn_name)
        direct = calls.get(fn_name, set())
        if target in direct:
            return True
        return any(callee in calls and reaches(callee, target, seen) for callee in direct)

    committing_routes = {name for name, called in calls.items() if "initialize" in called}
    assert committing_routes == {"bind_project"}
    required_stages = (
        "validate_against_schema_id",
        "assemble_project_binding",
        "rule_id",
        "verify_project_binding_identity",
        "reject_secret_material",
        "reject_wrong_kind_reference",
        "admit_genesis_transaction",
        "reference_edges",
    )
    for name in sorted(committing_routes):
        for stage in required_stages:
            assert reaches(name, stage, set()), (
                f"{name} calls store.initialize without reaching required admission stage "
                f"{stage!r} -- PUBLIC_COMMITTING_ROUTE_BYPASS_COUNT must be 0"
            )


def test_product_binding_fixture_never_imports_the_phase_8_fixture_module() -> None:
    """``tests/fixtures/product_binding.py`` is deliberately self-contained -- it must never
    *import* ``tests/fixtures/vertical_proof.py``, the Phase 8 fixture, which this Finding
    requires never substitute for a real Product Binding declaration. A real AST walk over
    every ``import``/``from ... import`` statement, never a bare substring search (this
    module's own docstring legitimately *names* ``vertical_proof.py`` in prose)."""

    import ast
    import inspect

    import tests.fixtures.product_binding as product_binding_module

    tree = ast.parse(inspect.getsource(product_binding_module))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    assert not any("vertical_proof" in name for name in imported_modules)
