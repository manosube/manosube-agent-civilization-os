"""Phase 13 (Issue #51) Independent Verification: the one public route
(``run_independent_verification``), end-to-end, over a real ``FileStateStore``.

Proves the canonical successful route (``VERIFICATION_CONTRACT.md`` §5), the required
rejection proofs (§6), and that no rejection or successful call ever mutates canonical
Store visibility -- the verifier is the only call this route ever makes past its own
admission gate, and it is called exactly once on the successful route and exactly zero
times on every rejection.

Structural Review Round 1 (P13-R1-F1/F2/F3): the fixture below binds a real Project
Binding (through the existing Phase 9 Binding owner) so ``boot_project`` -- the real
Authority-owner surface this route now re-verifies ``selection_authority_ref`` through --
succeeds, and commits one real, Store-resolvable ``observation_evidence`` record directly
through the Store's own public ``commit`` (the identical low-level surface Reflow's own
route calls), rather than the pre-Binding ``tests.natural_cycle`` fixture world this file
used before Round 1 (which never binds a Project and therefore cannot boot).

Structural Review Round 3 (P13-R3-F1): every call to ``run_independent_verification`` now
also supplies an explicit collection of ``verifier_selection_grant`` references -- real,
canonical, Human-Authority-declared records the existing Authority owner's own
``evaluate_verifier_selection`` re-verifies. ``_grant`` below builds the one that binds the
default fixture selection by construction, so every retained test below still exercises its
own concern rather than incidentally failing at the new Authority-owned check.

Structural Review Round 4 (P13-R4, Authority Provenance Bypass, P13-R3-F2): grant *content*
is no longer an accepted argument at all -- ``run_independent_verification`` now takes
``verifier_selection_grant_refs`` and resolves each through the Store's own
``resolve_record``. The fixture below now commits every grant variant this module's tests
need directly into the Store (alongside the one ``observation_evidence`` record Round 1
already committed), and ``_grant_ref`` recomputes the matching ``{"kind": ..., "id": ...}``
reference for a test body to pass -- content-addressing is deterministic, so the same
override arguments always name the same committed record.

Structural Review Round 5 (P13-R5, canonical Human declaration anchor): a genuinely
Store-resolved grant is still not, by itself, proof that a Human declared it -- any
Store-write-capable caller could commit a self-hashed grant. ``run_independent_verification``
now also takes ``human_grant_declaration_refs``, resolved through the identical Store call
site. The fixture below commits a real, genuine default declaration through the existing
Binding owner's own ``declare_human_grant`` (proving that route end-to-end), plus the
fabricated/mismatched/revoked/tampered variants this module's negative tests need -- built
and committed directly, the same way the Round 4 grant variants above already are, since
``declare_human_grant`` itself always resolves the real Human Authority reference and cannot
be made to produce a fabricated one.

Structural Review Round 5-R1 (Issue #51, P13-R5-R1,
``ADOPT_P13_R5_R1_SIGNED_HUMAN_DECLARATION_AND_SINGLE_COMMITTER``): a declaration's own
durable Store commission and self-consistent shape (Round 5) still never proved a *Human*,
rather than any Store-write-capable caller, authored it. Every declaration this fixture
commits now carries a real Ed25519 signature (``tests.fixtures.product_binding.sign_human_
grant_declaration``, the fixed deterministic test key) over a payload that directly restates
the anchored grant's own ``requirement_id``/``selection_id``/``verifier_identity``/
``permitted_boundary``, and this route now reads the real Project Binding's own public
``human_authority_signing_key`` (via ``boot_context.project_binding``) and passes it through
to the existing Authority owner, which independently re-verifies each candidate declaration's
signature before ever answering ``SELECTED`` -- proving that end-to-end, over the real Store,
is this file's own added concern.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
from typing import Any

import pytest
from tests.difference_helpers import PROJECT_ID as DIFFERENCE_FIXTURE_PROJECT_ID
from tests.evidence_helpers import change_free_verification_evidence_request, sufficiency_request
from tests.fixtures.product_binding import (
    PROJECT_ID,
    bind_project_kwargs,
    genesis_records,
    human_authority_ref,
    sign_human_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority import AuthorityError
from manosube_agent_civilization.authority.identity import verifier_selection_grant_id
from manosube_agent_civilization.binding import bind_project, declare_human_grant
from manosube_agent_civilization.binding.identity import human_grant_declaration_id
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.boot.errors import BootNotFoundError
from manosube_agent_civilization.evidence import (
    EvidenceError,
    derive_evidence,
    evaluate_sufficiency,
)
from manosube_agent_civilization.independent_verification import (
    EvidenceHandoffError,
    VerificationRequirement,
    VerificationRequirementError,
    VerificationResult,
    VerificationValueError,
    VerifierOutputError,
    VerifierSelection,
    route_verification_result_to_evidence,
    run_independent_verification,
)
import manosube_agent_civilization.independent_verification.evidence_handoff as evidence_handoff_module
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_DEFAULT_VERIFIER_IDENTITY = {"kind": "deterministic_test_runner", "id": "VERIFIER-0001"}


def _snapshot(store_root: Path, project_id: str) -> dict[str, str]:
    project_dir = store_root / "projects" / project_id
    if not project_dir.is_dir():
        return {}
    return {
        str(path.relative_to(project_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project_dir.rglob("*"))
        if path.is_file()
    }


def _bound(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store_root, kwargs, result


def _advance(
    store: FileStateStore, project_id: str, genesis_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a real second State transition -- the identical shape
    ``tests/integration/agent_runtime/test_temporary_agent_lifecycle.py::_advance`` already
    builds for its own equivalent proof."""

    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {
        "kind": "state_transition",
        "id": "TX-INDEPENDENT-VERIFICATION-0001",
    }
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-INDEPENDENT-VERIFICATION-0001",
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-06T10:00:00Z",
    }
    return successor, event


#: Every non-default, non-tampered ``verifier_selection_grant`` override this module's tests
#: need -- Structural Review Round 4 (P13-R4) requires each to be a real, durably
#: Store-committed record before any test may name it by reference, so the fixture below
#: commits every one of them up front rather than a test building one in memory and passing
#: its content directly (the exact caller-asserted-content shape Round 4 no longer accepts).
#: The tampered variant's own (clean, pre-tamper) content is deliberately not repeated here:
#: it is committed once, in its already-tampered form, under its own stale pre-tamper id --
#: see ``tampered_source``/``tampered_grant`` below.
_GRANT_OVERRIDE_VARIANTS: tuple[dict[str, Any], ...] = (
    {"project_id": "OTHER-PROJECT"},
    {"requirement_id": "VREQ-OTHER"},
    {"selection_id": "VSEL-OTHER"},
    {"verifier_identity": {"kind": "deterministic_test_runner", "id": "OTHER"}},
    {"permitted_boundary": {"scope": "different"}},
    {"granted_by": {"kind": "human_authority", "id": "AUTH-FABRICATED-BY-CALLER"}},
    {"status": "REVOKED"},
)

_DECLARED_AT = "2026-09-07T13:00:00Z"


@pytest.fixture(scope="module")
def _real_route(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """A real bound Project (Phase 9 Binding), with one real, Store-committed
    ``observation_evidence`` record, the real Human Authority reference Boot independently
    re-verifies for it, and every ``verifier_selection_grant`` variant this module's tests
    need -- also real and Store-committed (Structural Review Round 4, P13-R4) -- everything
    the corrected route needs to admit a genuine, authorized selection, or to refuse one for
    each of this module's required negative reasons."""

    tmp_path = tmp_path_factory.mktemp("independent-verification-bound-project")
    store_root, kwargs, result = _bound(tmp_path)
    project_id = kwargs["project_id"]
    project_binding_id = result["project_binding_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    genesis_state = result["committed_state"]
    evidence_id = "EVID-INDEPENDENT-VERIFICATION-TEST-0001"
    successor, event = _advance(store, project_id, genesis_state)

    grant_fixture_ctx = {"project_id": project_id, "human_authority_ref": human_authority_ref()}
    default_grant = _grant(grant_fixture_ctx)
    variant_grants = [
        _grant(grant_fixture_ctx, **override) for override in _GRANT_OVERRIDE_VARIANTS
    ]
    tampered_source = _grant(grant_fixture_ctx, selection_id="VSEL-TAMPER-SOURCE")
    tampered_grant = dict(tampered_source)
    tampered_grant["status"] = "REVOKED"  # edited after the identity above was already computed

    grant_records = [
        ("verifier_selection_grant", grant["verifier_selection_grant_id"], grant)
        for grant in (default_grant, *variant_grants)
    ] + [
        (
            "verifier_selection_grant",
            tampered_source["verifier_selection_grant_id"],
            tampered_grant,
        )
    ]

    declaration_ctx = {
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "human_authority_ref": grant_fixture_ctx["human_authority_ref"],
    }
    # P13-R5: the one fabricated-authority and one forged declaration variant this module's
    # tests need cannot be produced by `declare_human_grant` at all -- it always resolves the
    # real Human Authority reference from the real committed Project Binding, exactly as it
    # must -- so they are built and committed directly here, the identical shape
    # `declare_human_grant` itself produces, the same way the Round 4 `tampered_grant` above
    # already is.
    fabricated_authority_declaration = _declaration(
        declaration_ctx,
        default_grant,
        declared_by={"kind": "human_authority", "id": "AUTH-FABRICATED-BY-CALLER"},
    )
    # Anchored to a distinct already-committed grant (not `default_grant`) so this record's
    # own pre-tamper content -- and therefore its own computed id -- never collides with the
    # genuine `default_declaration` the real `declare_human_grant` route commits below.
    tampered_declaration_source = _declaration(declaration_ctx, variant_grants[1])
    tampered_declaration = dict(tampered_declaration_source)
    tampered_declaration["status"] = "REVOKED"  # edited after the identity above was computed

    declaration_records = [
        (
            "human_grant_declaration",
            declaration["human_grant_declaration_id"],
            declaration,
        )
        for declaration in (fabricated_authority_declaration,)
    ] + [
        (
            "human_grant_declaration",
            tampered_declaration_source["human_grant_declaration_id"],
            tampered_declaration,
        )
    ]

    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
        records=[
            (
                "observation_evidence",
                evidence_id,
                {"kind": "observation_evidence", "note": "Phase 13 test fixture record"},
            ),
            *grant_records,
            *declaration_records,
        ],
    )

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    assert dict(boot_context.human_authority_ref) == grant_fixture_ctx["human_authority_ref"]

    # P13-R5: the genuine declaration variants -- through the real Binding owner's own
    # `declare_human_grant` route, proving it end-to-end -- committed only now, since it
    # independently re-resolves the real, just-committed Project Binding and grants from the
    # Store rather than trusting any in-memory copy this fixture already built.
    default_declaration = declare_human_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=_ref(default_grant),
        status="ACTIVE",
        declared_at=_DECLARED_AT,
        signature=_sign_declaration(
            {
                "project_id": project_id,
                "project_binding_id": project_binding_id,
                "grant_ref": _ref(default_grant),
                "declared_by": grant_fixture_ctx["human_authority_ref"],
                "requirement_id": default_grant["requirement_id"],
                "selection_id": default_grant["selection_id"],
                "verifier_identity": default_grant["verifier_identity"],
                "permitted_boundary": default_grant["permitted_boundary"],
                "status": "ACTIVE",
                "declared_at": _DECLARED_AT,
            }
        ),
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]
    revoked_declaration = declare_human_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=_ref(default_grant),
        status="REVOKED",
        declared_at=_DECLARED_AT,
        signature=_sign_declaration(
            {
                "project_id": project_id,
                "project_binding_id": project_binding_id,
                "grant_ref": _ref(default_grant),
                "declared_by": grant_fixture_ctx["human_authority_ref"],
                "requirement_id": default_grant["requirement_id"],
                "selection_id": default_grant["selection_id"],
                "verifier_identity": default_grant["verifier_identity"],
                "permitted_boundary": default_grant["permitted_boundary"],
                "status": "REVOKED",
                "declared_at": _DECLARED_AT,
            }
        ),
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]
    other_grant_declaration = declare_human_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=_ref(variant_grants[0]),
        status="ACTIVE",
        declared_at=_DECLARED_AT,
        signature=_sign_declaration(
            {
                "project_id": project_id,
                "project_binding_id": project_binding_id,
                "grant_ref": _ref(variant_grants[0]),
                "declared_by": grant_fixture_ctx["human_authority_ref"],
                "requirement_id": variant_grants[0]["requirement_id"],
                "selection_id": variant_grants[0]["selection_id"],
                "verifier_identity": variant_grants[0]["verifier_identity"],
                "permitted_boundary": variant_grants[0]["permitted_boundary"],
                "status": "ACTIVE",
                "declared_at": _DECLARED_AT,
            }
        ),
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]

    return {
        "store": store,
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "evidence_id": evidence_id,
        "difference_id": "D-INDEPENDENT-VERIFICATION-TEST-0001",
        "human_authority_ref": dict(boot_context.human_authority_ref),
        "default_grant_ref": _ref(default_grant),
        "default_declaration_ref": _decl_ref(default_declaration),
        "revoked_declaration_ref": _decl_ref(revoked_declaration),
        "other_grant_declaration_ref": _decl_ref(other_grant_declaration),
        "fabricated_authority_declaration_ref": _decl_ref(fabricated_authority_declaration),
        "tampered_declaration_source": tampered_declaration_source,
    }


def _requirement(
    evidence_id: str, difference_id: str, human_authority_ref: dict[str, Any], **overrides: Any
) -> VerificationRequirement:
    fields: dict[str, Any] = {
        "requirement_id": "VREQ-0001",
        "project_id": PROJECT_ID,
        "target_refs": [
            {"kind": "observation_evidence", "id": evidence_id},
            {"kind": "difference", "id": difference_id},
        ],
        "verification_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
        "required_conditions": {"minimum_distinctness": "DISTINCT_LINEAGE"},
        "selection_authority_ref": dict(human_authority_ref),
    }
    fields.update(overrides)
    return VerificationRequirement(**fields)


def _selection(human_authority_ref: dict[str, Any], **overrides: Any) -> VerifierSelection:
    fields: dict[str, Any] = {
        "selection_id": "VSEL-0001",
        "project_id": PROJECT_ID,
        "requirement_id": "VREQ-0001",
        "status": "ACTIVE",
        "selection_authority_ref": dict(human_authority_ref),
        "verifier_identity": dict(_DEFAULT_VERIFIER_IDENTITY),
        "permitted_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
    }
    fields.update(overrides)
    return VerifierSelection(**fields)


def _grant(fx: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """One real, canonical, Human-Authority-declared ``verifier_selection_grant`` that binds
    the default fixture selection by construction (Structural Review Round 3, P13-R3-F1) --
    the existing Authority owner's own ``evaluate_verifier_selection`` re-verifies it, never
    trusting a caller-repeated ``human_authority_ref`` alone."""

    fields: dict[str, Any] = {
        "schema_version": "0.1",
        "verifier_selection_grant_id": "",
        "project_id": fx["project_id"],
        "requirement_id": "VREQ-0001",
        "selection_id": "VSEL-0001",
        "verifier_identity": dict(_DEFAULT_VERIFIER_IDENTITY),
        "permitted_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
        "status": "ACTIVE",
        "granted_by": dict(fx["human_authority_ref"]),
    }
    fields.update(overrides)
    fields["verifier_selection_grant_id"] = verifier_selection_grant_id(fields)
    return fields


def _ref(grant: dict[str, Any]) -> dict[str, Any]:
    """The ``{"kind": "verifier_selection_grant", "id": ...}`` reference a real, committed
    grant resolves through (Structural Review Round 4, P13-R4) -- never the grant's own
    content, which ``run_independent_verification`` no longer accepts as an argument."""

    return {"kind": "verifier_selection_grant", "id": grant["verifier_selection_grant_id"]}


def _grant_ref(fx: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """The reference to a grant the ``_real_route`` fixture already committed under these
    exact *overrides* -- content-addressing is deterministic, so recomputing the same
    content here always names the same committed record; this never constructs a grant the
    fixture did not already commit."""

    return _ref(_grant(fx, **overrides))


def _sign_declaration(fields: dict[str, Any]) -> dict[str, Any]:
    """The real signature a Human genuinely declaring *fields* would produce -- the fixed,
    deterministic test key (Structural Review Round 5-R1, P13-R5-R1), over the identical
    field set the real Project Binding's own ``human_authority_signing_key`` is checked
    against by ``evaluate_verifier_selection``."""

    return sign_human_grant_declaration(
        project_id=fields["project_id"],
        project_binding_id=fields["project_binding_id"],
        grant_ref=fields["grant_ref"],
        declared_by=fields["declared_by"],
        requirement_id=fields["requirement_id"],
        selection_id=fields["selection_id"],
        verifier_identity=fields["verifier_identity"],
        permitted_boundary=fields["permitted_boundary"],
        status=fields["status"],
        declared_at=fields["declared_at"],
    )


def _declaration(fx: dict[str, Any], grant: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """One ``human_grant_declaration`` body, in the identical shape the real
    ``declare_human_grant`` route itself produces (Structural Review Round 5, P13-R5;
    signature widened Round 5-R1, P13-R5-R1) -- used only to build the fabricated/forged
    variants that route can never itself produce, since it always resolves the real Human
    Authority reference rather than trusting a caller-supplied one."""

    fields: dict[str, Any] = {
        "schema_version": "0.1",
        "human_grant_declaration_id": "",
        "project_id": fx["project_id"],
        "project_binding_id": fx["project_binding_id"],
        "grant_ref": _ref(grant),
        "declared_by": dict(fx["human_authority_ref"]),
        "requirement_id": grant["requirement_id"],
        "selection_id": grant["selection_id"],
        "verifier_identity": deepcopy(grant["verifier_identity"]),
        "permitted_boundary": deepcopy(grant["permitted_boundary"]),
        "status": "ACTIVE",
        "declared_at": _DECLARED_AT,
    }
    fields.update(overrides)
    fields["signature"] = _sign_declaration(fields)
    fields["human_grant_declaration_id"] = human_grant_declaration_id(fields)
    return fields


def _decl_ref(declaration: dict[str, Any]) -> dict[str, Any]:
    """The ``{"kind": "human_grant_declaration", "id": ...}`` reference a real, committed
    declaration resolves through -- never the declaration's own content, which
    ``run_independent_verification`` no longer accepts as an argument either."""

    return {"kind": "human_grant_declaration", "id": declaration["human_grant_declaration_id"]}


def _identified(func: Any, identity: dict[str, Any] | None = None) -> Any:
    """Attach the ``verifier_identity`` attribute Round 1's route now requires (P13-R1-F1)
    before invocation -- a plain function is a real Python object and may carry one."""

    func.verifier_identity = dict(identity if identity is not None else _DEFAULT_VERIFIER_IDENTITY)
    return func


def _counting_verifier(
    payload: dict[str, Any], identity: dict[str, Any] | None = None
) -> tuple[list[int], Any]:
    calls: list[int] = []

    def verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        calls.append(1)
        return payload

    return calls, _identified(verifier, identity)


def _run(
    fx: dict[str, Any],
    requirement: VerificationRequirement,
    selection: VerifierSelection,
    verifier: Any,
    *,
    project_id: str | None = None,
    grant_refs: list[dict[str, Any]] | None = None,
    declaration_refs: list[dict[str, Any]] | None = None,
) -> VerificationResult:
    return run_independent_verification(
        fx["store"],
        project_id=project_id if project_id is not None else fx["project_id"],
        project_binding_id=fx["project_binding_id"],
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier_selection_grant_refs=(
            grant_refs if grant_refs is not None else [fx["default_grant_ref"]]
        ),
        human_grant_declaration_refs=(
            declaration_refs if declaration_refs is not None else [fx["default_declaration_ref"]]
        ),
        verifier=verifier,
    )


# --- the canonical successful route --------------------------------------------------- #


def test_successful_route_returns_a_verified_result_with_zero_store_mutation(
    _real_route: dict[str, Any],
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}],
            "observations": {"summary": "independently reproduced the reported outcome"},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)

    assert isinstance(result, VerificationResult)
    assert result.status == "VERIFIED"
    assert result.requirement_id == "VREQ-0001"
    assert result.selection_id == "VSEL-0001"
    assert result.project_id == project_id
    assert dict(result.target_refs[0]) == {
        "kind": "observation_evidence",
        "id": _real_route["evidence_id"],
    }
    assert dict(result.verifier_identity) == _DEFAULT_VERIFIER_IDENTITY
    assert dict(result.selection_authority_ref) == _real_route["human_authority_ref"]
    assert dict(result.verification_boundary) == {"scope": "repository", "boundary_id": "VB-0001"}
    assert dict(result.input_refs[0]) == {"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}
    assert dict(result.observations) == {"summary": "independently reproduced the reported outcome"}
    assert calls == [1]
    assert _snapshot(store.root, project_id) == before


def test_result_fields_are_immutable(_real_route: dict[str, Any]) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0001"}],
            "observations": {},
        }
    )
    result = _run(_real_route, requirement, selection, verifier)
    with pytest.raises(AttributeError):
        result.status = "FAILED"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.target_refs[0]["kind"] = "tampered"  # type: ignore[index]


def test_requirement_and_selection_fields_are_immutable(_real_route: dict[str, Any]) -> None:
    requirement = _requirement("EVIDENCE-1", "D-1", _real_route["human_authority_ref"])
    with pytest.raises(AttributeError):
        requirement.project_id = "OTHER"  # type: ignore[misc]
    with pytest.raises(TypeError):
        requirement.verification_boundary["scope"] = "tampered"  # type: ignore[index]

    selection = _selection(_real_route["human_authority_ref"])
    with pytest.raises(AttributeError):
        selection.status = "REVOKED"  # type: ignore[misc]
    with pytest.raises(TypeError):
        selection.verifier_identity["kind"] = "tampered"  # type: ignore[index]


def test_deep_freeze_rejects_a_set_and_other_unsupported_mutable_values(
    _real_route: dict[str, Any],
) -> None:
    """Structural Review Round 1 (P13-R1-F3): a ``set`` (or any other value that is
    neither a Mapping, Sequence, nor JSON-compatible scalar) must never be silently
    accepted as though it were frozen."""

    with pytest.raises(VerificationValueError):
        _requirement(
            _real_route["evidence_id"],
            _real_route["difference_id"],
            _real_route["human_authority_ref"],
            required_conditions={"tags": {"a", "b"}},
        )
    with pytest.raises(VerificationValueError):
        _selection(_real_route["human_authority_ref"], verifier_identity={"nested": object()})


# --- required rejection proofs: requirement/selection/boundary/target admission ------- #


def test_wrong_requested_project_id_is_rejected(_real_route: dict[str, Any]) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier, project_id="OTHER-PROJECT")
    assert calls == []


@pytest.mark.parametrize(
    "mutate_requirement,mutate_selection,expected_message_fragment",
    [
        (lambda req: replace(req, project_id="OTHER"), lambda sel: sel, "project_id"),
        (lambda req: req, lambda sel: replace(sel, project_id="OTHER"), "project_id"),
        (lambda req: req, lambda sel: replace(sel, requirement_id="OTHER-REQ"), "does not apply"),
        (lambda req: req, lambda sel: replace(sel, status="REVOKED"), "not ACTIVE"),
        (lambda req: req, lambda sel: replace(sel, status="EXPIRED"), "not ACTIVE"),
        (lambda req: req, lambda sel: replace(sel, status="BOGUS"), "not a recognized"),
        (
            lambda req: req,
            lambda sel: replace(
                sel, selection_authority_ref={"kind": "human_authority", "id": "OTHER"}
            ),
            "Human Authority",
        ),
        (
            lambda req: req,
            lambda sel: replace(sel, permitted_boundary={"scope": "different"}),
            "permitted_boundary",
        ),
    ],
)
def test_requirement_selection_mismatches_are_rejected_before_the_verifier_runs(
    _real_route: dict[str, Any],
    mutate_requirement: Any,
    mutate_selection: Any,
    expected_message_fragment: str,
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = mutate_requirement(
        _requirement(
            _real_route["evidence_id"],
            _real_route["difference_id"],
            _real_route["human_authority_ref"],
        )
    )
    selection = mutate_selection(_selection(_real_route["human_authority_ref"]))
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match=expected_message_fragment):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_fabricated_but_self_consistent_authority_ref_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """Structural Review Round 1 (P13-R1-F2): both ``selection_authority_ref`` values
    agreeing with *each other* is not authorization -- they must agree with the real,
    Boot-verified Human Authority reference. Two caller-fabricated, mutually-equal but
    fake references must still be refused, and the verifier must never be called."""

    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    fake_ref = {"kind": "human_authority", "id": "FABRICATED-BY-CALLER"}
    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        selection_authority_ref=dict(fake_ref),
    )
    selection = _selection(
        _real_route["human_authority_ref"], selection_authority_ref=dict(fake_ref)
    )
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="Human Authority"):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_an_empty_authority_ref_agreed_by_both_callers_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """The exact malformed case Codex's real review named: ``selection_authority_ref={}``
    on both sides must still be refused -- equality between two malformed values is not
    Authority."""

    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        selection_authority_ref={},
    )
    selection = _selection(_real_route["human_authority_ref"], selection_authority_ref={})
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


@pytest.mark.parametrize(
    "target_refs",
    [
        [],
        [{"kind": "observation_evidence"}],
        [{"id": "EVID-0001"}],
        [{"kind": "authority_decision", "id": "AUTH-1"}],
        [{"kind": "state", "id": "S-1"}],
    ],
)
def test_malformed_or_out_of_vocabulary_target_refs_are_rejected(
    _real_route: dict[str, Any], target_refs: list[dict[str, Any]]
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        target_refs=target_refs,
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_unresolvable_evidence_target_is_rejected_and_never_reaches_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        "EVIDENCE-DOES-NOT-EXIST",
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        target_refs=[{"kind": "observation_evidence", "id": "EVIDENCE-DOES-NOT-EXIST"}],
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="does not resolve"):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_difference_or_change_target_is_never_resolved_against_the_store(
    _real_route: dict[str, Any],
) -> None:
    """Difference and Change are never Store-owned record kinds in this vertical -- a
    fabricated ``difference``/``change`` id must not be rejected by Store resolution (only
    an ``observation_evidence`` target is ever resolved here)."""

    requirement = _requirement(
        _real_route["evidence_id"],
        _real_route["difference_id"],
        _real_route["human_authority_ref"],
        target_refs=[
            {"kind": "difference", "id": "D-DOES-NOT-EXIST"},
            {"kind": "change", "id": "CHG-DOES-NOT-EXIST"},
        ],
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": {},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)
    assert calls == [1]
    assert result.status == "VERIFIED"


# --- required rejection proofs: verifier identity binding (P13-R1-F1) ----------------- #


def test_a_callable_whose_declared_identity_mismatches_the_selection_is_never_invoked(
    _real_route: dict[str, Any],
) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}},
        identity={"kind": "deterministic_test_runner", "id": "A-DIFFERENT-VERIFIER"},
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_callable_with_no_declared_identity_is_never_invoked(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls: list[int] = []

    def bare_verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        calls.append(1)
        return {"status": "VERIFIED", "input_refs": [], "observations": {}}

    with pytest.raises(VerificationRequirementError, match="verifier_identity"):
        _run(_real_route, requirement, selection, bare_verifier)
    assert calls == []


def test_a_callable_with_an_unreadable_declared_identity_is_never_invoked(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    verifier.verifier_identity = "not-a-mapping"

    with pytest.raises(VerificationRequirementError, match="verifier_identity"):
        _run(_real_route, requirement, selection, verifier)
    assert calls == []


def test_only_the_correctly_identified_verifier_is_invoked_and_attributed(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": {},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)
    assert calls == [1]
    assert dict(result.verifier_identity) == _DEFAULT_VERIFIER_IDENTITY


# --- required rejection proofs: the verifier's own output shape ---------------------- #


@pytest.mark.parametrize(
    "payload",
    [
        "not-a-mapping",
        {"status": "MAYBE", "input_refs": [], "observations": {}},
        {"status": "VERIFIED", "input_refs": "not-a-list", "observations": {}},
        {"status": "VERIFIED", "input_refs": [{"kind": "source_snapshot"}], "observations": {}},
        {"status": "VERIFIED", "input_refs": [{"id": "SS-1"}], "observations": {}},
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": "not-a-mapping",
        },
    ],
)
def test_malformed_verifier_output_is_rejected(_real_route: dict[str, Any], payload: Any) -> None:
    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier(payload)

    with pytest.raises(VerifierOutputError):
        _run(_real_route, requirement, selection, verifier)
    assert _snapshot(store.root, project_id) == before


def test_verifier_citing_no_input_at_all_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, empty_input_verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerifierOutputError, match="no input_refs"):
        _run(_real_route, requirement, selection, empty_input_verifier)


def test_verifier_citing_only_the_target_refs_is_rejected_as_indistinguishable_provenance(
    _real_route: dict[str, Any],
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])

    def echo_verifier(*, requirement: VerificationRequirement, selection: VerifierSelection) -> Any:
        return {
            "status": "VERIFIED",
            "input_refs": [dict(ref) for ref in requirement.target_refs],
            "observations": {},
        }

    _identified(echo_verifier)

    with pytest.raises(VerifierOutputError, match="implementation-indistinguishable"):
        _run(_real_route, requirement, selection, echo_verifier)


@pytest.mark.parametrize("status", ["FAILED", "INSUFFICIENT"])
def test_a_non_unavailable_negative_result_still_requires_distinguishable_input(
    _real_route: dict[str, Any], status: str
) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier({"status": status, "input_refs": [], "observations": {}})

    with pytest.raises(VerifierOutputError):
        _run(_real_route, requirement, selection, verifier)


def test_unavailable_status_with_empty_input_refs_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """Structural Review Round 2 (P13-R2-F3): Round 0's disclosed ``UNAVAILABLE`` exemption
    from the independence check is superseded -- an ``UNAVAILABLE`` result with no
    ``input_refs`` at all is rejected exactly like any other status would be, not silently
    accepted as an unconstructible truthful report."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, unavailable_verifier = _counting_verifier(
        {"status": "UNAVAILABLE", "input_refs": [], "observations": {"reason": "offline"}}
    )

    with pytest.raises(VerifierOutputError, match="no input_refs"):
        _run(_real_route, requirement, selection, unavailable_verifier)


def test_unavailable_status_citing_only_target_refs_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """Structural Review Round 2 (P13-R2-F3): an ``UNAVAILABLE`` result that echoes only the
    requirement's own ``target_refs`` is implementation-indistinguishable provenance, exactly
    as for any other status -- it must still cite the explicit boundary/capability/
    observation/Evidence input that actually grounds why evaluation was not possible."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])

    def echo_unavailable_verifier(
        *, requirement: VerificationRequirement, selection: VerifierSelection
    ) -> Any:
        return {
            "status": "UNAVAILABLE",
            "input_refs": [dict(ref) for ref in requirement.target_refs],
            "observations": {"reason": "offline"},
        }

    _identified(echo_unavailable_verifier)

    with pytest.raises(VerifierOutputError, match="implementation-indistinguishable"):
        _run(_real_route, requirement, selection, echo_unavailable_verifier)


@pytest.mark.parametrize("status", ["FAILED", "INSUFFICIENT", "UNAVAILABLE"])
def test_every_real_negative_outcome_is_representable_with_distinguishable_input(
    _real_route: dict[str, Any], status: str
) -> None:
    """The failure statuses are ordinary results this route returns unmodified -- it never
    substitutes a status, and a negative outcome with genuine independent input is accepted
    exactly as a VERIFIED one is."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    _, verifier = _counting_verifier(
        {
            "status": status,
            "input_refs": [{"kind": "source_snapshot", "id": "SS-INDEPENDENT-0002"}],
            "observations": {"reason_code": "OBSERVED_MISMATCH"},
        }
    )

    result = _run(_real_route, requirement, selection, verifier)
    assert result.status == status


# --- required rejection proofs: Authority-owned verifier selection decision (P13-R3-F1) - #


def test_no_verifier_selection_grants_is_rejected_and_never_calls_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    """The finding's own first required proof: a caller-created selection that merely repeats
    known-real values (project_id, requirement_id, verifier_identity, permitted_boundary,
    status, the real Boot-verified Human Authority reference) is not itself an Authority
    Decision. With no grant ref supplied at all, the existing Authority owner's own
    ``evaluate_verifier_selection`` cannot answer ``SELECTED``, and the verifier is never
    called."""

    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="SELECTED"):
        _run(_real_route, requirement, selection, verifier, grant_refs=[])
    assert calls == []
    assert _snapshot(store.root, project_id) == before


# --- required rejection proofs: grant provenance is Store-resolved, never caller-supplied --- #
# --- content (Structural Review Round 4, P13-R4, Authority Provenance Bypass, P13-R3-F2) --- #


def test_a_grant_ref_naming_an_uncommitted_record_is_rejected_and_never_calls_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    """The Round 4 finding's own core required proof: a ref naming a grant that was never
    durably committed to the Store refuses before the Authority owner or the verifier is
    ever reached, with zero Store mutation -- a grant asserted only in this one call's own
    arguments cannot reach SELECTED, however plausible its id looks."""

    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    never_committed = _grant(_real_route, selection_id="VSEL-NEVER-COMMITTED")

    with pytest.raises(VerificationRequirementError, match="does not resolve"):
        _run(_real_route, requirement, selection, verifier, grant_refs=[_ref(never_committed)])
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_grant_content_supplied_directly_instead_of_a_reference_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """Grant *content* is no longer an accepted argument shape at all: a caller who supplies
    the whole ``verifier_selection_grant`` body where a ``{"kind", "id"}`` reference belongs
    -- the exact caller-asserted-provenance shape Round 3 accepted and Round 4 closes -- is
    rejected as a malformed reference, never treated as a grant."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    raw_content = _grant(_real_route)

    with pytest.raises(VerificationRequirementError, match="no readable kind"):
        _run(_real_route, requirement, selection, verifier, grant_refs=[raw_content])
    assert calls == []


def test_a_grant_ref_naming_the_wrong_kind_is_rejected(_real_route: dict[str, Any]) -> None:
    """A syntactically well-formed {"kind", "id"} reference whose kind is not
    ``verifier_selection_grant`` -- e.g. the very ``observation_evidence`` record this same
    fixture also committed -- is rejected before any Store resolution is even attempted."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    wrong_kind_ref = {"kind": "observation_evidence", "id": _real_route["evidence_id"]}

    with pytest.raises(VerificationRequirementError, match="permitted set"):
        _run(_real_route, requirement, selection, verifier, grant_refs=[wrong_kind_ref])
    assert calls == []


@pytest.mark.parametrize(
    ("label", "override"),
    [
        ("project", {"project_id": "OTHER-PROJECT"}),
        ("requirement", {"requirement_id": "VREQ-OTHER"}),
        ("selection", {"selection_id": "VSEL-OTHER"}),
        (
            "verifier identity",
            {"verifier_identity": {"kind": "deterministic_test_runner", "id": "OTHER"}},
        ),
        ("boundary", {"permitted_boundary": {"scope": "different"}}),
    ],
)
def test_a_grant_naming_a_different_selection_does_not_bind(
    _real_route: dict[str, Any], label: str, override: dict[str, Any]
) -> None:
    """A grant that binds every field but one is not *this* selection's grant at all."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="SELECTED"):
        _run(
            _real_route,
            requirement,
            selection,
            verifier,
            grant_refs=[_grant_ref(_real_route, **override)],
        )
    assert calls == []


def test_a_grant_declared_by_a_fabricated_human_authority_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """A grant may repeat every other field of the real selection exactly and still not
    bind, if its own ``granted_by`` does not canonical-reference-equal the real,
    Boot-verified Human Authority reference -- self-fabricated provenance never substitutes
    for the genuine one."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    fabricated_ref = _grant_ref(
        _real_route, granted_by={"kind": "human_authority", "id": "AUTH-FABRICATED-BY-CALLER"}
    )

    with pytest.raises(VerificationRequirementError, match="SELECTED"):
        _run(_real_route, requirement, selection, verifier, grant_refs=[fabricated_ref])
    assert calls == []


def test_a_grant_whose_real_status_is_not_active_does_not_bind(
    _real_route: dict[str, Any],
) -> None:
    """``run_independent_verification`` itself already requires ``verifier_selection.status
    == "ACTIVE"`` before this Authority-owned check ever runs (frozen semantic decision, kept
    from before Round 3), so a grant whose own real status differs -- ``REVOKED`` here -- can
    never agree with the declared ``selection_status`` this route passes through: it is
    refused as a status mismatch, not silently treated as binding."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    revoked_ref = _grant_ref(_real_route, status="REVOKED")

    with pytest.raises(VerificationRequirementError, match="GRANT_SELECTION_STATUS_MISMATCH"):
        _run(_real_route, requirement, selection, verifier, grant_refs=[revoked_ref])
    assert calls == []


def test_a_tampered_grant_propagates_the_existing_authority_owners_own_typed_error(
    _real_route: dict[str, Any],
) -> None:
    """A grant edited after its own content address was computed is a forged record, exactly
    the case ``authority.conformance.admit`` already refuses for every other Authority-owned
    record kind -- the resulting ``AuthorityError`` propagates unchanged, never caught or
    reclassified by this route. The fixture commits this exact tampered body under its own
    (now stale) pre-tamper id (Structural Review Round 4, P13-R4): durable Store commission
    alone is not sufficient provenance either -- a tampered record's own content-address
    self-consistency still fails inside the existing Authority owner's own admission gate."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    # The pre-tamper content whose id the fixture committed a post-tamper body under.
    tampered_source = _grant(_real_route, selection_id="VSEL-TAMPER-SOURCE")

    with pytest.raises(AuthorityError, match="identity does not match"):
        _run(_real_route, requirement, selection, verifier, grant_refs=[_ref(tampered_source)])
    assert calls == []


def test_only_a_genuine_grant_permits_exactly_one_verifier_call(
    _real_route: dict[str, Any],
) -> None:
    """The control: a real, canonical, Human-Authority-declared grant binding every field
    exactly is required and sufficient for the existing Authority owner to answer
    ``SELECTED`` -- and only then is the verifier ever invoked, exactly once."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": {},
        }
    )

    result = _run(
        _real_route, requirement, selection, verifier, grant_refs=[_grant_ref(_real_route)]
    )
    assert calls == [1]
    assert result.status == "VERIFIED"


# --- required rejection proofs: the Human Grant Declaration anchor is Store-resolved, ------ #
# --- never caller-supplied content (Structural Review Round 5, P13-R5) --------------------- #


def test_no_declaration_refs_is_rejected_and_never_calls_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    """The finding's own central case: a genuinely Store-resolved, self-consistent grant is
    still not, by itself, proof that a Human declared it. With no declaration ref supplied at
    all, ``evaluate_verifier_selection`` cannot answer ``SELECTED``, and the verifier is
    never called."""

    store: FileStateStore = _real_route["store"]
    project_id = _real_route["project_id"]
    before = _snapshot(store.root, project_id)

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="DECLARATION_MISSING"):
        _run(_real_route, requirement, selection, verifier, declaration_refs=[])
    assert calls == []
    assert _snapshot(store.root, project_id) == before


def test_a_declaration_ref_naming_an_uncommitted_record_is_rejected_and_never_calls_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    """A ref naming a declaration that was never durably committed to the Store refuses
    before the Authority owner or the verifier is ever reached, exactly as an unresolvable
    grant ref already does."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    never_committed = {"kind": "human_grant_declaration", "id": "HGD-" + "0" * 64}

    with pytest.raises(VerificationRequirementError, match="does not resolve"):
        _run(_real_route, requirement, selection, verifier, declaration_refs=[never_committed])
    assert calls == []


def test_declaration_content_supplied_directly_instead_of_a_reference_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """Declaration *content* is never an accepted argument shape either -- a caller who
    supplies the whole ``human_grant_declaration`` body where a ``{"kind", "id"}`` reference
    belongs is rejected as a malformed reference, never treated as a declaration."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    raw_content = _real_route["tampered_declaration_source"]

    with pytest.raises(VerificationRequirementError, match="no readable kind"):
        _run(_real_route, requirement, selection, verifier, declaration_refs=[raw_content])
    assert calls == []


def test_a_declaration_ref_naming_the_wrong_kind_is_rejected(_real_route: dict[str, Any]) -> None:
    """A syntactically well-formed {"kind", "id"} reference whose kind is not
    ``human_grant_declaration`` -- e.g. the default grant this same fixture also committed --
    is rejected before any Store resolution is even attempted."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    wrong_kind_ref = _real_route["default_grant_ref"]

    with pytest.raises(VerificationRequirementError, match="permitted set"):
        _run(_real_route, requirement, selection, verifier, declaration_refs=[wrong_kind_ref])
    assert calls == []


def test_a_declaration_anchoring_a_different_grant_does_not_bind(
    _real_route: dict[str, Any],
) -> None:
    """A declaration that exists, and is otherwise genuine, but anchors some other grant
    entirely is not a weaker anchor for the winning grant -- it is not a candidate for it at
    all, and the winning grant is refused exactly as if no declaration had been supplied."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="DECLARATION_MISSING"):
        _run(
            _real_route,
            requirement,
            selection,
            verifier,
            declaration_refs=[_real_route["other_grant_declaration_ref"]],
        )
    assert calls == []


def test_a_declaration_declared_by_a_fabricated_human_authority_is_rejected(
    _real_route: dict[str, Any],
) -> None:
    """A declaration may anchor the winning grant exactly and still not bind, if its own
    ``declared_by`` does not canonical-reference-equal the real, Boot-verified Human
    Authority reference -- self-fabricated provenance never substitutes for the genuine one,
    the identical class of check already applied to a grant's own ``granted_by``, now applied
    one layer deeper."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="DECLARATION_AUTHORITY_MISMATCH"):
        _run(
            _real_route,
            requirement,
            selection,
            verifier,
            declaration_refs=[_real_route["fabricated_authority_declaration_ref"]],
        )
    assert calls == []


def test_a_declaration_whose_real_status_is_not_active_does_not_bind(
    _real_route: dict[str, Any],
) -> None:
    """A declaration that genuinely anchors the winning grant, by the real Human Authority,
    but is itself no longer ``ACTIVE`` withholds the selection exactly as a non-``ACTIVE``
    grant already does -- explicit revocation handling, never an exception."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError, match="DECLARATION_NOT_ACTIVE"):
        _run(
            _real_route,
            requirement,
            selection,
            verifier,
            declaration_refs=[_real_route["revoked_declaration_ref"]],
        )
    assert calls == []


def test_a_tampered_declaration_propagates_the_existing_authority_owners_own_typed_error(
    _real_route: dict[str, Any],
) -> None:
    """A declaration edited after its own content address was computed is a forged record,
    exactly the case ``authority.conformance.admit`` already refuses for every other
    Authority-owned record kind -- the resulting ``AuthorityError`` propagates unchanged,
    never caught or reclassified by this route."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )
    # The pre-tamper content whose id the fixture committed a post-tamper body under.
    tampered_source = _real_route["tampered_declaration_source"]

    with pytest.raises(AuthorityError, match="identity does not match"):
        _run(
            _real_route,
            requirement,
            selection,
            verifier,
            declaration_refs=[_decl_ref(tampered_source)],
        )
    assert calls == []


def test_only_a_genuine_declaration_permits_exactly_one_verifier_call(
    _real_route: dict[str, Any],
) -> None:
    """The control: a real, canonical Human Grant Declaration genuinely anchoring the winning
    grant is required and sufficient for the existing Authority owner to answer ``SELECTED``
    -- and only then is the verifier ever invoked, exactly once."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-1"}],
            "observations": {},
        }
    )

    result = _run(
        _real_route,
        requirement,
        selection,
        verifier,
        declaration_refs=[_real_route["default_declaration_ref"]],
    )
    assert calls == [1]
    assert result.status == "VERIFIED"


# --- construction-time input type checks ----------------------------------------------- #


def test_non_instance_requirement_or_selection_is_rejected(_real_route: dict[str, Any]) -> None:
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        run_independent_verification(
            _real_route["store"],
            project_id=_real_route["project_id"],
            project_binding_id=_real_route["project_binding_id"],
            verification_requirement={"not": "a requirement instance"},  # type: ignore[arg-type]
            verifier_selection=selection,
            verifier_selection_grant_refs=[_grant_ref(_real_route)],
            human_grant_declaration_refs=[_real_route["default_declaration_ref"]],
            verifier=verifier,
        )
    assert calls == []


def test_non_canonical_project_id_is_rejected(_real_route: dict[str, Any]) -> None:
    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(VerificationRequirementError):
        _run(_real_route, requirement, selection, verifier, project_id="../escape")
    assert calls == []


def test_boot_project_failure_propagates_unchanged_and_never_calls_the_verifier(
    _real_route: dict[str, Any],
) -> None:
    """A wrong ``project_binding_id`` makes ``boot_project`` itself fail closed -- that
    failure propagates unchanged (frozen semantic decision 6/9), and the verifier is never
    reached."""

    requirement = _requirement(
        _real_route["evidence_id"], _real_route["difference_id"], _real_route["human_authority_ref"]
    )
    selection = _selection(_real_route["human_authority_ref"])
    calls, verifier = _counting_verifier(
        {"status": "VERIFIED", "input_refs": [], "observations": {}}
    )

    with pytest.raises(BootNotFoundError):
        run_independent_verification(
            _real_route["store"],
            project_id=_real_route["project_id"],
            project_binding_id="PB-DOES-NOT-EXIST",
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier_selection_grant_refs=[_grant_ref(_real_route)],
            human_grant_declaration_refs=[_real_route["default_declaration_ref"]],
            verifier=verifier,
        )
    assert calls == []


# --- route_verification_result_to_evidence: the real handoff (Structural Review Round 2, ---
# --- P13-R2-F2) ------------------------------------------------------------------------ #


def _handoff_verification_result(
    *, target_refs: tuple[dict[str, Any], ...] | None = None
) -> VerificationResult:
    """A minimal, real ``VerificationResult`` about the Difference
    ``change_free_verification_evidence_request()``'s own default request derives against --
    computed, never assumed, exactly as ``tests.evidence_helpers.sufficiency_request`` derives
    its own default identity the same way."""

    difference_id = str(
        derive_evidence(change_free_verification_evidence_request())["difference_ref"]["id"]
    )
    refs = (
        target_refs if target_refs is not None else ({"kind": "difference", "id": difference_id},)
    )
    return VerificationResult(
        status="VERIFIED",
        requirement_id="VREQ-HANDOFF-0001",
        selection_id="VSEL-HANDOFF-0001",
        project_id=DIFFERENCE_FIXTURE_PROJECT_ID,
        target_refs=refs,
        verifier_identity=dict(_DEFAULT_VERIFIER_IDENTITY),
        selection_authority_ref={"kind": "human_authority", "id": "AUTH-0001"},
        verification_boundary={"scope": "repository", "boundary_id": "VB-0001"},
        input_refs=({"kind": "source_snapshot", "id": "SS-HANDOFF-0001"},),
        observations={"summary": "independently reproduced the reported outcome"},
    )


def test_handoff_derives_a_genuine_evidence_record_matching_the_verification_result() -> None:
    verification_result = _handoff_verification_result()
    evidence_request = change_free_verification_evidence_request(provenance=None)

    evidence = route_verification_result_to_evidence(verification_result, evidence_request)

    assert evidence["target"]["project_id"] == verification_result.project_id
    named_difference_id = verification_result.target_refs[0]["id"]
    assert evidence["difference_ref"]["id"] == named_difference_id


def test_handoff_rejects_a_non_verification_result_instance() -> None:
    with pytest.raises(EvidenceHandoffError):
        route_verification_result_to_evidence(
            {"not": "a VerificationResult"},  # type: ignore[arg-type]
            change_free_verification_evidence_request(),
        )


def test_handoff_rejects_a_non_mapping_evidence_request() -> None:
    with pytest.raises(EvidenceHandoffError):
        route_verification_result_to_evidence(
            _handoff_verification_result(),
            "not-a-mapping",  # type: ignore[arg-type]
        )


def test_handoff_rejects_a_change_bound_evidence_request() -> None:
    evidence_request = change_free_verification_evidence_request()
    evidence_request["change_request"] = {"not": "None"}

    with pytest.raises(EvidenceHandoffError, match="Change-free"):
        route_verification_result_to_evidence(_handoff_verification_result(), evidence_request)


def test_handoff_rejects_a_post_change_observation_request() -> None:
    evidence_request = change_free_verification_evidence_request()
    evidence_request["post_change_observation_request"] = {"not": "None"}

    with pytest.raises(EvidenceHandoffError, match="post_change_observation_request"):
        route_verification_result_to_evidence(_handoff_verification_result(), evidence_request)


def test_handoff_rejects_a_request_with_no_verification_observation_request() -> None:
    evidence_request = change_free_verification_evidence_request()
    evidence_request["verification_observation_request"] = None

    with pytest.raises(EvidenceHandoffError, match="verification_observation_request"):
        route_verification_result_to_evidence(_handoff_verification_result(), evidence_request)


def test_handoff_rejects_a_derived_evidence_record_naming_a_different_project() -> None:
    verification_result = _handoff_verification_result()
    mismatched_result = replace(verification_result, project_id="A-DIFFERENT-PROJECT")

    with pytest.raises(EvidenceHandoffError, match="different project"):
        route_verification_result_to_evidence(
            mismatched_result, change_free_verification_evidence_request(provenance=None)
        )


def test_handoff_rejects_a_derived_evidence_record_bound_to_an_unnamed_difference() -> None:
    verification_result = _handoff_verification_result(
        target_refs=({"kind": "difference", "id": "D-VERIFICATION-RESULT-NEVER-NAMED"},)
    )

    with pytest.raises(EvidenceHandoffError, match="never named"):
        route_verification_result_to_evidence(
            verification_result, change_free_verification_evidence_request(provenance=None)
        )


def test_existing_evidence_owner_admission_failures_propagate_unchanged() -> None:
    """``EvidenceError`` is the existing Evidence owner's own failure mode -- this handoff
    neither catches nor reclassifies it (Structural Review Round 2, P13-R2-F2)."""

    evidence_request = change_free_verification_evidence_request(provenance=None)
    evidence_request["artifact_references"] = "not-a-list"

    with pytest.raises(EvidenceError):
        route_verification_result_to_evidence(_handoff_verification_result(), evidence_request)


def test_handoff_produced_request_is_accepted_by_the_existing_sufficiency_owners_own_request_shape() -> (
    None
):
    """Structural Review Round 2 (P13-R2-F2): once the handoff returns a genuine canonical
    Evidence record, the *request* that produced it is already exactly the shape the existing
    evidence-sufficiency owner's own public ``evaluate_sufficiency`` accepts -- this test
    proves connectability without production code calling ``evaluate_sufficiency`` itself
    (which would make this package a second sufficiency owner)."""

    verification_result = _handoff_verification_result()
    evidence_request = change_free_verification_evidence_request(provenance=None)

    evidence = route_verification_result_to_evidence(verification_result, evidence_request)

    # The handoff injects the provenance it constructs into its own internal copy of the
    # request (never mutating the caller's) -- so the request this test hands onward must
    # carry the identical, already-verified value the returned Evidence record itself holds,
    # not the None this test's own copy still carries after the call returns.
    evidence_request["verification_result_provenance"] = evidence["verification_result_provenance"]

    result = evaluate_sufficiency(
        sufficiency_request(
            difference_id=str(evidence["difference_ref"]["id"]),
            evidence_requests=[evidence_request],
        )
    )
    assert result["evidence_sufficiency_result"]["evidence_sufficiency_id"]


# --------------------------------------------------------------------------- #
# verification_result_provenance (Structural Review Round 6, P13-R6,
# ADOPT_P13_R6_PROVENANCE_COMPLETE_EVIDENCE_HANDOFF)
# --------------------------------------------------------------------------- #


def test_handoff_derives_evidence_whose_provenance_matches_the_verification_result() -> None:
    """The record the handoff returns carries the real VerificationResult's own ten fields,
    constructed by the handoff itself -- never by the caller."""

    verification_result = _handoff_verification_result()
    evidence_request = change_free_verification_evidence_request(provenance=None)

    evidence = route_verification_result_to_evidence(verification_result, evidence_request)

    provenance = evidence["verification_result_provenance"]
    assert provenance["status"] == verification_result.status
    assert provenance["requirement_id"] == verification_result.requirement_id
    assert provenance["selection_id"] == verification_result.selection_id
    assert provenance["project_id"] == verification_result.project_id
    assert provenance["target_refs"]["members"] == [
        dict(ref) for ref in verification_result.target_refs
    ]
    assert provenance["verifier_identity"] == dict(verification_result.verifier_identity)
    assert provenance["selection_authority_ref"] == dict(
        verification_result.selection_authority_ref
    )
    assert provenance["verification_boundary"] == dict(verification_result.verification_boundary)
    assert provenance["input_refs"]["members"] == [
        dict(ref) for ref in verification_result.input_refs
    ]
    assert provenance["observations"] == dict(verification_result.observations)


def test_handoff_rejects_a_caller_supplied_verification_result_provenance() -> None:
    """The handoff constructs this field itself and never accepts, nor silently overwrites,
    one a caller already placed on ``evidence_request``."""

    evidence_request = change_free_verification_evidence_request()
    evidence_request["verification_result_provenance"] = {"caller": "supplied"}

    with pytest.raises(EvidenceHandoffError, match="verification_result_provenance"):
        route_verification_result_to_evidence(_handoff_verification_result(), evidence_request)


def test_handoff_refuses_to_return_evidence_whose_provenance_does_not_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A defensive check on a predecessor this handoff does not itself control: if
    ``derive_evidence`` ever returned a record whose own provenance disagreed with what the
    handoff constructed, the handoff must refuse it rather than return a mismatched record."""

    real_derive_evidence = derive_evidence

    def _tampering_derive_evidence(request: dict[str, Any]) -> dict[str, Any]:
        record = real_derive_evidence(request)
        tampered = dict(record)
        tampered["verification_result_provenance"] = dict(
            tampered["verification_result_provenance"] or {}, status="FAILED"
        )
        return tampered

    monkeypatch.setattr(evidence_handoff_module, "derive_evidence", _tampering_derive_evidence)

    with pytest.raises(EvidenceHandoffError, match="does not exactly equal"):
        route_verification_result_to_evidence(
            _handoff_verification_result(),
            change_free_verification_evidence_request(provenance=None),
        )
