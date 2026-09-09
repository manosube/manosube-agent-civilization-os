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

**Round 5 (P15-R5-F1): the ownership boundary is now carried by a closure, not by a value type.**
Round 4's ``RuntimeDeploymentAuthority`` was an ordinary public frozen dataclass with an ordinary
public constructor, and the request-facing bootstrap was a free module-level function whose only
defence was an ``isinstance`` check -- so a caller could construct their **own** authority over an
alternate Store/Project/Binding and hand it straight in. The review rules out a sentinel, a
private constructor, a leading-underscore field, an opaque ``repr`` and an ``isinstance`` check as
the trust control, so the type is deleted and composition now returns the request-facing operation
*itself*:

```text
compose_trusted_runtime_deployment_authority(...) -> the bound request-facing callable
<returned callable>(*, github_projection_grant_refs, github_projection_grant_declaration_refs)
```

A closure has no public constructor. The only way to obtain a working one is to call composition,
which runs the full anchor-signature/currency admission gate first.

**Round 5 (P15-R5-F2): every new capability issuance rechecks the bound admission's currency.**
Round 4 disclosed that an already-composed authority behaved like a cached credential -- rotation
and revocation bound only the *next* composition. Round 5 narrows that boundary without
contradicting the contract's "closed over afterward" wording, by separating two questions: the
*anchor* is still verified exactly once, at composition, and never appears on a request-facing
signature; but the *currency* of the already-admitted record is now proved freshly on every call,
from the canonical Store's own pointer plus the retained admission id and generation. A rotated or
revoked composition authority therefore mints **no new** capability, refusing before any grant
resolution and at zero adapter, network and authorization cost.

**Still disclosed, and deliberate: capabilities already issued are not retroactively revoked.**
The adopted boundary is prevention of *new* issuance from a no-longer-current composition
authority. A ``ProjectionExecutionCapability`` a holder obtained while the admission was still
current keeps working; that is stated as its own control below rather than left for a reader to
infer a retroactive property this design does not have.
"""

from __future__ import annotations

import inspect
from pathlib import Path
import types
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
    compose_trusted_runtime_deployment_authority,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import runtime_root_admission_target_key
from manosube_agent_civilization.runtime.root_admission import (
    verify_runtime_root_admission_signature,
)

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

    *anchor*/*admission_signer* exist so the attacker world below can be admitted under its
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
            "bootstrap": compose_trusted_runtime_deployment_authority(
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
    slots, containers, **and closure cells** -- the material an "is this secret retained
    anywhere?" question has to be answered over, rather than over one hand-picked attribute.

    P15-R5-F1 adds the closure-cell traversal: what composition now returns is a function object
    whose bound world lives in ``__closure__`` rather than in a dataclass's own slots, so a
    traversal that stopped at ``__dict__``/``__slots__`` would find nothing at all and the
    anchor-absence assertion below would be vacuous. It is proved non-vacuous explicitly, by
    requiring the traversal to *find* the bound admission id it genuinely does hold.
    """

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
    for cell in getattr(value, "__closure__", None) or ():
        try:
            contents = cell.cell_contents
        except ValueError:  # pragma: no cover -- an unfilled cell holds nothing to find
            continue
        found.extend(_reachable_strings(contents, depth=depth + 1, seen=seen))
    return found


# ---------------------------------------------------------------------------
# The composition-bound world reaches the controlled adapter boundary
# ---------------------------------------------------------------------------


def test_a_canonical_composition_bound_world_reaches_the_controlled_adapter(
    _canonical: dict[str, Any],
) -> None:
    """The positive decisive control (P15-R5-F1, required proof line 1). A deployment composes
    once, hands request-facing code the resulting **bound service** and nothing else, and calling
    that service with canonical grant/declaration references reaches a real capability and, when
    exercised, the controlled adapter boundary -- zero live network calls, since
    ``FakeGitHubAdapter`` reaches nothing."""

    bootstrap = _canonical["admitted"]["bootstrap"]
    capability = bootstrap(
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


def test_the_composed_bootstrap_retains_the_raw_trust_anchor_nowhere(
    _canonical: dict[str, Any],
) -> None:
    """Contract 1, item 2, proved dynamically: the anchor is admitted only at the trusted
    composition step and is **closed over afterward** -- here, discarded outright.

    Retaining it would recreate exactly the "raw anchor reachable downstream" problem this whole
    contract exists to close, so the assertion is over everything reachable from the composed
    service, not over one hand-picked attribute: no attribute, slot, container, closure cell, or
    ``repr`` of it contains the anchor hex. Round 5 (P15-R5-F1) makes the closure cells the place
    the bound world actually lives, so the traversal reaches into them explicitly -- and the
    non-vacuity assertion below is what proves it genuinely does.
    """

    bootstrap = _canonical["admitted"]["bootstrap"]
    anchor = trust_anchor_public_key_hex()
    assert len(anchor) == 64
    reachable = _reachable_strings(bootstrap)
    # Non-vacuity: the traversal must genuinely be able to find a string the service *does* hold,
    # or "the anchor is absent" would be an assertion about a traversal that finds nothing.
    admission_id = _canonical["admitted"]["runtime_root_admission_ref"]["id"]
    assert any(admission_id in text for text in reachable), (
        "the traversal cannot see the service's own bound admission id, so it could not see a "
        "retained anchor either"
    )
    assert not any(anchor in text for text in reachable), "the raw trust anchor is retained"
    assert anchor not in repr(bootstrap)


def test_the_composed_bootstrap_is_a_closure_with_no_public_constructor(
    _canonical: dict[str, Any],
) -> None:
    """P15-R5-F1: the control is *obtainability*, not a type check.

    What composition returns is a plain function object defined inside the composition entry
    point's own frame. There is no class to instantiate, no public constructor to call, and no
    module attribute holding an equivalent operation -- so the only way to obtain a working
    request-facing bootstrap is to call composition and pass its admission gate.

    What the closure *does* retain -- deliberately -- is the exact admission id and generation it
    was composed against, which is precisely what P15-R5-F2's per-call currency recheck needs and
    the most a service may hold without reintroducing a raw anchor downstream (Contract 1,
    item 5).
    """

    bootstrap = _canonical["admitted"]["bootstrap"]
    assert isinstance(bootstrap, types.FunctionType)
    assert bootstrap.__closure__, "the bound world must live in closure cells, not in arguments"
    assert not hasattr(bootstrap_module, "RuntimeDeploymentAuthority")
    assert not hasattr(bootstrap_module, "bootstrap_projection_execution_capability")
    assert {name for name in vars(bootstrap) if not name.startswith("_")} == set()

    bound = inspect.getclosurevars(bootstrap).nonlocals
    assert bound["bound_generation"] == 0
    assert bound["bound_admission_id"] == _canonical["admitted"]["runtime_root_admission_ref"]["id"]
    assert bound["project_id"] == _canonical["project_id"]
    assert bound["project_binding_id"] == _canonical["project_binding_id"]
    assert bound["store"] is _canonical["store"]
    assert "trust_anchor_public_key_hex" not in bound


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

    capability = _attacker["admitted"]["bootstrap"](
        github_projection_grant_refs=[_attacker["grant_ref"]],
        github_projection_grant_declaration_refs=[_attacker["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)
    assert _attacker["admitted"]["trust_anchor_public_key_hex"] == _attacker_anchor_public_key_hex()
    assert _attacker["admitted"]["trust_anchor_public_key_hex"] != trust_anchor_public_key_hex()


def test_the_attacker_world_cannot_be_substituted_into_the_request_facing_bootstrap(
    _canonical: dict[str, Any], _attacker: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**The decisive control** (P15-R5-F1, required proof lines 2-4). A fully self-consistent
    alternate Store, with its own Binding, Authority, grants and subjects, a correctly signed root
    admission, the matching attacker public key **and its own genuinely composed service**, cannot
    be supplied to the canonical request operation -- and every attempt costs zero authorization
    evaluations, zero adapter calls and zero network calls.

    Every substitution the attacker could try is enumerated, and each is a ``TypeError``: not a
    refusal computed at runtime, but a parameter that **does not exist**. Round 3 could only rule
    out ``store``/``project_id``/``project_binding_id``; Round 4 added the admission reference and
    the anchor; Round 5 adds the last one Round 4 itself had introduced -- ``deployment_authority``
    -- because *substituting the authority object* was the remaining expressible attack, and the
    object it named was an ordinary public dataclass anyone could construct.
    """

    bootstrap = _canonical["admitted"]["bootstrap"]
    attacker_bootstrap = _attacker["admitted"]["bootstrap"]
    authorization_calls = {"count": 0}
    # The one adapter this whole delivery can reach at all. It is created here and handed to
    # nothing, so its call count is a direct, literal measurement of "zero adapter calls" -- and,
    # since it is a controlled fake that opens no socket, of zero network calls too.
    adapter = FakeGitHubAdapter()

    def _counting_evaluate(request: Any) -> Any:
        authorization_calls["count"] += 1
        return evaluate_projection_authorization(request)

    monkeypatch.setattr(bootstrap_module, "evaluate_projection_authorization", _counting_evaluate)

    # (a) The attacker's own service, over the attacker's own references, genuinely works inside
    # the attacker's own world. This is expected and required: it is what makes every refusal
    # below a statement about ownership rather than about a broken world.
    inside_its_own_world = attacker_bootstrap(
        github_projection_grant_refs=[_attacker["grant_ref"]],
        github_projection_grant_declaration_refs=[_attacker["declaration_ref"]],
    )
    assert isinstance(inside_its_own_world, ProjectionExecutionCapability)
    assert authorization_calls["count"] == 1
    authorization_calls["count"] = 0

    # (b) There is no way to call the CANONICAL service with the attacker's authority or world
    # injected. Every kwarg the Round 3/Round 4 shapes used to accept is enumerated, including the
    # authority object itself, and each names a parameter that simply does not exist.
    substitutions: list[dict[str, Any]] = [
        {"deployment_authority": attacker_bootstrap},
        {"store": _attacker["store"]},
        {"project_id": _attacker["project_id"]},
        {"project_binding_id": _attacker["project_binding_id"]},
        {"runtime_root_admission_ref": _attacker["admitted"]["runtime_root_admission_ref"]},
        {"trust_anchor_public_key_hex": _attacker["admitted"]["trust_anchor_public_key_hex"]},
        {
            "deployment_authority": attacker_bootstrap,
            "store": _attacker["store"],
            "project_id": _attacker["project_id"],
            "project_binding_id": _attacker["project_binding_id"],
            "runtime_root_admission_ref": _attacker["admitted"]["runtime_root_admission_ref"],
            "trust_anchor_public_key_hex": _attacker["admitted"]["trust_anchor_public_key_hex"],
        },
    ]
    for substitution in substitutions:
        with pytest.raises(TypeError):
            bootstrap(
                github_projection_grant_refs=[_canonical["grant_ref"]],
                github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
                **substitution,
            )
        assert authorization_calls["count"] == 0, substitution

    # ...nor positionally: there is no first parameter to fill either.
    with pytest.raises(TypeError):
        bootstrap(
            attacker_bootstrap,
            github_projection_grant_refs=[_canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
        )
    assert authorization_calls["count"] == 0

    # And the attacker's own composed service, invoked directly, reaches nothing of the canonical
    # world's: it is bound to the attacker's own Store and project, so the canonical
    # grant/declaration references simply do not resolve inside it.
    with pytest.raises(RuntimeRequirementError):
        attacker_bootstrap(
            github_projection_grant_refs=[_canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
        )
    assert authorization_calls["count"] == 0

    # (c) The shape itself, proved by introspection over the *object composition returned* rather
    # than over a module-level function: only the two operation-scoped references, and none of the
    # six forbidden names.
    parameters = inspect.signature(bootstrap).parameters
    assert set(parameters) == {
        "github_projection_grant_refs",
        "github_projection_grant_declaration_refs",
    }
    for forbidden in (
        "deployment_authority",
        "store",
        "project_id",
        "project_binding_id",
        "runtime_root_admission_ref",
        "trust_anchor_public_key_hex",
    ):
        assert forbidden not in parameters

    # Zero adapter calls, stated literally rather than inferred: the one capability produced above
    # was produced inside the attacker's own world and never executed, and the one adapter in this
    # test was never handed to anything.
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
    assert callable(recomposed)
    assert inspect.getclosurevars(recomposed).nonlocals["bound_generation"] == 1


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


# ---------------------------------------------------------------------------
# P15-R5-F2: a no-longer-current composition authority issues no NEW capability
# ---------------------------------------------------------------------------


def _counting_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, int]:
    """Count every ``evaluate_projection_authorization`` the shipped bootstrap performs.

    Every refusal below must happen *before* grant resolution and therefore before any
    authorization evaluation -- which is also before any adapter or network call could exist,
    since a capability object is what reaches an adapter and none is produced. The identical
    counting technique Round 4's own decisive controls established.
    """

    calls = {"count": 0}

    def _counting_evaluate(request: Any) -> Any:
        calls["count"] += 1
        return evaluate_projection_authorization(request)

    monkeypatch.setattr(bootstrap_module, "evaluate_projection_authorization", _counting_evaluate)
    return calls


def _issue(world: dict[str, Any]) -> Any:
    return world["admitted"]["bootstrap"](
        github_projection_grant_refs=[world["grant_ref"]],
        github_projection_grant_declaration_refs=[world["declaration_ref"]],
    )


def test_a_service_composed_at_a_rotated_away_admission_issues_no_new_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R5-F2's decisive control, rotation half.** Compose at A (ACTIVE, generation 0);
    rotate the chain to B (ACTIVE, generation 1, predecessor A) through the shipped committer;
    then call the OLD service.

    Round 4 accepted this: the anchor had been verified once, at composition, and never again, so
    an already-composed authority kept minting capabilities from a superseded admission forever.
    The refusal now happens before a single grant is resolved -- zero authorization evaluations,
    and therefore zero adapter and zero network calls.
    """

    calls = _counting_bootstrap(monkeypatch)
    a_ref = _canonical["admitted"]["runtime_root_admission_ref"]
    assert _admission_pointer(_canonical) == a_ref["id"]

    b = _rotate(
        _canonical, status="ACTIVE", declared_at="2026-09-08T05:00:00Z", at="2026-09-09T05:00:00Z"
    )
    assert _admission_pointer(_canonical) == str(b["runtime_root_admission_id"]) != a_ref["id"]

    with pytest.raises(RuntimeRequirementError) as raised:
        _issue(_canonical)
    assert "no longer the current one" in str(raised.value), raised.value
    assert calls["count"] == 0


def test_a_service_composed_before_a_revocation_issues_no_new_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R5-F2's decisive control, revocation half.** The identical shape, with the successor
    committed as ``REVOKED`` instead of ``ACTIVE``. The old service refuses on currency for the
    same reason and at the same zero cost -- and a chain whose head is REVOKED admits nothing new
    at all afterwards, since even a *fresh* composition against that head is refused for not being
    ACTIVE (proved above)."""

    calls = _counting_bootstrap(monkeypatch)
    _rotate(
        _canonical, status="REVOKED", declared_at="2026-09-08T06:00:00Z", at="2026-09-09T06:00:00Z"
    )

    with pytest.raises(RuntimeRequirementError) as raised:
        _issue(_canonical)
    assert "no longer the current one" in str(raised.value), raised.value
    assert calls["count"] == 0


def test_the_refusal_is_on_currency_alone_not_because_the_old_admission_became_invalid(
    _canonical: dict[str, Any],
) -> None:
    """The non-vacuity control for both refusals above.

    A ``runtime_root_admission`` is immutable and content-addressed, so rotating or revoking a
    chain cannot alter the record it superseded: A stays individually resolvable, keeps its own
    unchanged content address and semantic fingerprint, stays ``ACTIVE``, and its signature still
    verifies against the very anchor it was signed under. If any of that had stopped being true,
    the refusals above would prove something much weaker than they claim. They refuse on
    **currency alone**.
    """

    a = _canonical["admitted"]["runtime_root_admission"]
    a_ref = _canonical["admitted"]["runtime_root_admission_ref"]
    _rotate(
        _canonical, status="ACTIVE", declared_at="2026-09-08T05:00:00Z", at="2026-09-09T05:00:00Z"
    )

    resolved = _canonical["store"].resolve_record(
        _canonical["project_id"], ROOT_ADMISSION_RECORD_KIND, a_ref["id"]
    )
    assert resolved == a
    assert resolved["status"] == "ACTIVE"
    assert verify_runtime_root_admission_signature(
        dict(resolved), trust_anchor_public_key_hex=trust_anchor_public_key_hex()
    )


def test_a_service_freshly_composed_at_the_new_current_admission_succeeds(
    _canonical: dict[str, Any],
) -> None:
    """The positive control P15-R5-F2 requires. Rotation does not break provisioning; it moves it.
    A deployment that recomposes against the admission the pointer now names -- the thing a real
    deployment does at its next startup -- gets a fully working service back and reaches a real
    capability through it."""

    b = _rotate(
        _canonical, status="ACTIVE", declared_at="2026-09-08T05:00:00Z", at="2026-09-09T05:00:00Z"
    )
    b_id = str(b["runtime_root_admission_id"])
    fresh = compose_trusted_runtime_deployment_authority(
        _canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
        runtime_root_admission_ref={"kind": ROOT_ADMISSION_RECORD_KIND, "id": b_id},
        trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
    )
    assert inspect.getclosurevars(fresh).nonlocals["bound_admission_id"] == b_id
    capability = fresh(
        github_projection_grant_refs=[_canonical["grant_ref"]],
        github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)

    adapter = FakeGitHubAdapter()  # controlled -- zero live network calls
    result = capability.execute(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        projection_payload=_PAYLOAD,
        adapter=adapter,
        materialized_at="2026-09-09T00:00:00Z",
        attempt_claim_token="RUNTIME-RECOMPOSED-ATTEMPT-0001",  # noqa: S106
    )
    assert adapter.materialize_call_count == 1
    assert result["receipt"].status == "VERIFIED"


def test_a_capability_issued_before_a_rotation_is_not_retroactively_revoked(
    _canonical: dict[str, Any],
) -> None:
    """The disclosed non-requirement, stated exactly as the adoption states it: "Already-issued
    downstream projection capabilities are not retroactively revoked by this correction. The
    adopted boundary is prevention of new issuance from a no-longer-current composition
    authority."

    So this test does the honest thing rather than letting a reader assume a retroactive property
    this correction does not have. It issues a capability from the service *while A is still
    current*, exercises it against the controlled adapter to prove it is genuinely working, then
    rotates the chain and proves (a) that already-issued capability object and the execution
    context bound to it are **unchanged** -- P15-R5-F2 reaches into nothing already handed out --
    while (b) the very same service can no longer issue a *new* one.

    Disclosed precisely, because the distinction matters: whether that already-issued capability
    would still *execute* after the rotation is not this correction's question at all. Phase 14's
    own independent context-currency check
    (:func:`~manosube_agent_civilization.projection.execution.execution_context_still_current`)
    refuses execution after **any** State transition, related or not -- a pre-existing mechanism
    with its own separate reasons, which a rotation commit trips exactly as an unrelated commit
    would. This test therefore asserts what this round is responsible for: the object is not
    touched, and new issuance is what stops.
    """

    before = _issue(_canonical)
    assert isinstance(before, ProjectionExecutionCapability)

    # Non-vacuity: it is a genuinely working capability while its world is still current.
    adapter = FakeGitHubAdapter()
    result = before.execute(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        projection_payload=_PAYLOAD,
        adapter=adapter,
        materialized_at="2026-09-09T00:00:00Z",
        attempt_claim_token="RUNTIME-PRE-ROTATION-ATTEMPT-0001",  # noqa: S106
    )
    assert adapter.materialize_call_count == 1
    assert result["receipt"].status == "VERIFIED"

    context_before = before._context
    bound_state_revision = context_before.state_revision
    bound_fingerprint = context_before.semantic_fingerprint
    bound_authorities = dict(context_before.authorities)

    _rotate(
        _canonical, status="REVOKED", declared_at="2026-09-08T06:00:00Z", at="2026-09-09T06:00:00Z"
    )

    # (a) Nothing about the already-issued capability changed: same object, same bound context,
    # same recorded State revision, fingerprint and pre-issued authorities.
    assert before._context is context_before
    assert context_before.state_revision == bound_state_revision
    assert context_before.semantic_fingerprint == bound_fingerprint
    assert dict(context_before.authorities) == bound_authorities

    # (b) ...and the service it came from mints nothing further.
    with pytest.raises(RuntimeRequirementError):
        _issue(_canonical)


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
