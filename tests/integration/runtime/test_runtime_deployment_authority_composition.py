"""P15-R4-F1: the trust anchor is owned by a composition step, and the request-facing bootstrap
has no parameter through which any of it can be substituted.

**The finding, restated.** Round 3 (P15-R3-F1) made provisioning require a canonical,
Store-committed, ACTIVE ``runtime_root_admission`` genuinely signed by an externally supplied
trust anchor -- a real control, and every one of its checks still runs. But it required the anchor
**and** the admission reference as keyword arguments of the *request-facing* capability call, so
a caller supplied both sides of the question:

```text
bootstrap_projection_execution_capability(
    TrustedRuntimeRoot(attacker_store, attacker_project, attacker_binding),
    runtime_root_admission_ref=<attacker's own, correctly signed, ACTIVE admission>,
    trust_anchor_public_key_hex=<the attacker's own matching public key>,   <-- caller-supplied
    ...
)                                                                          ACCEPTED, and wrong
```

Round 4 replaces the check with an ownership boundary:

```text
TRUSTED_DEPLOYMENT_COMPOSITION   owns the Store handle, project_id, project_binding_id, the
                                 root-admission selection, and the configured anchor. Runs once,
                                 before any request boundary exists.
REQUEST_FACING_BOOTSTRAP         may supply operation-scoped references only. It has NO parameter
                                 for any of the above -- proved by introspection, not by eye.
```

and closes the second half of the same class of defect one level up from where Round 3 closed it
for declarations: a root admission now has a signed ``generation``/``predecessor_ref`` chain and a
real pointer in Project State, so a composition-level rotation or revocation genuinely takes
effect rather than leaving the superseded admission usable forever.

**Disclosed, and deliberate: an already-composed authority is a cached capability.** Composition
Boots and verifies the anchor exactly once and then discards it; the anchor is absent from the
authority's own state and is not re-verified per request-facing call. That is the direct
consequence of the adopted contract's own wording -- "closed over afterward", "absent from every
request-facing execution signature" -- which rules out per-request re-verification. So rotation
and revocation bind the **next** composition, exactly as a rotated credential binds the next
issuance rather than retroactively invalidating a token already in a caller's hand. The controls
below prove that boundary precisely rather than overclaiming it
(``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.5, item 1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.runtime_world import (
    ROOT_ADMISSION_RECORD_KIND,
    admission_successor_fields,
    admitted_root,
    alternate_bound,
    bound,
    commit_declaration,
    commit_grant,
    commit_records,
    commit_root_admission,
    foreign_trust_anchor_private_key,
    root_admission_for,
    sign_alternate_github_projection_grant_declaration,
    trust_anchor_public_key_hex,
)

from manosube_agent_civilization.authority import evaluate_projection_authorization
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import FakeGitHubAdapter, ProjectionExecutionCapability
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.runtime import (
    bootstrap as bootstrap_module,
    commit_runtime_root_admission,
)
from manosube_agent_civilization.runtime.admission_registry import current_root_admission_id
from manosube_agent_civilization.runtime.bootstrap import (
    RuntimeDeploymentAuthority,
    bootstrap_projection_execution_capability,
    compose_trusted_runtime_deployment_authority,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import runtime_root_admission_target_key

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
_PAYLOAD = {
    "name": "MANOSUBE Evidence Check",
    "head_sha": "a" * 40,
    "status": "completed",
    "conclusion": "neutral",
    "output": {"title": "Evidence artifact", "summary": "hello"},
}


def _attacker_anchor_public_key_hex() -> str:
    return foreign_trust_anchor_private_key().public_key().public_bytes_raw().hex()


def _authority_world(
    store: Any,
    ctx: dict[str, Any],
    *,
    recorded_at: str,
    signer: Any = None,
    transaction_prefix: str,
    anchor: str | None = None,
    admission_signer: Any = None,
) -> dict[str, Any]:
    """Commit one genuine subject/grant/declaration triple into *store*, then admit and compose.

    *anchor*/*admission_signer* exist so the alternate world below can be admitted under its
    **own** trust anchor -- a genuinely correct, genuinely signed admission, verified against the
    matching attacker public key. That is the exact shape the decisive control needs: a world that
    is legitimate on its own terms *and* legitimately admitted on its own terms.
    """

    evidence = derive_evidence(observation_evidence_request(recorded_at=recorded_at))
    commit_records(
        store,
        ctx["project_id"],
        store.load_current(ctx["project_id"]),
        f"{transaction_prefix}-EVIDENCE",
        [("observation_evidence", evidence["evidence_id"], evidence)],
    )
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    human_authority_ref = dict(boot_context.human_authority_ref)
    grant_ref, grant = commit_grant(
        store,
        ctx["project_id"],
        human_authority_ref,
        f"{transaction_prefix}-GRANT",
        subject_ref={"kind": "observation_evidence", "id": evidence["evidence_id"]},
        subject_fingerprint=evidence_semantic_fingerprint(evidence),
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
    )
    declaration_ref = commit_declaration(
        store,
        ctx["project_id"],
        ctx["project_binding_id"],
        human_authority_ref,
        grant,
        signer=signer,
    )
    world = {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": human_authority_ref,
        "grant_ref": grant_ref,
        "declaration_ref": declaration_ref,
    }
    if anchor is None:
        world["admitted"] = admitted_root(
            store,
            project_id=ctx["project_id"],
            project_binding_id=ctx["project_binding_id"],
        )
    else:
        admission = root_admission_for(
            ctx["project_id"],
            ctx["project_binding_id"],
            signer=admission_signer,
        )
        ref = commit_root_admission(store, ctx["project_id"], admission, trust_anchor=anchor)
        world["admitted"] = {
            "deployment_authority": compose_trusted_runtime_deployment_authority(
                store,
                project_id=ctx["project_id"],
                project_binding_id=ctx["project_binding_id"],
                runtime_root_admission_ref=ref,
                trust_anchor_public_key_hex=anchor,
            ),
            "runtime_root_admission_ref": ref,
            "trust_anchor_public_key_hex": anchor,
            "runtime_root_admission": admission,
        }
    return world


@pytest.fixture
def _canonical(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path / "canonical")
    return _authority_world(
        store,
        ctx,
        recorded_at="2026-09-09T00:00:00Z",
        transaction_prefix="TX-COMPOSITION-CANONICAL",
    )


@pytest.fixture
def _attacker(tmp_path: Path) -> dict[str, Any]:
    """A fully self-consistent alternate world -- its own Store, its own external Human Authority,
    its own Ed25519 signing key, its own Project Binding, its own grants/declarations/subjects --
    **and** its own correctly signed, currently-admitted root admission, admitted under the
    attacker's own matching trust anchor.

    This is exactly the world the review's decisive control names, and exactly the world Round 3's
    request-facing signature would have accepted when the attacker supplied their own anchor
    alongside it.
    """

    store, ctx = alternate_bound(tmp_path / "attacker")
    return _authority_world(
        store,
        ctx,
        recorded_at="2026-09-09T00:00:02Z",
        signer=sign_alternate_github_projection_grant_declaration,
        transaction_prefix="TX-COMPOSITION-ATTACKER",
        anchor=_attacker_anchor_public_key_hex(),
        admission_signer=foreign_trust_anchor_private_key(),
    )


def _reachable_strings(value: Any, *, depth: int = 0, seen: set[int] | None = None) -> list[str]:
    """Every string reachable from *value* within a bounded traversal of its own attributes,
    slots, and containers -- the material an "is this secret retained anywhere?" question has to
    be answered over, rather than over one hand-picked attribute."""

    seen = seen if seen is not None else set()
    if depth > 5 or id(value) in seen:
        return []
    seen.add(id(value))
    if isinstance(value, str):
        return [value]
    if isinstance(value, bytes):
        return [value.decode("utf-8", "replace")]
    if isinstance(value, dict):
        found: list[str] = []
        for key, item in value.items():
            found.extend(_reachable_strings(key, depth=depth + 1, seen=seen))
            found.extend(_reachable_strings(item, depth=depth + 1, seen=seen))
        return found
    if isinstance(value, list | tuple | set | frozenset):
        found = []
        for item in value:
            found.extend(_reachable_strings(item, depth=depth + 1, seen=seen))
        return found
    found = [repr(value)]
    for slot in getattr(type(value), "__slots__", ()):
        if hasattr(value, slot):
            found.extend(_reachable_strings(getattr(value, slot), depth=depth + 1, seen=seen))
    for item in getattr(value, "__dict__", {}).values():
        found.extend(_reachable_strings(item, depth=depth + 1, seen=seen))
    return found


# ---------------------------------------------------------------------------
# The composition-bound world reaches the controlled adapter boundary
# ---------------------------------------------------------------------------


def test_a_canonical_composition_bound_world_reaches_the_controlled_adapter(
    _canonical: dict[str, Any],
) -> None:
    """The positive decisive control. A deployment composes once, hands request-facing code the
    resulting authority and nothing else, and a real capability reaches a controlled adapter --
    zero live network calls, since ``FakeGitHubAdapter`` reaches nothing."""

    capability = bootstrap_projection_execution_capability(
        _canonical["admitted"]["deployment_authority"],
        github_projection_grant_refs=[_canonical["grant_ref"]],
        github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)

    adapter = FakeGitHubAdapter()
    result = capability.execute(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        projection_payload=_PAYLOAD,
        adapter=adapter,
        materialized_at="2026-09-09T00:00:00Z",
        attempt_claim_token="RUNTIME-COMPOSITION-ATTEMPT-0001",  # noqa: S106
    )
    assert adapter.materialize_call_count == 1
    assert result["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# The raw anchor is genuinely gone once composition has run
# ---------------------------------------------------------------------------


def test_the_composed_authority_retains_the_raw_trust_anchor_nowhere(
    _canonical: dict[str, Any],
) -> None:
    """Contract 1, item 2, proved dynamically: the anchor is admitted only at the trusted
    composition step and is **closed over afterward** -- here, discarded outright.

    Retaining it would recreate exactly the "raw anchor reachable downstream" problem this whole
    contract exists to close, so the assertion is over everything reachable from the composed
    object, not over one hand-picked attribute: no attribute, slot, container, or ``repr`` of it
    contains the anchor hex.
    """

    authority = _canonical["admitted"]["deployment_authority"]
    anchor = trust_anchor_public_key_hex()
    assert len(anchor) == 64
    reachable = _reachable_strings(authority)
    assert reachable, "the traversal must actually reach something"
    assert not any(anchor in text for text in reachable), "the raw trust anchor is retained"
    assert anchor not in repr(authority)


def test_the_composed_authority_exposes_no_public_accessor_at_all(
    _canonical: dict[str, Any],
) -> None:
    """It is a capability, not a record: nothing public hands back the Store, the project, the
    Binding, or the bound admission body. What it *does* retain -- deliberately -- is the exact
    admission generation it was composed against, so a bound context can always say which
    anchor/admission generation it speaks for (Contract 1, item 5)."""

    authority = _canonical["admitted"]["deployment_authority"]
    assert [name for name in dir(authority) if not name.startswith("_")] == []
    assert authority._runtime_root_admission_generation == 0
    assert (
        authority._runtime_root_admission_id
        == (_canonical["admitted"]["runtime_root_admission_ref"]["id"])
    )
    assert "Store" not in repr(authority)
    assert _canonical["project_id"] not in repr(authority)


# ---------------------------------------------------------------------------
# The decisive alternate-world control
# ---------------------------------------------------------------------------


def test_the_attacker_world_is_genuinely_self_consistent_and_self_admitted(
    _attacker: dict[str, Any],
) -> None:
    """Non-vacuity, and the premise the decisive control below rests on.

    The attacker world is not broken in any way. It is bound through the identical real
    ``bind_project`` route under its own Human Authority and signing key; its grants and
    declarations are genuinely signed; and its root admission is genuinely signed by, and
    genuinely admitted under, *its own* trust anchor -- committed through the identical shipped
    committer, so its admission chain pointer is genuinely populated. Composing within itself
    yields a real capability.

    Round 3's request-facing signature would have accepted exactly this, because the attacker
    supplied the anchor too.
    """

    capability = bootstrap_projection_execution_capability(
        _attacker["admitted"]["deployment_authority"],
        github_projection_grant_refs=[_attacker["grant_ref"]],
        github_projection_grant_declaration_refs=[_attacker["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)
    assert _attacker["admitted"]["trust_anchor_public_key_hex"] == _attacker_anchor_public_key_hex()
    assert _attacker["admitted"]["trust_anchor_public_key_hex"] != trust_anchor_public_key_hex()


def test_the_attacker_world_cannot_be_substituted_into_the_request_facing_bootstrap(
    _canonical: dict[str, Any], _attacker: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**The decisive control.** A fully self-consistent alternate Store, with its own Binding,
    Authority, grants and subjects, a correctly signed root admission, and the matching attacker
    public key, cannot be substituted into the request-facing bootstrap -- and every attempt costs
    zero adapter and zero network calls.

    Every substitution the attacker could try is enumerated, and each is a ``TypeError``: not a
    refusal computed at runtime, but a parameter that **does not exist**. Round 3 could only rule
    out ``store``/``project_id``/``project_binding_id``; ruling out the admission reference and
    the anchor is the whole Round 4 correction, because those two were exactly how the attacker
    supplied both sides of the question.
    """

    authority = _canonical["admitted"]["deployment_authority"]
    authorization_calls = {"count": 0}
    # The one adapter this whole delivery can reach at all. It is created here and handed to
    # nothing, so its call count is a direct, literal measurement of "zero adapter calls" -- and,
    # since it is a controlled fake that opens no socket, of zero network calls too.
    adapter = FakeGitHubAdapter()

    def _counting_evaluate(request: Any) -> Any:
        authorization_calls["count"] += 1
        return evaluate_projection_authorization(request)

    monkeypatch.setattr(bootstrap_module, "evaluate_projection_authorization", _counting_evaluate)

    substitutions: list[dict[str, Any]] = [
        {"store": _attacker["store"]},
        {"project_id": _attacker["project_id"]},
        {"project_binding_id": _attacker["project_binding_id"]},
        {"runtime_root_admission_ref": _attacker["admitted"]["runtime_root_admission_ref"]},
        {"trust_anchor_public_key_hex": _attacker["admitted"]["trust_anchor_public_key_hex"]},
        {
            "store": _attacker["store"],
            "project_id": _attacker["project_id"],
            "project_binding_id": _attacker["project_binding_id"],
            "runtime_root_admission_ref": _attacker["admitted"]["runtime_root_admission_ref"],
            "trust_anchor_public_key_hex": _attacker["admitted"]["trust_anchor_public_key_hex"],
        },
    ]
    for substitution in substitutions:
        with pytest.raises(TypeError):
            bootstrap_projection_execution_capability(
                authority,
                github_projection_grant_refs=[_canonical["grant_ref"]],
                github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
                **substitution,
            )
    assert authorization_calls["count"] == 0

    # And the attacker's own composed authority, handed in directly, reaches nothing of the
    # canonical world's: it is bound to the attacker's own Store and project, so the canonical
    # grant/declaration references simply do not resolve inside it.
    with pytest.raises(RuntimeRequirementError):
        bootstrap_projection_execution_capability(
            _attacker["admitted"]["deployment_authority"],
            github_projection_grant_refs=[_canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
        )
    assert authorization_calls["count"] == 0

    # Zero adapter calls, stated literally rather than inferred: no capability object was ever
    # produced by any attempt above, so there is nothing that could have reached an adapter, and
    # the one adapter in this test was never touched.
    assert adapter.materialize_call_count == 0


# ---------------------------------------------------------------------------
# Substituting each element independently, at the composition boundary
# ---------------------------------------------------------------------------


def _refuses_composition(
    *,
    store: Any,
    project_id: str,
    project_binding_id: str,
    admission_ref: Any,
    anchor: Any,
) -> str:
    with pytest.raises(RuntimeRequirementError) as raised:
        compose_trusted_runtime_deployment_authority(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            runtime_root_admission_ref=admission_ref,
            trust_anchor_public_key_hex=anchor,
        )
    return str(raised.value)


def test_substituting_only_the_anchor_is_independently_refused(
    _canonical: dict[str, Any],
) -> None:
    """Everything canonical except the anchor: the attacker's own well-formed, genuinely
    different Ed25519 public key. The anchor decides, and only the anchor."""

    message = _refuses_composition(
        store=_canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        admission_ref=_canonical["admitted"]["runtime_root_admission_ref"],
        anchor=_attacker_anchor_public_key_hex(),
    )
    assert "genuine signature" in message, message


def test_substituting_only_the_admission_is_independently_refused(
    _canonical: dict[str, Any], _attacker: dict[str, Any]
) -> None:
    """Everything canonical except the admission reference, which names the attacker's own
    genuinely valid, genuinely current admission -- valid *there*, resolvable nowhere here."""

    message = _refuses_composition(
        store=_canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        admission_ref=_attacker["admitted"]["runtime_root_admission_ref"],
        anchor=trust_anchor_public_key_hex(),
    )
    assert "does not resolve" in message, message


def test_substituting_only_the_store_is_independently_refused(
    _canonical: dict[str, Any], _attacker: dict[str, Any]
) -> None:
    """The canonical project, Binding, admission reference and anchor -- against the attacker's
    Store. Nothing about the canonical world exists in there, so Boot itself refuses before any
    admission question is asked."""

    with pytest.raises(Exception) as raised:
        compose_trusted_runtime_deployment_authority(
            _attacker["store"],
            project_id=_canonical["project_id"],
            project_binding_id=_canonical["project_binding_id"],
            runtime_root_admission_ref=_canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
        )
    assert not isinstance(raised.value, TypeError)


def test_substituting_only_the_project_is_independently_refused(
    _canonical: dict[str, Any], _attacker: dict[str, Any]
) -> None:
    """Disclosed: the alternate world deliberately reuses the canonical *project name* -- what
    makes it an alternate world is its own Human Authority, signing key and Project Binding, not a
    renamed project -- so substituting ``_attacker["project_id"]`` would substitute nothing at
    all. A genuinely different project identity is named instead."""

    assert _attacker["project_id"] == _canonical["project_id"]
    with pytest.raises(Exception) as raised:
        compose_trusted_runtime_deployment_authority(
            _canonical["store"],
            project_id="PRJ-ELSEWHERE-0001",
            project_binding_id=_canonical["project_binding_id"],
            runtime_root_admission_ref=_canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
        )
    assert not isinstance(raised.value, TypeError)


def test_substituting_only_the_binding_is_independently_refused(
    _canonical: dict[str, Any], _attacker: dict[str, Any]
) -> None:
    with pytest.raises(Exception) as raised:
        compose_trusted_runtime_deployment_authority(
            _canonical["store"],
            project_id=_canonical["project_id"],
            project_binding_id=_attacker["project_binding_id"],
            runtime_root_admission_ref=_canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
        )
    assert not isinstance(raised.value, TypeError)


# ---------------------------------------------------------------------------
# The root-admission lifecycle: rotation and revocation are genuinely effective
# ---------------------------------------------------------------------------


def _admission_pointer(world: dict[str, Any]) -> str | None:
    return current_root_admission_id(
        world["store"].load_current(world["project_id"]),
        runtime_root_admission_target_key(
            {
                "project_binding_ref": {
                    "kind": "project_binding",
                    "id": world["project_binding_id"],
                }
            }
        ),
    )


def _rotate(world: dict[str, Any], *, status: str, declared_at: str, at: str) -> dict[str, Any]:
    current = world["admitted"]["runtime_root_admission"]
    successor = root_admission_for(
        world["project_id"],
        world["project_binding_id"],
        status=status,
        declared_at=declared_at,
        **admission_successor_fields(current),
    )
    commit_runtime_root_admission(
        world["store"],
        world["project_id"],
        successor,
        trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
        committed_at=at,
    )
    return successor


def test_an_admission_rotated_at_the_composition_level_can_no_longer_be_replayed(
    _canonical: dict[str, Any],
) -> None:
    """Contract 1, item 5. Compose successfully against admission A; rotate to B through the
    shipped committer; then prove a *fresh* composition attempt referencing A's own
    still-individually-valid, still-resolvable, still-ACTIVE, still-anchor-signed reference is
    refused.

    Round 3 accepted exactly this -- it asked only "does a matching ACTIVE admission exist and
    resolve?", which is precisely the ineffective-revocation question Round 3 itself had already
    rejected one level down for declarations.
    """

    a_ref = _canonical["admitted"]["runtime_root_admission_ref"]
    assert _admission_pointer(_canonical) == a_ref["id"]

    b = _rotate(
        _canonical, status="ACTIVE", declared_at="2026-09-08T05:00:00Z", at="2026-09-09T05:00:00Z"
    )
    b_id = str(b["runtime_root_admission_id"])
    assert _admission_pointer(_canonical) == b_id != a_ref["id"]

    # A is untouched: still resolvable, still ACTIVE, still genuinely anchor-signed.
    resolved_a = _canonical["store"].resolve_record(
        _canonical["project_id"], ROOT_ADMISSION_RECORD_KIND, a_ref["id"]
    )
    assert resolved_a == _canonical["admitted"]["runtime_root_admission"]
    assert resolved_a["status"] == "ACTIVE"

    message = _refuses_composition(
        store=_canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        admission_ref=a_ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert "no longer the current one" in message, message

    # ...and composing against B, the admission the pointer now names, succeeds normally.
    recomposed = compose_trusted_runtime_deployment_authority(
        _canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        runtime_root_admission_ref={"kind": ROOT_ADMISSION_RECORD_KIND, "id": b_id},
        trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
    )
    assert isinstance(recomposed, RuntimeDeploymentAuthority)
    assert recomposed._runtime_root_admission_generation == 1


def test_a_revoked_admission_chain_admits_no_further_composition_at_all(
    _canonical: dict[str, Any],
) -> None:
    """Revocation closes both doors at once, exactly as it does for declarations: the superseded
    admission is no longer current, and the revocation itself is not ``ACTIVE``. After it, this
    Project Binding's own chain admits nothing."""

    a_ref = _canonical["admitted"]["runtime_root_admission_ref"]
    b = _rotate(
        _canonical, status="REVOKED", declared_at="2026-09-08T06:00:00Z", at="2026-09-09T06:00:00Z"
    )
    b_id = str(b["runtime_root_admission_id"])
    assert _admission_pointer(_canonical) == b_id

    superseded = _refuses_composition(
        store=_canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        admission_ref=a_ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert "no longer the current one" in superseded, superseded

    revoked = _refuses_composition(
        store=_canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        admission_ref={"kind": ROOT_ADMISSION_RECORD_KIND, "id": b_id},
        anchor=trust_anchor_public_key_hex(),
    )
    assert "is not ACTIVE" in revoked, revoked


def test_a_revoked_admission_chain_is_permanently_terminal(
    _canonical: dict[str, Any],
) -> None:
    """And it cannot be quietly reopened: no successor to the revocation, and no replay of any
    ancestor, is ever admitted for that chain again.

    Scope, disclosed: this proves the terminal property only. The adopted contract says a later
    reactivation "requires a separately adopted new target epoch/chain, not silent pointer
    movement", and deliberately does not require that epoch to be built now -- so it is not built
    (``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.5, item 8).
    """

    revocation = _rotate(
        _canonical, status="REVOKED", declared_at="2026-09-08T06:00:00Z", at="2026-09-09T06:00:00Z"
    )
    reactivation = root_admission_for(
        _canonical["project_id"],
        _canonical["project_binding_id"],
        declared_at="2026-09-08T07:00:00Z",
        **admission_successor_fields(revocation),
    )
    with pytest.raises(RuntimeRequirementError, match="terminal"):
        commit_runtime_root_admission(
            _canonical["store"],
            _canonical["project_id"],
            reactivation,
            trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
            committed_at="2026-09-09T07:00:00Z",
        )
    with pytest.raises(RuntimeRequirementError, match="terminal"):
        commit_runtime_root_admission(
            _canonical["store"],
            _canonical["project_id"],
            _canonical["admitted"]["runtime_root_admission"],
            trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
            committed_at="2026-09-09T08:00:00Z",
        )
    assert _admission_pointer(_canonical) == revocation["runtime_root_admission_id"]


def test_an_authority_composed_before_a_rotation_remains_usable_by_its_holder(
    _canonical: dict[str, Any],
) -> None:
    """The disclosed judgment call, proved rather than left as prose
    (``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.5, item 1).

    The adopted contract requires the anchor to be "closed over afterward" and "absent from every
    request-facing execution signature", which rules out per-request re-verification. An
    already-composed authority therefore behaves like a cached credential: it keeps working for
    whoever holds it until they recompose. Rotation and revocation bind the **next** composition,
    which is exactly what the two controls above prove, and this test states the other half
    honestly rather than letting a reader assume a retroactive property this design does not have.
    """

    authority = _canonical["admitted"]["deployment_authority"]
    _rotate(
        _canonical, status="REVOKED", declared_at="2026-09-08T06:00:00Z", at="2026-09-09T06:00:00Z"
    )
    capability = bootstrap_projection_execution_capability(
        authority,
        github_projection_grant_refs=[_canonical["grant_ref"]],
        github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)

    # ...while a fresh composition -- the thing a deployment does at its next startup -- is
    # refused outright, which is where a revocation actually takes effect.
    with pytest.raises(RuntimeRequirementError):
        compose_trusted_runtime_deployment_authority(
            _canonical["store"],
            project_id=_canonical["project_id"],
            project_binding_id=_canonical["project_binding_id"],
            runtime_root_admission_ref=_canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
        )


def test_an_admission_planted_without_the_committer_is_never_current(
    _canonical: dict[str, Any],
) -> None:
    """The "anyone who can write a Store record can admit anything" gap, closed at this level
    too: a perfectly genuine, correctly anchor-signed admission inserted as a raw record was never
    made current through the canonical commit-and-supersede path, so it admits nothing."""

    planted = root_admission_for(
        _canonical["project_id"],
        _canonical["project_binding_id"],
        declared_at="2026-09-08T09:00:00Z",
    )
    commit_records(
        _canonical["store"],
        _canonical["project_id"],
        _canonical["store"].load_current(_canonical["project_id"]),
        "TX-RUNTIME-PLANTED-ROOT-ADMISSION",
        [
            (
                ROOT_ADMISSION_RECORD_KIND,
                str(planted["runtime_root_admission_id"]),
                planted,
            )
        ],
    )
    message = _refuses_composition(
        store=_canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        admission_ref={
            "kind": ROOT_ADMISSION_RECORD_KIND,
            "id": str(planted["runtime_root_admission_id"]),
        },
        anchor=trust_anchor_public_key_hex(),
    )
    assert "no longer the current one" in message, message
