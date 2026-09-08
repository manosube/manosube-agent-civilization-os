"""Phase 14 (Issue #62), V3: real GitHub vertical proof harness.

SHUKOU's own implementation adoption
(``ADOPT_P14_D001_PROJECTION_ENVELOPE_IMPLEMENTATION``, Issue #62) authorizes implementation,
local/controlled tests, and "preparation of the V3 proof harness" -- and, in the identical
comment, explicitly withholds authority to *execute* any of it against a live target:

```text
V3_REAL_GITHUB_PROOF_REQUIRED=true
V3_TARGET_REPOSITORY_NOT_YET_FROZEN=true
V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false
PRE_V3_EXACT_TARGET_AND_ARTIFACT_BOUNDARY_RECONFIRMATION_REQUIRED=true
```

Every test that would perform a live write is therefore ``pytest.mark.skip``, with that exact
citation as the skip reason -- the harness exists (it constructs a real
:class:`~manosube_agent_civilization.projection.github_adapter.RealGitHubAdapter` and a real
``project_to_github`` call, over a real bound Project), but no assertion in this file runs
against a live network until the exact target repository, artifact count, naming, cleanup, and
no-merge boundary are separately frozen and re-confirmed by a further SHUKOU decision.

Structural Review Round 1 (Issue #62, P14-R1-F5) requires this harness to be genuinely
executable, not merely prepared: :func:`_run_vertical_proof` is the one shared body every
projection kind's own test calls, parameterized only by which adapter it is given. Three
tests below (``test_v3_..._with_the_controlled_adapter``) call it with the controlled
:class:`~manosube_agent_civilization.projection.github_adapter.FakeGitHubAdapter` and are
**not** skipped -- they prove the identical harness logic (real Difference/Change/Evidence
subjects, real Authority Decision grants, real payloads) runs to completion today, for all
three projection kinds, with zero live network access. The three ``RealGitHubAdapter`` tests
call the exact same function; only the adapter and the skip differ.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any
import urllib.request

import pytest
from tests.authority_helpers import action, derived_difference, rule, scope
from tests.change_helpers import route as change_route
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    sign_github_projection_grant_declaration,
)
from tests.fixtures.v3_authority_test_material import (
    genuine_project_binding,
    genuine_v3_authority_store_and_references,
)
from tests.fixtures.v3_live_write_authority import (
    V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV,
    V3AuthorizedExecutionContext,
    load_v3_live_write_authority_references,
    open_v3_live_write_store,
    resolve_v3_live_write_authority,
    v3_execution_context_still_current,
)
from tests.fixtures.v3_target_configuration import (
    ALL_V3_ENV_VARS,
    ARTIFACT_NAMING_PREFIX_ENV,
    AUTHORIZED_ARTIFACT_COUNT_ENV,
    AUTHORIZED_ARTIFACT_KINDS_ENV,
    CHANGE_BASE_REF_ENV,
    CHANGE_HEAD_REF_ENV,
    CLEANUP_CONFIRMED_ENV,
    EVIDENCE_HEAD_SHA_ENV,
    NO_MERGE_CONFIRMED_ENV,
    TARGET_REPOSITORY_ENV,
    TOKEN_ENV,
    V3TargetConfiguration,
    load_v3_target_configuration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import bind_project, declare_github_projection_grant
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.change.identity import (
    change_id as compute_change_id,
    change_semantic_fingerprint,
)
from manosube_agent_civilization.difference.identity import difference_id as compute_difference_id
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import (
    FakeGitHubAdapter,
    RealGitHubAdapter,
    project_to_github,
)
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.projection.types import GitHubAdapter
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

_SKIP_REASON = (
    "V3_EXTERNAL_WRITE_ALLOWED_BY_THIS_COMMENT=false -- ADOPT_P14_D001_PROJECTION_ENVELOPE_"
    "IMPLEMENTATION (Issue #62) authorizes preparing this harness, not executing it against "
    "a live target, until the exact repository/artifact/cleanup/no-merge boundary is "
    "separately frozen and re-confirmed, and load_v3_target_configuration()/"
    "load_v3_live_write_authority_references()/resolve_v3_live_write_authority() are all "
    "re-checked at collection time on every run."
)

#: Which single ``artifact_kind`` :class:`~manosube_agent_civilization.projection.
#: github_adapter.RealGitHubAdapter` actually materializes for each ``projection_kind`` --
#: the identical mapping ``github_adapter.py``'s own ``materialize`` uses. Bound here so the
#: three real-adapter tests below can require their own artifact_kind be a member of the
#: frozen configuration's own ``authorized_artifact_kinds`` (Structural Review Round 4,
#: P14-R4-F3) before ever constructing a ``RealGitHubAdapter`` call.
_PROJECTION_KIND_TO_ARTIFACT_KIND: dict[str, str] = {
    "DIFFERENCE_ISSUE": "issue",
    "CHANGE_PULL_REQUEST": "pull_request",
    "EVIDENCE_ARTIFACT": "check_run",
}


def _require_authorized_artifact_kind(config: V3TargetConfiguration, projection_kind: str) -> None:
    """Refuse to proceed unless *projection_kind*'s own real artifact_kind is a member of
    *config*'s own ``authorized_artifact_kinds`` (Structural Review Round 4, P14-R4-F3) --
    binding the frozen boundary's own artifact-kind authorization into the harness itself,
    never left as a configuration-module-only check nothing downstream re-verifies."""

    artifact_kind = _PROJECTION_KIND_TO_ARTIFACT_KIND[projection_kind]
    if artifact_kind not in config.authorized_artifact_kinds:
        raise AssertionError(
            f"projection_kind {projection_kind!r} requires artifact_kind {artifact_kind!r}, "
            f"which is not among this frozen configuration's own authorized_artifact_kinds: "
            f"{sorted(config.authorized_artifact_kinds)}"
        )


def _v3_authorized() -> bool:
    """Return whether a later, separate authorization has actually configured a bounded,
    fully validated V3 target (Structural Review Round 3, P14-R3-F3) -- always ``False`` in
    this delivery, checked explicitly rather than assumed."""

    return load_v3_target_configuration() is not None


def _v3_live_authorized_context() -> V3AuthorizedExecutionContext | None:
    """Resolve the one authority context the V3 harness's own real-adapter tests are gated on
    (Structural Review Round 4, Issue #62, P14-R4-F3; genuine signed Human Authority, Round 6,
    P14-R6-F2; external trust anchor, Round 7, P14-R7-F1; canonical issuable authority,
    Round 8, P14-R8-F1; Store/Boot-resolved authority routed to execution, Round 9, P14-R9-F1):
    a fail-closed runtime gate requiring a fully validated, fully bound
    :class:`V3TargetConfiguration` and project-scoped V3 live-write authority **references**
    read from the environment
    (:func:`~tests.fixtures.v3_live_write_authority.load_v3_live_write_authority_references`),
    resolved against the real canonical Store those references name and verified through the
    identical canonical Authority/Binding/Boot route
    (:func:`~manosube_agent_civilization.authority.projection_authorization.
    evaluate_projection_authorization`, :func:`~manosube_agent_civilization.boot.boot_project`)
    a real GitHub projection call already uses -- always ``None`` in this delivery. This
    function, not a hardcoded ``pytest.mark.skip``, is what the real-adapter tests below are
    gated on, so a later round that supplies genuine references to a real, committed Store via
    the environment (issued entirely outside this repository, by whoever genuinely holds the
    real Project Binding's Human Authority private key, committed by whatever process SHUKOU
    authorizes) activates them *without any source edit* to this file. The returned context,
    when not ``None``, is the exact object every real-adapter test below must thread unchanged
    into the execution call that reaches the adapter -- never a separately built Store/
    project/refs of its own."""

    config = load_v3_target_configuration()
    references = load_v3_live_write_authority_references()
    store = open_v3_live_write_store(references)
    return resolve_v3_live_write_authority(store, config, references)


def _v3_live_authorized() -> bool:
    """Boolean convenience over :func:`_v3_live_authorized_context`, for the module-level
    ``pytest.mark.skipif`` gate, which cannot itself hold onto a resolved Store/context."""

    return _v3_live_authorized_context() is not None


def _bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


def _commit(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
) -> dict[str, Any]:
    successor = dict(current_state)
    successor["state_revision"] = current_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": current_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": current_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-09-08T00:00:00Z",
    }
    store.commit(
        project_id,
        current_state["state_revision"],
        current_state["semantic_fingerprint"],
        successor,
        event,
        records=records,
    )
    return successor


def _commit_grant(
    store: FileStateStore,
    project_id: str,
    human_authority_ref: dict[str, Any],
    current_state: dict[str, Any],
    transaction_id: str,
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    payload_fingerprint: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(target_repository),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": "MATERIALIZE_PROJECTION",
        "status": "ACTIVE",
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    next_state = _commit(
        store,
        project_id,
        current_state,
        transaction_id,
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    return (
        {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        next_state,
        grant,
    )


def _commit_declaration(
    store: FileStateStore,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: dict[str, Any],
    grant: dict[str, Any],
) -> dict[str, Any]:
    """Declare and commit one real, genuinely Ed25519-signed ``github_projection_grant_
    declaration`` anchoring *grant*, through the real committing route (Structural Review
    Round 2, Issue #62, P14-R2-F1) -- a Store-resolved grant alone, with no matching signed
    Human declaration anchoring it, authorizes zero adapter calls."""

    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    signature = sign_github_projection_grant_declaration(
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        declared_by=human_authority_ref,
        subject_ref=grant["subject_ref"],
        subject_fingerprint=grant["subject_fingerprint"],
        projection_kind=grant["projection_kind"],
        target_repository=grant["target_repository"],
        payload_fingerprint=grant["payload_fingerprint"],
        permitted_action=grant["permitted_action"],
        status="ACTIVE",
        declared_at="2026-09-08T00:00:00Z",
    )
    result = declare_github_projection_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status="ACTIVE",
        declared_at="2026-09-08T00:00:00Z",
        signature=signature,
        schema_root=SCHEMA_ROOT,
    )
    declaration = result["github_projection_grant_declaration"]
    return {
        "kind": "github_projection_grant_declaration",
        "id": declaration["github_projection_grant_declaration_id"],
    }


def _build_v3_subject(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    subject_kind: str,
    *,
    transaction_id: str = "TX-V3-EVIDENCE-0001",
) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, Any]]:
    """Build (and, for ``observation_evidence``, commit) one real canonical subject of
    *subject_kind* -- the identical subject-construction logic every projection-kind proof in
    this file shares, factored out so both :func:`_run_vertical_proof` (its own throwaway
    Store/Binding) and :func:`_run_v3_authorized_vertical_proof` (a genuinely resolved,
    authorized :class:`~tests.fixtures.v3_live_write_authority.V3AuthorizedExecutionContext`'s
    own Store) build the identical subject shape. Returns ``(subject_ref,
    subject_fingerprint, kwargs, current_state)`` -- *current_state* only advances for
    ``observation_evidence``, which must commit its own subject record before it can be
    referenced."""

    kwargs: dict[str, Any] = {}
    if subject_kind == "difference":
        difference = dict(derived_difference())
        difference["project_id"] = project_id
        difference["difference_id"] = compute_difference_id(difference)
        subject_ref = {"kind": "difference", "id": difference["difference_id"]}
        import hashlib

        subject_fingerprint = (
            "sha256:" + hashlib.sha256(difference["difference_id"].encode("utf-8")).hexdigest()
        )
        kwargs["subject_record"] = difference
    elif subject_kind == "change":
        difference = dict(derived_difference())
        difference["project_id"] = project_id
        difference["difference_id"] = compute_difference_id(difference)
        _authority_input, _decision, change_request = change_route(
            difference, action(), scope(), rules=[rule(project_id)]
        )
        change = derive_change(change_request)
        subject_ref = {"kind": "change", "id": compute_change_id(change)}
        subject_fingerprint = change_semantic_fingerprint(change)
        kwargs["subject_record"] = change
    else:
        evidence = derive_evidence(observation_evidence_request())
        current_state = _commit(
            store,
            project_id,
            current_state,
            transaction_id,
            [("observation_evidence", evidence["evidence_id"], evidence)],
        )
        subject_ref = {"kind": "observation_evidence", "id": evidence["evidence_id"]}
        subject_fingerprint = evidence_semantic_fingerprint(evidence)

    return subject_ref, subject_fingerprint, kwargs, current_state


def _run_vertical_proof(
    tmp_path: Path,
    *,
    subject_kind: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    projection_payload: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Project one real canonical subject of *subject_kind* to GitHub via *adapter* and
    return the outcome -- the one shared body every projection-kind test below calls
    (Structural Review Round 1, P14-R1-F5). Builds a real, genuinely-committed
    ``github_projection_grant`` so the call reaches the adapter at all."""

    store, ctx = _bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    human_authority_ref = dict(boot_context.human_authority_ref)
    current_state = ctx["genesis_state"]

    subject_ref, subject_fingerprint, kwargs, current_state = _build_v3_subject(
        store, ctx["project_id"], current_state, subject_kind
    )

    grant_ref, current_state, grant = _commit_grant(
        store,
        ctx["project_id"],
        human_authority_ref,
        current_state,
        "TX-V3-GRANT-0001",
        subject_ref=subject_ref,
        subject_fingerprint=subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=target_repository,
        payload_fingerprint=projection_payload_fingerprint(dict(projection_payload)),
    )
    # Structural Review Round 2 (P14-R2-F1): the grant's own Store persistence is never itself
    # proof a Human declared it -- a real, genuinely signed declaration anchors it too.
    declaration_ref = _commit_declaration(
        store, ctx["project_id"], ctx["project_binding_id"], human_authority_ref, grant
    )

    return project_to_github(
        store,
        project_id=ctx["project_id"],
        project_binding_id=ctx["project_binding_id"],
        subject_ref=subject_ref,
        projection_kind=projection_kind,
        target_repository=target_repository,
        projection_payload=projection_payload,
        github_authority_ref=human_authority_ref,
        materialized_at="2026-09-08T00:00:01Z",
        adapter=adapter,
        github_projection_grant_refs=[grant_ref],
        github_projection_grant_declaration_refs=[declaration_ref],
        attempt_claim_token=f"PROJECTION-ATTEMPT-V3-{projection_kind.replace('_', '-')}",
        **kwargs,
    )


def _run_v3_authorized_vertical_proof(
    context: V3AuthorizedExecutionContext,
    *,
    subject_kind: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    projection_payload: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """The identical projection call :func:`_run_vertical_proof` makes -- but its Store,
    project, Project Binding, and Human Authority reference are sourced entirely from
    *context*, the one already-resolved, already-authorized
    :class:`~tests.fixtures.v3_live_write_authority.V3AuthorizedExecutionContext`
    :func:`~tests.fixtures.v3_live_write_authority.resolve_v3_live_write_authority` returned
    (Structural Review Round 9, P14-R9-F1) -- never a separately built, unrelated throwaway
    Store/Binding of this function's own the way Round 8's own ``_run_v3_authorized_execution``
    still did. *context*'s own ``github_projection_grant_refs``/``github_projection_grant_
    declaration_refs`` are bound to the V3-configuration subject (the meta-authorization
    proving a live V3 run against this exact configuration/target/boundary is SHUKOU-
    authorized at all, verified once by :func:`~tests.fixtures.v3_live_write_authority.
    resolve_v3_live_write_authority` before this function is ever called) -- never to *this*
    call's own Difference/Change/Evidence subject, so this function mints a fresh,
    subject-scoped grant/declaration into *context.store*, the identical production-shaped
    per-subject authorization :func:`~manosube_agent_civilization.projection.route.
    project_to_github` always independently requires of every caller, V3 or not. The subject
    itself (a fresh Difference/Change/Evidence, the project-scoped input this finding
    explicitly permits a caller to carry) is likewise built fresh, but committed into
    *context.store* -- the same real, already-Boot-verified Store the meta-authorization
    itself resolved, never a disconnected one."""

    store = context.store
    project_id = context.project_id
    human_authority_ref = dict(context.github_authority_ref)
    current_state = dict(store.load_current(project_id))
    projection_kind_token = projection_kind.replace("_", "-")

    subject_ref, subject_fingerprint, kwargs, current_state = _build_v3_subject(
        store,
        project_id,
        current_state,
        subject_kind,
        transaction_id=f"TX-V3-AUTHORIZED-EVIDENCE-{projection_kind_token}",
    )

    grant_ref, current_state, grant = _commit_grant(
        store,
        project_id,
        human_authority_ref,
        current_state,
        f"TX-V3-AUTHORIZED-GRANT-{projection_kind_token}",
        subject_ref=subject_ref,
        subject_fingerprint=subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=target_repository,
        payload_fingerprint=projection_payload_fingerprint(dict(projection_payload)),
    )
    declaration_ref = _commit_declaration(
        store, project_id, context.project_binding_id, human_authority_ref, grant
    )

    return project_to_github(
        store,
        project_id=project_id,
        project_binding_id=context.project_binding_id,
        subject_ref=subject_ref,
        projection_kind=projection_kind,
        target_repository=target_repository,
        projection_payload=projection_payload,
        github_authority_ref=human_authority_ref,
        materialized_at="2026-09-08T00:00:01Z",
        adapter=adapter,
        github_projection_grant_refs=[grant_ref],
        github_projection_grant_declaration_refs=[declaration_ref],
        attempt_claim_token=f"PROJECTION-ATTEMPT-V3-AUTHORIZED-{projection_kind.replace('_', '-')}",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Structural Review Round 5 (Issue #62, P14-R5-F2): whole-run artifact-count enforcement and
# the cleanup terminal -- a shared budget across the *complete* three-projection V3 run, and a
# harness-owned (test-only) close/cancel of every artifact this run actually materialized.
# ---------------------------------------------------------------------------


class V3ArtifactBudgetExceededError(RuntimeError):
    """Raised by :class:`_BudgetEnforcingAdapter` when a further ``materialize`` call would
    exceed the frozen configuration's own ``authorized_artifact_count`` -- enforced as one
    shared budget across the *whole* three-projection run, never per projection kind
    independently. Storing ``authorized_artifact_count`` on the configuration alone (Round 4's
    own state) proved nothing about what a run actually materializes; this is what makes the
    count a real, mechanically enforced ceiling rather than a declared-but-unchecked value."""


class _BudgetEnforcingAdapter:
    """Wrap *adapter*, refusing a further ``materialize`` call once *counter* (a shared,
    mutable single-element list threaded across every projection kind in one run) has already
    reached *budget*. Every other call (``observe``, ``find_by_correlation_key``,
    ``adapter_identity``) passes straight through unchanged -- this wrapper exists only to
    enforce the one authorized count, never to reinterpret materialization/observation
    semantics :class:`~manosube_agent_civilization.projection.types.GitHubAdapter` already
    owns.

    Structural Review Round 6 (Issue #62, P14-R6-F1): *on_materialized* is called with the
    real ``external_artifact_ref`` the instant ``adapter.materialize`` itself returns
    successfully -- at the external-write boundary itself, before ``materialize`` even
    returns to ``project_to_github``'s own caller, and therefore before observation, receipt
    construction, the Envelope's own Store commit, or any later route step has any chance to
    fail. Round 5's own cleanup tracking only recorded an artifact once the *entire*
    ``project_to_github`` call returned a success outcome -- so a real external creation
    followed by any later failure in that same call left nothing registered for cleanup at
    all, a genuine leak this callback closes."""

    def __init__(
        self,
        adapter: GitHubAdapter,
        budget: int,
        counter: list[int],
        on_materialized: Callable[[Mapping[str, Any]], None],
    ) -> None:
        self._adapter = adapter
        self._budget = budget
        self._counter = counter
        self._on_materialized = on_materialized

    @property
    def adapter_identity(self) -> Mapping[str, Any]:
        return self._adapter.adapter_identity

    def materialize(self, **kwargs: Any) -> Mapping[str, Any]:
        if self._counter[0] >= self._budget:
            raise V3ArtifactBudgetExceededError(
                f"this V3 run already materialized {self._counter[0]} artifact(s), the exact "
                f"authorized_artifact_count ({self._budget}) -- refusing a further "
                "materialize call rather than silently exceeding the frozen boundary"
            )
        result = self._adapter.materialize(**kwargs)
        self._counter[0] += 1
        # The external artifact now genuinely exists -- register it for cleanup before this
        # method even returns, so nothing downstream (observe, Envelope commit, or any other
        # later route step) can fail without this artifact still being tracked.
        self._on_materialized(result)
        return result

    def find_by_correlation_key(self, **kwargs: Any) -> Mapping[str, Any] | None:
        return self._adapter.find_by_correlation_key(**kwargs)

    def observe(self, **kwargs: Any) -> Mapping[str, Any]:
        return self._adapter.observe(**kwargs)


@dataclass(frozen=True, slots=True)
class V3ArtifactCleanupOutcome:
    """The cleanup result for exactly one artifact this run actually materialized -- never
    fabricated for an artifact the run never reached."""

    projection_kind: str
    artifact_kind: str
    external_artifact_ref: Mapping[str, Any]
    closed: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class V3CleanupReceipt:
    """The cleanup terminal for one complete, or partially completed, V3 authorized run
    (Structural Review Round 5, Issue #62, P14-R5-F2): one :class:`V3ArtifactCleanupOutcome`
    per artifact this run actually materialized, never more and never fewer -- a run that
    fails partway (a budget refusal, an adapter error) still produces a receipt covering
    exactly what it did materialize before failing, not a claim of full-run completion."""

    outcomes: tuple[V3ArtifactCleanupOutcome, ...]

    @property
    def all_closed(self) -> bool:
        return all(outcome.closed for outcome in self.outcomes)


class V3CleanupNotConfirmedError(RuntimeError):
    """Raised by :func:`_close_artifact` when the PATCH call itself completed without a
    transport error, but the response's own returned state does not actually reflect closure
    (Structural Review Round 6, Issue #62, P14-R6-F1) -- a non-error HTTP response alone is
    never itself proof of a confirmed terminal state; a tampered, stale, or wrong-shaped
    response body is treated identically to an unavailable transport, never as success."""


def _close_artifact(
    *,
    token: str,
    owner: str,
    repo: str,
    artifact_kind: str,
    external_artifact_ref: Mapping[str, Any],
) -> None:
    """Close/cancel one materialized artifact via one direct, harness-owned PATCH call --
    deliberately never through :class:`~manosube_agent_civilization.projection.github_adapter.
    GitHubAdapter` (whose Protocol has, and must never gain, a close/delete capability: the
    identical "must never merge a Pull Request" boundary this package's own
    ``RealGitHubAdapter`` already enforces for its own ``materialize``/``observe`` methods
    extends to never closing or deleting on the adapter's own behalf either). This is test-only
    transport, exactly as ``RealGitHubAdapter``'s own module already reserves the transport
    surface to itself in production code -- this function exists only in this test harness.

    Structural Review Round 6 (P14-R6-F1): a cleanup result may only be called successful
    after the *returned* GitHub state is actually validated -- this function now parses the
    PATCH response body and requires it to genuinely reflect the closed/cancelled terminal
    state, raising :class:`V3CleanupNotConfirmedError` otherwise. A non-error HTTP status by
    itself (e.g. a stale cache, a tampered or wrong-shaped body) is never treated as
    confirmation."""

    external_id = external_artifact_ref["external_id"]
    if artifact_kind == "issue":
        path = f"/repos/{owner}/{repo}/issues/{external_id}"
        payload: dict[str, Any] = {"state": "closed"}
    elif artifact_kind == "pull_request":
        path = f"/repos/{owner}/{repo}/pulls/{external_id}"
        payload = {"state": "closed"}
    elif artifact_kind == "check_run":
        path = f"/repos/{owner}/{repo}/check-runs/{external_id}"
        payload = {"status": "completed", "conclusion": "cancelled"}
    else:
        raise AssertionError(f"cleanup is not modeled for artifact_kind {artifact_kind!r}")

    request = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))

    if artifact_kind in ("issue", "pull_request"):
        confirmed = isinstance(body, dict) and body.get("state") == "closed"
    else:
        confirmed = (
            isinstance(body, dict)
            and body.get("status") == "completed"
            and body.get("conclusion") == "cancelled"
        )
    if not confirmed:
        raise V3CleanupNotConfirmedError(
            f"PATCH to close/cancel {artifact_kind} {external_id!r} returned without a "
            f"transport error, but its own returned state does not confirm closure: {body!r}"
        )


#: The three projection kinds a complete, authorized V3 run covers, and the fixed
#: subject/payload shape each one needs -- shared by both the live-gated and the offline
#: transport-fixture executions below, so the two can never silently diverge.
_V3_RUN_PROJECTIONS: tuple[tuple[str, str], ...] = (
    ("DIFFERENCE_ISSUE", "difference"),
    ("CHANGE_PULL_REQUEST", "change"),
    ("EVIDENCE_ARTIFACT", "observation_evidence"),
)


def _v3_run_payload(config: V3TargetConfiguration, projection_kind: str) -> dict[str, Any]:
    if projection_kind == "DIFFERENCE_ISSUE":
        return {"title": f"{config.artifact_naming_prefix} -- Difference", "body": "harness"}
    if projection_kind == "CHANGE_PULL_REQUEST":
        return {
            "title": f"{config.artifact_naming_prefix} -- Change",
            "body": "harness",
            "head_ref": config.change_head_ref,
            "base_ref": config.change_base_ref,
        }
    return {
        "name": config.artifact_naming_prefix,
        "head_sha": config.evidence_head_sha,
        "status": "completed",
        "conclusion": "neutral",
        "output": {"title": config.artifact_naming_prefix, "summary": "harness"},
    }


def _run_v3_authorized_execution(
    tmp_path: Path,
    config: V3TargetConfiguration,
    adapter_factory: Callable[[str], GitHubAdapter],
    *,
    cleanup_receipt_sink: list[V3CleanupReceipt] | None = None,
    context: V3AuthorizedExecutionContext | None = None,
) -> dict[str, Any]:
    """Run the complete, three-projection V3 execution as ONE cohesive run (Structural Review
    Round 5, Issue #62, P14-R5-F2), sharing a single artifact budget enforced against
    *config*'s own ``authorized_artifact_count`` across all three projection kinds together --
    never three independently budget-blind pytest tests each capable of materializing
    regardless of what the other two already spent. Unconditionally attempts cleanup, in a
    ``finally``, of every artifact this run actually materialized before returning or
    propagating -- the required partial-run/failure handling, so a mid-run refusal never
    leaves an already-materialized artifact uncleaned. Never merges a Pull Request or any
    other artifact -- no method this function or :class:`_BudgetEnforcingAdapter` calls is
    capable of one.

    *adapter_factory* is called once per projection kind, with that kind's own name, so a
    caller may inject a kind-specific failing adapter (Structural Review Round 6, P14-R6-F1)
    to prove cleanup still covers an artifact whose own later route step -- observation,
    Envelope commit, or anything after materialize -- fails. *cleanup_receipt_sink*, when
    supplied, receives the :class:`V3CleanupReceipt` even when this function itself raises --
    the ``finally`` block always appends to it before the original exception propagates, so a
    caller proving a failed run's own cleanup outcome does not need this function to return
    normally to inspect it.

    *context*, when supplied (Structural Review Round 9, P14-R9-F1), is the one already-
    resolved, already-authorized :class:`~tests.fixtures.v3_live_write_authority.
    V3AuthorizedExecutionContext` this run threads unchanged into
    :func:`_run_v3_authorized_vertical_proof` for every projection kind, instead of each kind
    building its own disconnected throwaway Store/Binding via :func:`_run_vertical_proof` --
    never a detached authorization check followed by execution against an unrelated Store.
    This function fails closed, before materializing anything, if *context* is no longer
    current (:func:`~tests.fixtures.v3_live_write_authority.
    v3_execution_context_still_current`) -- a Store mutation between authorization and this
    call must refuse the whole run rather than execute against a possibly-stale context. Left
    ``None`` (the default), every projection kind instead binds its own fresh, disconnected
    Project via :func:`_run_vertical_proof`, exactly as this function has always done for the
    offline budget/cleanup/failure-injection proofs that have nothing to do with V3 live-write
    authority at all."""

    if context is not None and not v3_execution_context_still_current(context):
        raise AssertionError(
            "V3 live-write authority context no longer reflects the current Store state -- "
            "refusing the entire authorized run before materializing anything"
        )

    counter = [0]
    materialized: list[tuple[str, str, dict[str, Any]]] = []
    outcomes: list[dict[str, Any]] = []
    try:
        for projection_kind, subject_kind in _V3_RUN_PROJECTIONS:
            _require_authorized_artifact_kind(config, projection_kind)
            artifact_kind = _PROJECTION_KIND_TO_ARTIFACT_KIND[projection_kind]

            def _register(
                ref: Mapping[str, Any],
                *,
                _projection_kind: str = projection_kind,
                _artifact_kind: str = artifact_kind,
            ) -> None:
                materialized.append((_projection_kind, _artifact_kind, dict(ref)))

            adapter = _BudgetEnforcingAdapter(
                adapter_factory(projection_kind),
                config.authorized_artifact_count,
                counter,
                on_materialized=_register,
            )
            if context is not None:
                outcome = _run_v3_authorized_vertical_proof(
                    context,
                    subject_kind=subject_kind,
                    projection_kind=projection_kind,
                    target_repository=config.target_repository,
                    projection_payload=_v3_run_payload(config, projection_kind),
                    adapter=adapter,
                )
            else:
                # Each projection kind binds its own genesis Project State under a distinct
                # sub-path -- ``_bound``'s own fixed ``PROJECT_ID`` would otherwise collide
                # the second time this loop calls it against the identical *tmp_path*.
                outcome = _run_vertical_proof(
                    tmp_path / projection_kind,
                    subject_kind=subject_kind,
                    projection_kind=projection_kind,
                    target_repository=config.target_repository,
                    projection_payload=_v3_run_payload(config, projection_kind),
                    adapter=adapter,
                )
            assert outcome["receipt"].status == "VERIFIED"
            outcomes.append(outcome)
    finally:
        cleanup_outcomes: list[V3ArtifactCleanupOutcome] = []
        for projection_kind, artifact_kind, external_artifact_ref in materialized:
            try:
                _close_artifact(
                    token=config.token,
                    owner=config.owner,
                    repo=config.repo,
                    artifact_kind=artifact_kind,
                    external_artifact_ref=external_artifact_ref,
                )
                cleanup_outcomes.append(
                    V3ArtifactCleanupOutcome(
                        projection_kind, artifact_kind, external_artifact_ref, closed=True
                    )
                )
            except Exception as exc:
                cleanup_outcomes.append(
                    V3ArtifactCleanupOutcome(
                        projection_kind,
                        artifact_kind,
                        external_artifact_ref,
                        closed=False,
                        error=str(exc),
                    )
                )
        cleanup_receipt = V3CleanupReceipt(tuple(cleanup_outcomes))
        if cleanup_receipt_sink is not None:
            cleanup_receipt_sink.append(cleanup_receipt)

    return {
        "outcomes": outcomes,
        "materialized_count": counter[0],
        "cleanup_receipt": cleanup_receipt,
    }


def test_v3_authorization_is_not_yet_configured_in_this_environment() -> None:
    """The one assertion this file makes without being skipped for the *live* target: proves
    the gate itself is real, not merely a comment -- this delivery's own environment
    genuinely has no fully validated V3 target configured and no live-write authority granted
    (Structural Review Round 4, P14-R4-F3: the two are independently checked), so the
    ``RealGitHubAdapter`` tests below genuinely cannot run live here even if their
    ``skipif`` markers were somehow bypassed by mistake."""

    assert _v3_authorized() is False
    assert load_v3_target_configuration() is None
    assert load_v3_live_write_authority_references() is None
    assert resolve_v3_live_write_authority(None, None, None) is None
    assert _v3_live_authorized() is False
    assert _v3_live_authorized_context() is None


def test_unauthorized_or_mismatched_human_authority_causes_zero_network_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Structural Review Round 6 (Issue #62, P14-R6-F2), reused verbatim by Round 8
    (P14-R8-F1) and Round 9 (P14-R9-F1): a fully valid, fully bound
    :class:`V3TargetConfiguration` *plus* genuinely-issued, genuinely Store-committed, but
    mismatched (wrong configuration) V3 live-write authority references must still refuse --
    and, since ``_v3_live_authorized()`` is what every real-adapter test's own ``pytest.mark.
    skipif`` gates on, that refusal happens entirely offline, before any adapter is ever
    constructed and therefore before ``urllib.request.urlopen`` could ever be called even
    once."""

    valid_env = {
        TARGET_REPOSITORY_ENV: "acme/widget",
        TOKEN_ENV: "test-token-not-a-real-secret",
        CHANGE_HEAD_REF_ENV: "agent/frozen-v3-branch",
        CHANGE_BASE_REF_ENV: "main",
        EVIDENCE_HEAD_SHA_ENV: "0123456789abcdef0123456789abcdef01234567",
        ARTIFACT_NAMING_PREFIX_ENV: "MANOSUBE V3 proof (do not merge)",
        CLEANUP_CONFIRMED_ENV: "true",
        NO_MERGE_CONFIRMED_ENV: "true",
        AUTHORIZED_ARTIFACT_KINDS_ENV: "issue,pull_request,check_run",
        AUTHORIZED_ARTIFACT_COUNT_ENV: "3",
    }
    assert set(valid_env) == set(ALL_V3_ENV_VARS)
    for key, value in valid_env.items():
        monkeypatch.setenv(key, value)

    config = load_v3_target_configuration()
    assert config is not None

    # A genuinely issued (real Store-committed project_binding, real signed grant/declaration
    # pair per projection kind) set of references -- but built for a *different* configuration
    # (a different repository), so the resolved grants' own subject_fingerprint/
    # target_repository never match this environment's real config. Real cryptographic
    # material, genuinely committed to a real Store, still refused (Structural Review Round 9,
    # P14-R9-F1).
    wrong_config = replace(config, repo="a-different-widget")
    _store, mismatched_references = genuine_v3_authority_store_and_references(
        tmp_path, wrong_config
    )
    payload = {
        "store_root": mismatched_references.store_root,
        "project_id": mismatched_references.project_id,
        "project_binding_id": mismatched_references.project_binding_id,
        "github_projection_grant_refs": list(mismatched_references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            mismatched_references.github_projection_grant_declaration_refs
        ),
    }
    monkeypatch.setenv(V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV, json.dumps(payload))

    def _forbidden_urlopen(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "urllib.request.urlopen was called despite unauthorized/mismatched V3 live-write "
            "authority -- this must never happen"
        )

    monkeypatch.setattr(urllib.request, "urlopen", _forbidden_urlopen)

    assert _v3_authorized() is True
    assert load_v3_live_write_authority_references() == mismatched_references
    assert _v3_live_authorized() is False
    assert _v3_live_authorized_context() is None


def test_never_committed_fabricated_material_causes_zero_network_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Structural Review Round 9's own required control: a fully self-consistent,
    correctly-signed Project Binding and grant/declaration -- built entirely offline via
    :func:`~tests.fixtures.v3_authority_test_material.genuine_project_binding` and never
    committed to the real, genuinely-bound Store this environment's own references name --
    must cause zero network calls. ``store.resolve_record`` returns ``None`` for a reference
    nothing ever committed, refused before ``evaluate_projection_authorization`` is ever
    reached and therefore before any adapter could ever be constructed."""

    valid_env = {
        TARGET_REPOSITORY_ENV: "acme/widget",
        TOKEN_ENV: "test-token-not-a-real-secret",
        CHANGE_HEAD_REF_ENV: "agent/frozen-v3-branch",
        CHANGE_BASE_REF_ENV: "main",
        EVIDENCE_HEAD_SHA_ENV: "0123456789abcdef0123456789abcdef01234567",
        ARTIFACT_NAMING_PREFIX_ENV: "MANOSUBE V3 proof (do not merge)",
        CLEANUP_CONFIRMED_ENV: "true",
        NO_MERGE_CONFIRMED_ENV: "true",
        AUTHORIZED_ARTIFACT_KINDS_ENV: "issue,pull_request,check_run",
        AUTHORIZED_ARTIFACT_COUNT_ENV: "3",
    }
    for key, value in valid_env.items():
        monkeypatch.setenv(key, value)
    config = load_v3_target_configuration()
    assert config is not None

    # A real, genuinely bound and committed Store -- but the grant/declaration references
    # this environment names point at a fabricated Project Binding's own never-committed
    # ids, never anything this real Store actually contains.
    _store, real_references = genuine_v3_authority_store_and_references(tmp_path, config)
    fabricated_binding = genuine_project_binding()
    fabricated_payload = {
        "store_root": real_references.store_root,
        "project_id": real_references.project_id,
        "project_binding_id": real_references.project_binding_id,
        "github_projection_grant_refs": [
            {
                "kind": "github_projection_grant",
                "id": f"GH-PROJ-GRANT-NEVER-COMMITTED-{fabricated_binding['project_binding_id']}",
            }
        ],
        "github_projection_grant_declaration_refs": [
            {
                "kind": "github_projection_grant_declaration",
                "id": (
                    f"GH-PROJ-GRANT-DECL-NEVER-COMMITTED-{fabricated_binding['project_binding_id']}"
                ),
            }
        ],
    }
    monkeypatch.setenv(V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV, json.dumps(fabricated_payload))

    def _forbidden_urlopen(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "urllib.request.urlopen was called despite unresolved, never-committed V3 "
            "live-write authority references -- this must never happen"
        )

    monkeypatch.setattr(urllib.request, "urlopen", _forbidden_urlopen)

    assert _v3_live_authorized() is False
    assert _v3_live_authorized_context() is None
    # The real Store, for its part, genuinely does authorize its own real references --
    # proving the refusal above is specific to the fabricated, never-committed ids, not to
    # this Store/configuration pairing being unauthorizable in general.
    real_store = open_v3_live_write_store(real_references)
    assert real_store is not None
    assert resolve_v3_live_write_authority(real_store, config, real_references) is not None


# ---------------------------------------------------------------------------
# Structural Review Round 4 (P14-R4-F3): the harness's own artifact-kind binding, exercised
# directly and entirely offline -- no Store, no adapter, no network.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("projection_kind", "excluded_kind"),
    [
        ("DIFFERENCE_ISSUE", "issue"),
        ("CHANGE_PULL_REQUEST", "pull_request"),
        ("EVIDENCE_ARTIFACT", "check_run"),
    ],
)
def test_require_authorized_artifact_kind_refuses_an_unauthorized_kind(
    projection_kind: str, excluded_kind: str
) -> None:
    narrow_config = V3TargetConfiguration(
        owner=_MOCK_CONFIG.owner,
        repo=_MOCK_CONFIG.repo,
        token=_MOCK_CONFIG.token,
        change_head_ref=_MOCK_CONFIG.change_head_ref,
        change_base_ref=_MOCK_CONFIG.change_base_ref,
        evidence_head_sha=_MOCK_CONFIG.evidence_head_sha,
        artifact_naming_prefix=_MOCK_CONFIG.artifact_naming_prefix,
        cleanup_confirmed=True,
        no_merge_confirmed=True,
        authorized_artifact_kinds=frozenset(
            {"issue", "pull_request", "check_run"} - {excluded_kind}
        ),
        authorized_artifact_count=_MOCK_CONFIG.authorized_artifact_count,
    )
    with pytest.raises(AssertionError):
        _require_authorized_artifact_kind(narrow_config, projection_kind)


def test_require_authorized_artifact_kind_accepts_the_authorized_kind() -> None:
    for projection_kind in ("DIFFERENCE_ISSUE", "CHANGE_PULL_REQUEST", "EVIDENCE_ARTIFACT"):
        _require_authorized_artifact_kind(_MOCK_CONFIG, projection_kind)


# ---------------------------------------------------------------------------
# Structural Review Round 1 (P14-R1-F5): the harness itself, proven executable today via the
# controlled adapter -- for all three projection kinds, never skipped.
# ---------------------------------------------------------------------------


def test_v3_harness_projects_a_real_difference_to_an_issue_with_the_controlled_adapter(
    tmp_path: Path,
) -> None:
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="difference",
        projection_kind="DIFFERENCE_ISSUE",
        target_repository={"host": "github", "owner": "acme", "repo": "widget"},
        projection_payload={"title": "V3 harness (Difference)", "body": "harness"},
        adapter=FakeGitHubAdapter(),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_harness_projects_a_real_change_to_a_pull_request_with_the_controlled_adapter(
    tmp_path: Path,
) -> None:
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="change",
        projection_kind="CHANGE_PULL_REQUEST",
        target_repository={"host": "github", "owner": "acme", "repo": "widget"},
        projection_payload={
            "title": "V3 harness (Change)",
            "body": "harness",
            "head_ref": "agent/v3-harness",
            "base_ref": "main",
        },
        adapter=FakeGitHubAdapter(),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_harness_projects_a_real_evidence_item_to_an_artifact_with_the_controlled_adapter(
    tmp_path: Path,
) -> None:
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="observation_evidence",
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository={"host": "github", "owner": "acme", "repo": "widget"},
        projection_payload={
            "name": "V3 harness (Evidence)",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": "V3 harness", "summary": "harness"},
        },
        adapter=FakeGitHubAdapter(),
    )
    assert outcome["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# The identical harness, over the real adapter -- gated on live V3 authorization.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _v3_live_authorized(), reason=_SKIP_REASON)
def test_v3_authorized_full_three_projection_run_against_the_live_target(tmp_path: Path) -> None:
    """Would run the complete, authorized V3 execution against the live target: all three of
    Issue #62's own V3 requirements (Difference to Issue, Change to Pull Request, Evidence to
    check-run) as ONE cohesive run sharing a single artifact budget, followed by a cleanup
    terminal closing every artifact this run actually materialized (Structural Review Round 5,
    Issue #62, P14-R5-F2). See the module-level controlled-adapter tests above, and the offline
    transport-fixture test below, for proof this exact harness body is mechanically complete
    and runs today; only the live network calls (``RealGitHubAdapter``) are gated.

    Structural Review Round 4 (P14-R4-F3) previously ran this as three separate tests, each
    only able to see its own materialize call -- never the other two's -- so nothing enforced
    that the *whole* run stayed within ``authorized_artifact_count``. Collapsing them into one
    shared-budget execution (Round 5) is what makes the count a real, run-wide ceiling."""

    config = load_v3_target_configuration()
    assert config is not None
    context = _v3_live_authorized_context()
    assert context is not None
    result = _run_v3_authorized_execution(
        tmp_path,
        config,
        lambda projection_kind: RealGitHubAdapter(token=config.token),
        context=context,
    )
    assert result["materialized_count"] == config.authorized_artifact_count
    assert result["cleanup_receipt"].all_closed


# ---------------------------------------------------------------------------
# Structural Review Round 3 (P14-R3-F3): transport fixtures proving all three
# *configured* real-adapter routes are mechanically executable -- the identical
# ``_run_vertical_proof`` harness body, over a real ``RealGitHubAdapter``, driven by a
# synthetic but fully validated ``V3TargetConfiguration``, with ``urllib.request.urlopen``
# monkeypatched to canned GitHub-shaped responses. No live network access occurs -- none of
# these three tests carry ``pytest.mark.skip``.
# ---------------------------------------------------------------------------

_MOCK_CONFIG = V3TargetConfiguration(
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


# ---------------------------------------------------------------------------
# Structural Review Round 8 (P14-R8-F1)'s own required positive control, updated for Round 9
# (P14-R9-F1): a genuinely issued, genuinely Store-committed V3 live-write authority --
# resolved through the identical canonical Authority/Binding/Boot route the live gate itself
# consumes -- reaches the controlled adapter boundary for every projection kind, entirely
# offline, with zero network calls of any kind. Deliberately drives
# ``_run_v3_authorized_vertical_proof`` directly (never ``_run_v3_authorized_execution``,
# whose own cleanup step always issues a real PATCH regardless of which adapter materialized
# the artifact, which would defeat the "zero network calls" proof this positive control
# specifically makes) -- but now threads the *same* resolved
# :class:`~tests.fixtures.v3_live_write_authority.V3AuthorizedExecutionContext` the live gate
# itself would produce, rather than a detached ``_run_vertical_proof`` call against an
# unrelated throwaway Store.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("subject_kind", "projection_kind", "projection_payload"),
    [
        (
            "difference",
            "DIFFERENCE_ISSUE",
            {"title": "V3 authorized proof (Difference)", "body": "harness"},
        ),
        (
            "change",
            "CHANGE_PULL_REQUEST",
            {
                "title": "V3 authorized proof (Change)",
                "body": "harness",
                "head_ref": "agent/v3-harness",
                "base_ref": "main",
            },
        ),
        (
            "observation_evidence",
            "EVIDENCE_ARTIFACT",
            {
                "name": "V3 authorized proof (Evidence)",
                "head_sha": "a" * 40,
                "status": "completed",
                "conclusion": "neutral",
                "output": {"title": "V3 authorized proof", "summary": "harness"},
            },
        ),
    ],
)
def test_authorized_material_reaches_the_controlled_adapter_boundary_with_zero_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    subject_kind: str,
    projection_kind: str,
    projection_payload: dict[str, Any],
) -> None:
    store, references = genuine_v3_authority_store_and_references(tmp_path, _MOCK_CONFIG)
    context = resolve_v3_live_write_authority(store, _MOCK_CONFIG, references)
    assert context is not None
    assert v3_execution_context_still_current(context) is True

    def _forbidden_urlopen(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "urllib.request.urlopen was called during a controlled-adapter run -- this must "
            "never happen"
        )

    monkeypatch.setattr(urllib.request, "urlopen", _forbidden_urlopen)

    outcome = _run_v3_authorized_vertical_proof(
        context,
        subject_kind=subject_kind,
        projection_kind=projection_kind,
        target_repository={
            "host": "github",
            "owner": _MOCK_CONFIG.owner,
            "repo": _MOCK_CONFIG.repo,
        },
        projection_payload=projection_payload,
        adapter=FakeGitHubAdapter(),
    )
    assert outcome["receipt"].status == "VERIFIED"


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def _install_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[str, str, dict[str, Any] | None], Any]
) -> None:
    """Route every ``urlopen`` call ``RealGitHubAdapter`` makes through *handler* -- the
    identical monkeypatching pattern ``test_real_github_adapter_transport.py`` already
    establishes, duplicated here (never imported) per this package's own per-file fixture
    convention, since this file's own purpose (proving the full harness end to end) is
    genuinely distinct from that file's own (proving the adapter alone)."""

    def fake_urlopen(request: urllib.request.Request, timeout: int = 30) -> _FakeResponse:
        method = request.get_method()
        path = request.full_url[len("https://api.github.com") :]
        raw_data = request.data
        body = json.loads(raw_data.decode("utf-8")) if isinstance(raw_data, bytes) else None
        return _FakeResponse(handler(method, path, body))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def test_v3_configured_real_adapter_projects_a_difference_to_an_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/issues":
            assert body is not None
            return {
                "number": 501,
                "html_url": f"https://github.com/{owner}/{repo}/issue/501",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/issues/501":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Difference",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "updated_at": "2026-09-08T00:00:02Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="difference",
        projection_kind="DIFFERENCE_ISSUE",
        target_repository=_MOCK_CONFIG.target_repository,
        projection_payload={
            "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Difference",
            "body": "harness",
        },
        adapter=RealGitHubAdapter(token=_MOCK_CONFIG.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_configured_real_adapter_projects_a_change_to_a_pull_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/pulls":
            assert body is not None
            return {
                "number": 502,
                "html_url": f"https://github.com/{owner}/{repo}/pull_request/502",
                "title": body["title"],
                "body": body["body"],
                "head": {"ref": body["head"]},
                "base": {"ref": body["base"]},
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/pulls/502":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Change",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "head": {"ref": _MOCK_CONFIG.change_head_ref},
                "base": {"ref": _MOCK_CONFIG.change_base_ref},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="change",
        projection_kind="CHANGE_PULL_REQUEST",
        target_repository=_MOCK_CONFIG.target_repository,
        projection_payload={
            "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Change",
            "body": "harness",
            "head_ref": _MOCK_CONFIG.change_head_ref,
            "base_ref": _MOCK_CONFIG.change_base_ref,
        },
        adapter=RealGitHubAdapter(token=_MOCK_CONFIG.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


def test_v3_configured_real_adapter_projects_an_evidence_item_to_a_check_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo
    head_sha = _MOCK_CONFIG.evidence_head_sha

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path == f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs":
            return {"check_runs": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/check-runs":
            assert body is not None
            return {
                "id": 503,
                "html_url": f"https://github.com/{owner}/{repo}/check_run/503",
                "name": body["name"],
                "head_sha": body["head_sha"],
                "status": body["status"],
                "conclusion": body["conclusion"],
                "output": body["output"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/check-runs/503":
            return {
                "name": _MOCK_CONFIG.artifact_naming_prefix,
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": "neutral",
                "output": {"title": _MOCK_CONFIG.artifact_naming_prefix, "summary": "harness"},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    outcome = _run_vertical_proof(
        tmp_path,
        subject_kind="observation_evidence",
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_MOCK_CONFIG.target_repository,
        projection_payload={
            "name": _MOCK_CONFIG.artifact_naming_prefix,
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": "neutral",
            "output": {"title": _MOCK_CONFIG.artifact_naming_prefix, "summary": "harness"},
        },
        adapter=RealGitHubAdapter(token=_MOCK_CONFIG.token),
    )
    assert outcome["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# Structural Review Round 5 (Issue #62, P14-R5-F2)'s own required offline transport fixture:
# the complete, authorized three-projection run, sharing one enforced budget and ending in a
# cleanup terminal -- proving the exact artifact count, no merge call, and cleanup completion,
# entirely offline (the identical monkeypatched-transport discipline the three tests above
# already establish, driven here through ``_run_v3_authorized_execution`` instead of three
# separate calls to ``_run_vertical_proof``).
# ---------------------------------------------------------------------------


def test_v3_authorized_full_three_projection_run_enforces_the_authorized_artifact_count_and_completes_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo
    head_sha = _MOCK_CONFIG.evidence_head_sha
    calls: list[tuple[str, str]] = []

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        calls.append((method, path))
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/issues":
            assert body is not None
            return {
                "number": 601,
                "html_url": f"https://github.com/{owner}/{repo}/issue/601",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/issues/601":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Difference",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/issues/601":
            assert body == {"state": "closed"}
            return {"number": 601, "state": "closed"}
        if method == "POST" and path == f"/repos/{owner}/{repo}/pulls":
            assert body is not None
            return {
                "number": 602,
                "html_url": f"https://github.com/{owner}/{repo}/pull_request/602",
                "title": body["title"],
                "body": body["body"],
                "head": {"ref": body["head"]},
                "base": {"ref": body["base"]},
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/pulls/602":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Change",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "head": {"ref": _MOCK_CONFIG.change_head_ref},
                "base": {"ref": _MOCK_CONFIG.change_base_ref},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/pulls/602":
            assert body == {"state": "closed"}
            return {"number": 602, "state": "closed"}
        if method == "GET" and path == f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs":
            return {"check_runs": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/check-runs":
            assert body is not None
            return {
                "id": 603,
                "html_url": f"https://github.com/{owner}/{repo}/check_run/603",
                "name": body["name"],
                "head_sha": body["head_sha"],
                "status": body["status"],
                "conclusion": body["conclusion"],
                "output": body["output"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/check-runs/603":
            return {
                "name": _MOCK_CONFIG.artifact_naming_prefix,
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": "neutral",
                "output": {"title": _MOCK_CONFIG.artifact_naming_prefix, "summary": "harness"},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/check-runs/603":
            assert body == {"status": "completed", "conclusion": "cancelled"}
            return {"id": 603, "status": "completed", "conclusion": "cancelled"}
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    result = _run_v3_authorized_execution(
        tmp_path,
        _MOCK_CONFIG,
        lambda projection_kind: RealGitHubAdapter(token=_MOCK_CONFIG.token),
    )

    assert _MOCK_CONFIG.authorized_artifact_count == 3
    assert result["materialized_count"] == 3
    assert len(result["cleanup_receipt"].outcomes) == 3
    assert result["cleanup_receipt"].all_closed
    # No merge call is ever made -- no method this harness or ``_close_artifact`` calls is
    # capable of one, and the handler's own fallback would raise on any unexpected call.
    assert not any(method == "PUT" for method, _ in calls)
    assert not any("/merge" in path for _, path in calls)
    assert sum(1 for method, _ in calls if method == "PATCH") == 3


def test_v3_authorized_execution_refuses_beyond_the_authorized_count_and_still_cleans_up_what_it_materialized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The required partial-run/failure handling: an authorized count too small for the
    complete three-projection run refuses the third projection's own ``materialize`` call
    before any artifact is ever created for it, while the two artifacts this run did already
    materialize are still cleaned up -- the cleanup terminal covers exactly what this run
    actually created, never a false claim of full-run completion."""

    narrow_config = replace(_MOCK_CONFIG, authorized_artifact_count=2)
    owner, repo = narrow_config.owner, narrow_config.repo
    head_sha = narrow_config.evidence_head_sha
    calls: list[tuple[str, str]] = []

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        calls.append((method, path))
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/issues":
            assert body is not None
            return {
                "number": 701,
                "html_url": f"https://github.com/{owner}/{repo}/issue/701",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/issues/701":
            return {
                "title": f"{narrow_config.artifact_naming_prefix} -- Difference",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/issues/701":
            assert body == {"state": "closed"}
            return {"number": 701, "state": "closed"}
        if method == "POST" and path == f"/repos/{owner}/{repo}/pulls":
            assert body is not None
            return {
                "number": 702,
                "html_url": f"https://github.com/{owner}/{repo}/pull_request/702",
                "title": body["title"],
                "body": body["body"],
                "head": {"ref": body["head"]},
                "base": {"ref": body["base"]},
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/pulls/702":
            return {
                "title": f"{narrow_config.artifact_naming_prefix} -- Change",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "head": {"ref": narrow_config.change_head_ref},
                "base": {"ref": narrow_config.change_base_ref},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/pulls/702":
            assert body == {"state": "closed"}
            return {"number": 702, "state": "closed"}
        if method == "GET" and path == f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs":
            return {"check_runs": []}
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    with pytest.raises(V3ArtifactBudgetExceededError):
        _run_v3_authorized_execution(
            tmp_path,
            narrow_config,
            lambda projection_kind: RealGitHubAdapter(token=narrow_config.token),
        )

    # The third projection's own artifact-creating call never happens -- the budget refusal
    # happens before it -- while both artifacts already materialized are still cleaned up.
    assert not any(
        method == "POST" and path == f"/repos/{owner}/{repo}/check-runs" for method, path in calls
    )
    assert sum(1 for method, _ in calls if method == "PATCH") == 2


# ---------------------------------------------------------------------------
# Structural Review Round 6 (Issue #62, P14-R6-F1): post-write/pre-return failure controls --
# a genuine external write followed by a failure in any later route step (here, observation)
# must still leave the artifact registered for cleanup, since registration now happens at the
# external-write boundary itself (inside ``_BudgetEnforcingAdapter.materialize``), never after
# the whole ``project_to_github`` call has already returned success.
# ---------------------------------------------------------------------------


class _ObserveFailingAdapter:
    """Wrap *adapter*, passing ``materialize``/``find_by_correlation_key`` straight through
    but unconditionally raising on ``observe`` -- simulates any failure that happens after a
    genuine external write already succeeded (observation itself, receipt construction, the
    Envelope's own Store commit, or any later route step), proving cleanup still covers the
    artifact the external write already created."""

    def __init__(self, adapter: GitHubAdapter) -> None:
        self._adapter = adapter
        self.adapter_identity = adapter.adapter_identity

    def materialize(self, **kwargs: Any) -> Mapping[str, Any]:
        return self._adapter.materialize(**kwargs)

    def find_by_correlation_key(self, **kwargs: Any) -> Mapping[str, Any] | None:
        return self._adapter.find_by_correlation_key(**kwargs)

    def observe(self, **kwargs: Any) -> Mapping[str, Any]:
        raise RuntimeError("simulated failure after a genuine external write already succeeded")


def _post_write_failure_transport_handler(
    config: V3TargetConfiguration, calls: list[tuple[str, str]]
) -> Callable[[str, str, dict[str, Any] | None], dict[str, Any]]:
    """Build a transport handler covering the calls a run reaches when zero, one, or two
    leading projection kinds complete their entire route normally (materialize, then a real
    GET-by-id re-observe) before the one *failing* kind's own materialize succeeds but its
    ``observe`` is never actually invoked through the real transport at all
    (:class:`_ObserveFailingAdapter` raises before that call) -- search/creation endpoints for
    all three kinds, their own GET-by-id read-back, and their own PATCH close/cancel
    endpoints."""

    owner, repo = config.owner, config.repo
    head_sha = config.evidence_head_sha

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        calls.append((method, path))
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "GET" and path == f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs":
            return {"check_runs": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/issues":
            assert body is not None
            return {
                "number": 801,
                "html_url": f"https://github.com/{owner}/{repo}/issue/801",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/issues/801":
            return {
                "title": f"{config.artifact_naming_prefix} -- Difference",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/issues/801":
            assert body == {"state": "closed"}
            return {"number": 801, "state": "closed"}
        if method == "POST" and path == f"/repos/{owner}/{repo}/pulls":
            assert body is not None
            return {
                "number": 802,
                "html_url": f"https://github.com/{owner}/{repo}/pull_request/802",
                "title": body["title"],
                "body": body["body"],
                "head": {"ref": body["head"]},
                "base": {"ref": body["base"]},
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/pulls/802":
            return {
                "title": f"{config.artifact_naming_prefix} -- Change",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "head": {"ref": config.change_head_ref},
                "base": {"ref": config.change_base_ref},
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/pulls/802":
            assert body == {"state": "closed"}
            return {"number": 802, "state": "closed"}
        if method == "POST" and path == f"/repos/{owner}/{repo}/check-runs":
            assert body is not None
            return {
                "id": 803,
                "html_url": f"https://github.com/{owner}/{repo}/check_run/803",
                "name": body["name"],
                "head_sha": body["head_sha"],
                "status": body["status"],
                "conclusion": body["conclusion"],
                "output": body["output"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/check-runs/803":
            assert body == {"status": "completed", "conclusion": "cancelled"}
            return {"id": 803, "status": "completed", "conclusion": "cancelled"}
        raise AssertionError(f"unexpected call: {method} {path}")

    return handler


@pytest.mark.parametrize(
    ("failing_kind", "expected_patch_count"),
    [
        ("DIFFERENCE_ISSUE", 1),
        ("CHANGE_PULL_REQUEST", 2),
        ("EVIDENCE_ARTIFACT", 3),
    ],
)
def test_cleanup_still_covers_an_artifact_when_a_later_route_step_fails_after_materialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing_kind: str, expected_patch_count: int
) -> None:
    """One control per projection kind (Structural Review Round 6, Issue #62, P14-R6-F1): the
    named kind's own external write genuinely succeeds, then the run fails in a later route
    step (here, observation) -- every artifact materialized up to and including that failing
    kind is still represented in the cleanup terminal, proving registration happens at the
    external-write boundary itself, not after ``project_to_github`` has already returned."""

    calls: list[tuple[str, str]] = []
    handler = _post_write_failure_transport_handler(_MOCK_CONFIG, calls)
    _install_transport(monkeypatch, handler)

    def adapter_factory(projection_kind: str) -> GitHubAdapter:
        real = RealGitHubAdapter(token=_MOCK_CONFIG.token)
        if projection_kind == failing_kind:
            return _ObserveFailingAdapter(real)
        return real

    with pytest.raises(RuntimeError, match="simulated failure"):
        _run_v3_authorized_execution(tmp_path, _MOCK_CONFIG, adapter_factory)

    assert sum(1 for method, _ in calls if method == "PATCH") == expected_patch_count


# ---------------------------------------------------------------------------
# Structural Review Round 6 (P14-R6-F1): a non-error HTTP response alone is never itself
# proof of a confirmed terminal state -- a cleanup PATCH whose own returned body does not
# actually reflect closure, and a cleanup PATCH the transport itself never completes, must
# both report ``closed=False``, never a false success.
# ---------------------------------------------------------------------------


def test_cleanup_response_not_reflecting_closure_is_not_reported_as_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/issues":
            assert body is not None
            return {
                "number": 901,
                "html_url": f"https://github.com/{owner}/{repo}/issue/901",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/issues/901":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Difference",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/issues/901":
            # A non-error HTTP response whose own body does *not* actually confirm closure
            # (a stale/tampered/wrong-shaped state) -- must never be trusted as success.
            return {"number": 901, "state": "open"}
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    sink: list[V3CleanupReceipt] = []
    # A budget of 1 stops the run right after the Difference/Issue kind's own materialize --
    # the identical, already-proven budget-refusal mechanism, used here only to isolate
    # exactly one materialized artifact for this cleanup-tamper control.
    with pytest.raises(V3ArtifactBudgetExceededError):
        _run_v3_authorized_execution(
            tmp_path,
            replace(_MOCK_CONFIG, authorized_artifact_count=1),
            lambda projection_kind: RealGitHubAdapter(token=_MOCK_CONFIG.token),
            cleanup_receipt_sink=sink,
        )

    assert len(sink) == 1
    cleanup_receipt = sink[0]
    assert len(cleanup_receipt.outcomes) == 1
    assert cleanup_receipt.all_closed is False
    assert cleanup_receipt.outcomes[0].closed is False
    assert "does not confirm closure" in (cleanup_receipt.outcomes[0].error or "")


def test_cleanup_transport_unavailable_is_not_reported_as_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, repo = _MOCK_CONFIG.owner, _MOCK_CONFIG.repo

    def handler(method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        if method == "GET" and path.startswith("/search/issues"):
            return {"items": []}
        if method == "POST" and path == f"/repos/{owner}/{repo}/issues":
            assert body is not None
            return {
                "number": 902,
                "html_url": f"https://github.com/{owner}/{repo}/issue/902",
                "title": body["title"],
                "body": body["body"],
                "updated_at": "2026-09-08T00:00:01Z",
            }
        if method == "GET" and path == f"/repos/{owner}/{repo}/issues/902":
            return {
                "title": f"{_MOCK_CONFIG.artifact_naming_prefix} -- Difference",
                "body": "harness\n\n<!-- manosube-projection-correlation-key: ignored -->",
                "updated_at": "2026-09-08T00:00:02Z",
            }
        if method == "PATCH" and path == f"/repos/{owner}/{repo}/issues/902":
            raise TimeoutError("simulated transport unavailability")
        raise AssertionError(f"unexpected call: {method} {path}")

    _install_transport(monkeypatch, handler)
    sink: list[V3CleanupReceipt] = []
    with pytest.raises(V3ArtifactBudgetExceededError):
        _run_v3_authorized_execution(
            tmp_path,
            replace(_MOCK_CONFIG, authorized_artifact_count=1),
            lambda projection_kind: RealGitHubAdapter(token=_MOCK_CONFIG.token),
            cleanup_receipt_sink=sink,
        )

    assert len(sink) == 1
    cleanup_receipt = sink[0]
    assert len(cleanup_receipt.outcomes) == 1
    assert cleanup_receipt.all_closed is False
    assert cleanup_receipt.outcomes[0].closed is False
    assert "simulated transport unavailability" in (cleanup_receipt.outcomes[0].error or "")
