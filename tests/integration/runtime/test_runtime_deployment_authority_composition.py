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

**Round 7 (P15-R7-F1): each barrier now commits to the EXACT FULL RECORD, not only to a projection
of it.** Round 6's two recomputations are hashes of ``ROOT_ADMISSION_SEMANTIC_FIELDS``, a
projection that deliberately excludes three of the record's own fields -- its declared
``runtime_root_admission_id``, its declared ``runtime_root_admission_semantic_fingerprint``, and
its whole ``signature`` block. A Store-level substitution changing only one of those three left
every semantic field, and therefore every existing check, exactly as it was. Composition now
additionally captures a deterministic digest of the exact anchor-verified record, through this
repository's own single canonical serialization owner, and each barrier requires three further
things: declared id == recomputed id == bound id, the same three-way equality for the fingerprint,
and full-record commitment == the composition-time one. Nine requirements, not six; the four
isolated substitution controls are at the end of this file.

**Still disclosed, and deliberate: capabilities already issued are not retroactively revoked.**
The adopted boundary is prevention of *new* issuance from a no-longer-current composition
authority. A ``ProjectionExecutionCapability`` a holder obtained while the admission was still
current keeps working; that is stated as its own control below rather than left for a reader to
infer a retroactive property this design does not have.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
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
from manosube_agent_civilization.runtime.identity import (
    ROOT_ADMISSION_SEMANTIC_FIELDS,
    runtime_root_admission_semantic_fingerprint,
    runtime_root_admission_target_key,
)
from manosube_agent_civilization.runtime.root_admission import (
    verify_runtime_root_admission_signature,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

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


# ---------------------------------------------------------------------------
# P15-R6-F1: the pre-issuance barrier, and resolved-record integrity
# ---------------------------------------------------------------------------
#
# Round 5's per-call recheck ran ONCE, at the start of the request-facing call, and the capability
# was then built from that same original Boot snapshot after every grant, declaration and subject
# had been resolved and every Authority decision evaluated. Round 6 found that open in two
# independently reproducible ways, and the controls below exercise both as real races and real
# substitutions rather than asserting an outcome:
#
#   1. a canonical rotation or revocation committing AFTER the first check and BEFORE the
#      capability is returned, which Round 5 still followed with a newly issued capability;
#   2. a Store-level substitution of the record body under the CURRENT admission id, which the
#      four Round 5 checks (generation/status/project/binding) could not see at all, because every
#      one of them reads a field the substituted body itself declares.

_GRANT_RECORD_KIND = "github_projection_grant"


def _compose_over(store: Any, world: dict[str, Any]) -> Any:
    """Compose a genuine, fully admitted service over *store* -- normally a proxy wrapping
    *world*'s own real Store -- through the identical shipped composition entry point every other
    control here uses. Nothing about the admission gate is bypassed or weakened: composition runs
    its full anchor-signature and currency check against the real record, exactly as it does in
    the fixture."""

    return compose_trusted_runtime_deployment_authority(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        runtime_root_admission_ref=world["admitted"]["runtime_root_admission_ref"],
        trust_anchor_public_key_hex=trust_anchor_public_key_hex(),
    )


class _RequestBarrierStore:
    """A real Store proxy that lands one genuine canonical commit at a deterministic barrier
    *inside* one request-facing call: the moment the operation resolves its first
    ``github_projection_grant`` reference.

    Deliberately the identical shape as this suite's own established barrier stores --
    ``test_runtime_deployment_identity_anchor.py``'s ``_PointerBarrierStore`` (P15-R3-F2) and
    ``test_runtime_declaration_transition_chain.py``'s ``_CompetingSuccessorStore`` /
    ``_UnrelatedContentionStore`` -- rather than a new concurrency-simulation mechanism. Only the
    hook point differs, and it is chosen precisely: the request-facing operation Boots and runs its
    **first** admission barrier before resolving a single grant, and Boots again and runs its
    **second** barrier only after every grant, declaration and subject has been resolved and every
    Authority decision evaluated. A grant resolution therefore fires strictly between the two, and
    fires exactly once for a single-grant request.

    ``armed`` exists because composition itself resolves records through this same proxy: the
    injection must not fire while the service is still being composed, or the barrier would land
    before the first check rather than between the two. :meth:`arm` also resets the admission
    resolution counter, so ``admission_resolutions`` counts only what the request-facing call
    itself did -- which is how the positive control proves both barriers genuinely ran.
    """

    def __init__(self, delegate: Any, *, inject: Any = None) -> None:
        self._delegate = delegate
        self._inject = inject
        self.armed = False
        self.injected = False
        self.admission_resolutions = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def arm(self) -> None:
        self.armed = True
        self.admission_resolutions = 0

    def resolve_record(self, project_id: str, kind: str, record_id: str) -> Any:
        if kind == ROOT_ADMISSION_RECORD_KIND:
            self.admission_resolutions += 1
        if (
            self.armed
            and self._inject is not None
            and not self.injected
            and kind == _GRANT_RECORD_KIND
        ):
            self.injected = True
            self._inject()
        return self._delegate.resolve_record(project_id, kind, record_id)


def _rotation_barrier(
    world: dict[str, Any], *, status: str, declared_at: str, at: str
) -> tuple[_RequestBarrierStore, dict[str, Any]]:
    """Arrange a real, committed canonical rotation to land strictly between the request-facing
    operation's two admission barriers, and return the proxy Store and a mutable box the
    successor's own body is recorded in once it genuinely commits."""

    landed: dict[str, Any] = {}

    def _inject() -> None:
        landed["successor"] = _rotate(world, status=status, declared_at=declared_at, at=at)

    return _RequestBarrierStore(world["store"], inject=_inject), landed


def test_a_rotation_landing_between_the_two_barriers_returns_no_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R6-F1's decisive control, rotation half** (adopted correction item 5, first bullet).

    The service is composed normally, while A is genuinely current, and its first admission
    barrier genuinely passes. A real canonical rotation to B -- committed through the shipped
    ``commit_runtime_root_admission``, not simulated -- then lands strictly *after* that first
    barrier and strictly *before* the second, at the moment the operation resolves its first grant
    reference. Round 5 issued a capability anyway, because the capability was constructed from the
    same original Boot snapshot the first barrier had already read.

    Three things are asserted rather than assumed, so this proves a real race was exercised:
    the injection genuinely fired (``store.injected``); the rotation genuinely committed and the
    Store's own current-admission pointer now names B; and the Authority evaluation genuinely ran
    (``calls["count"] == 1``), which is what places the refusal at the *second* barrier -- the
    first one had already let the request through.

    No ``ProjectionExecutionCapability`` is returned, and the one adapter in this test is handed to
    nothing, so its call count is a literal measurement of zero adapter and zero network calls.
    """

    calls = _counting_bootstrap(monkeypatch)
    adapter = FakeGitHubAdapter()
    a_id = _canonical["admitted"]["runtime_root_admission_ref"]["id"]
    assert _admission_pointer(_canonical) == a_id

    store, landed = _rotation_barrier(
        _canonical, status="ACTIVE", declared_at="2026-09-08T05:00:00Z", at="2026-09-09T05:00:00Z"
    )
    bootstrap = _compose_over(store, _canonical)
    store.arm()

    with pytest.raises(RuntimeRequirementError) as raised:
        bootstrap(
            github_projection_grant_refs=[_canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
        )
    assert "no longer the current one" in str(raised.value), raised.value

    # The race was genuinely exercised: a real successor really committed, mid-request.
    assert store.injected, "the rotation never landed, so no race was exercised at all"
    b_id = str(landed["successor"]["runtime_root_admission_id"])
    assert _admission_pointer(_canonical) == b_id != a_id
    # ...and it landed after the FIRST barrier had already passed: the request got as far as
    # evaluating Authority, which happens only once every grant and declaration has resolved.
    assert calls["count"] == 1
    assert adapter.materialize_call_count == 0


def test_a_revocation_landing_between_the_two_barriers_returns_no_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R6-F1's decisive control, revocation half** (adopted correction item 5, second
    bullet). The identical barrier technique, with the successor committed as ``REVOKED`` instead
    of ``ACTIVE``.

    Both doors close at once here, exactly as they do at composition: the admission this service
    was composed against is no longer the one the pointer names, and what the pointer now names is
    not ``ACTIVE`` either. The refusal is on the first of those, which is the earlier requirement.
    """

    calls = _counting_bootstrap(monkeypatch)
    adapter = FakeGitHubAdapter()
    store, landed = _rotation_barrier(
        _canonical, status="REVOKED", declared_at="2026-09-08T06:00:00Z", at="2026-09-09T06:00:00Z"
    )
    bootstrap = _compose_over(store, _canonical)
    store.arm()

    with pytest.raises(RuntimeRequirementError) as raised:
        bootstrap(
            github_projection_grant_refs=[_canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
        )
    assert "no longer the current one" in str(raised.value), raised.value

    assert store.injected, "the revocation never landed, so no race was exercised at all"
    assert landed["successor"]["status"] == "REVOKED"
    assert _admission_pointer(_canonical) == str(landed["successor"]["runtime_root_admission_id"])
    assert calls["count"] == 1
    assert adapter.materialize_call_count == 0


class _SubstitutedAdmissionBodyStore:
    """A real Store proxy that substitutes a *different body* under the admission's own **current,
    unchanged** id -- the Store-level substitution P15-R6-F1's second manifestation names.

    Deliberately bypasses the canonical committer entirely: the pointer is never moved, no
    successor is ever committed, and no chain rule is exercised. This is what "an attacker who can
    write the Store's own record storage" looks like from the reading side, which is exactly the
    threat the recheck has to survive -- and it is arranged as a proxy rather than by overwriting
    the ``FileStateStore``'s own files, because that store independently detects a permanent file
    diverging from its transaction's staged copy and would refuse with its own corruption error,
    proving nothing at all about this recheck.

    ``armed`` exists so that composition itself sees, and proves, the genuine ORIGINAL record. The
    substitution begins only once a real service has been composed against the real admission.
    """

    def __init__(self, delegate: Any, *, admission_id: str, substituted: dict[str, Any]) -> None:
        self._delegate = delegate
        self._admission_id = admission_id
        self._substituted = substituted
        self.armed = False
        self.substitutions = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def resolve_record(self, project_id: str, kind: str, record_id: str) -> Any:
        if self.armed and kind == ROOT_ADMISSION_RECORD_KIND and record_id == self._admission_id:
            self.substitutions += 1
            return dict(self._substituted)
        return self._delegate.resolve_record(project_id, kind, record_id)


def test_a_record_body_substituted_under_the_current_id_issues_no_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R6-F1's second manifestation** (adopted correction items 2 and 5, third bullet):
    resolved-record integrity, not merely how the resolved record's own fields read.

    The substituted body changes exactly one adopted semantic field -- ``declared_at`` -- and
    changes nothing else. Its ``generation``, ``status``, ``project_id`` and ``project_binding_ref``
    are byte-identical to the original's, and it keeps the original's own declared
    ``runtime_root_admission_id`` and ``runtime_root_admission_semantic_fingerprint``, so the
    chain pointer still names it and it still schema-validates.

    **Why the Round 5 gate could not have caught this.** Its four requirements were: the pointer
    still names the captured id (it does -- the pointer was never moved); the resolved record
    carries the captured ``generation`` (it does -- unchanged); it is still ``ACTIVE`` (it is --
    unchanged); and it still restates this Project and Binding (it does -- unchanged). Every one of
    those reads a field the substituted body itself declares, and this substitution deliberately
    leaves all four reading exactly as before. The record's own *signature* is not re-verified by
    the per-call recheck either -- the anchor is gone by then, by design -- so nothing in Round 5
    was left that could observe the change. Composition proved the ORIGINAL record; Round 5's
    recheck never re-proved that the body now resolving is still that record.

    **What catches it now.** The recheck recomputes the resolved body's own identity and semantic
    fingerprint *from that body's actual content* and requires exact equality with the commitment
    captured at composition. ``declared_at`` is one of ``ROOT_ADMISSION_SEMANTIC_FIELDS``, so both
    recomputations move, and neither equals the captured reference. Crucially the comparison is
    against the composition-time-captured reference, never against the body's own declared
    id/fingerprint fields -- a tampered body can self-consistently declare a forged pair matching
    its own tampered content, and a self-comparison would pass it.

    The refusal happens at the FIRST barrier, before a single grant reference is resolved: zero
    authorization evaluations, and therefore zero adapter and zero network calls, measured
    literally.
    """

    calls = _counting_bootstrap(monkeypatch)
    adapter = FakeGitHubAdapter()
    original = dict(_canonical["admitted"]["runtime_root_admission"])
    admission_id = str(original["runtime_root_admission_id"])

    substituted = dict(original)
    substituted["declared_at"] = "2026-09-08T00:00:01Z"
    assert substituted != original
    # The four Round 5 requirements all still read exactly as they did before.
    for unchanged in ("generation", "status", "project_id", "project_binding_ref"):
        assert substituted[unchanged] == original[unchanged]
    # ...and so do the body's own self-declared identity and fingerprint, and its signature.
    assert substituted["runtime_root_admission_id"] == original["runtime_root_admission_id"]
    assert (
        substituted["runtime_root_admission_semantic_fingerprint"]
        == original["runtime_root_admission_semantic_fingerprint"]
    )
    assert substituted["signature"] == original["signature"]

    store = _SubstitutedAdmissionBodyStore(
        _canonical["store"], admission_id=admission_id, substituted=substituted
    )
    bootstrap = _compose_over(store, _canonical)  # composed against the genuine ORIGINAL record
    store.armed = True

    with pytest.raises(RuntimeRequirementError) as raised:
        bootstrap(
            github_projection_grant_refs=[_canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
        )
    message = str(raised.value)
    assert "own recomputed identity" in message, message
    assert "composed against" in message, message

    assert store.substitutions == 1, "the substituted body was never actually consulted"
    assert calls["count"] == 0, "refused before Authority evaluation"
    assert adapter.materialize_call_count == 0
    # The chain itself was never touched: this is a substitution, not a rotation.
    assert _admission_pointer(_canonical) == admission_id


def test_an_unchanged_current_admission_still_issues_a_working_capability(
    _canonical: dict[str, Any],
) -> None:
    """**The positive control P15-R6-F1 requires** (adopted correction item 5, fourth bullet):
    the two new checks are not vacuously always-refusing, and the second barrier does not refuse a
    request nothing happened during.

    An unmodified, still-current admission composes, issues a real capability through the identical
    proxy machinery the negative controls above use, and that capability genuinely reaches the
    controlled ``FakeGitHubAdapter`` boundary -- zero live network calls, since the fake opens
    nothing.

    Non-vacuity of the barrier itself is measured rather than assumed: the request-facing call
    resolves the current admission record **twice**, once per barrier. A single resolution would
    mean the pre-issuance barrier had quietly stopped running, and every rotation control above
    would then be proving something weaker than it claims.
    """

    store = _RequestBarrierStore(_canonical["store"])
    bootstrap = _compose_over(store, _canonical)
    bound_cells = inspect.getclosurevars(bootstrap).nonlocals
    assert (
        bound_cells["bound_semantic_fingerprint"]
        == _canonical["admitted"]["runtime_root_admission"][
            "runtime_root_admission_semantic_fingerprint"
        ]
    )
    store.arm()

    capability = bootstrap(
        github_projection_grant_refs=[_canonical["grant_ref"]],
        github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)
    assert store.admission_resolutions == 2, "the pre-issuance barrier did not run"

    adapter = FakeGitHubAdapter()
    result = capability.execute(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        projection_payload=_PAYLOAD,
        adapter=adapter,
        materialized_at="2026-09-09T00:00:00Z",
        attempt_claim_token="RUNTIME-SECOND-BARRIER-ATTEMPT-0001",  # noqa: S106
    )
    assert adapter.materialize_call_count == 1
    assert result["receipt"].status == "VERIFIED"


def test_the_issued_context_snapshots_the_final_boot_not_the_initial_one(
    _canonical: dict[str, Any],
) -> None:
    """**Adopted correction item 4**: the returned context is built from the FINAL Boot's State
    snapshot, not the one read when the request started.

    A genuinely **unrelated** State-touching commit lands at the same mid-request barrier the
    rotation controls use -- an ordinary record touching no chain at all, the identical
    unrelated-contention technique ``test_runtime_declaration_transition_chain.py``'s own
    ``_UnrelatedContentionStore`` already establishes. It bumps ``state_revision`` and rewrites
    ``semantic_fingerprint`` while moving no admission pointer whatsoever, so the request is
    legitimate throughout and a capability must still be issued: this is the distinction between
    "the world moved" and "this chain's own currency changed", and only the second may refuse.

    Before this round the context recorded the revision that was current when the request *began*,
    which is a claim about a State that was already superseded by the time the capability existed.
    It now records what was current at the moment of return.

    *Disclosed, so this control is read for exactly what it proves.* ``semantic_fingerprint`` is a
    pure function of *semantic* State, and committing a record that participates in no semantic
    claim does not move it -- so the two snapshots here differ in ``state_revision`` and agree on
    ``semantic_fingerprint``, and that agreement is asserted rather than glossed over. Both fields
    are still asserted to equal what is current at the moment of return, which is the property
    item 4 actually names; ``state_revision`` is what makes the two snapshots distinguishable at
    all, and is therefore what carries the discrimination.
    """

    def _inject() -> None:
        commit_records(
            _canonical["store"],
            _canonical["project_id"],
            _canonical["store"].load_current(_canonical["project_id"]),
            "TX-RUNTIME-BOOTSTRAP-UNRELATED-CONTENTION",
            [
                (
                    "runtime_deployment_declaration",
                    "RUNTIME-DEPLOYMENT-DECLARATION-" + "2" * 64,
                    {"note": "an unrelated record, touching no chain whatsoever"},
                )
            ],
        )

    store = _RequestBarrierStore(_canonical["store"], inject=_inject)
    bootstrap = _compose_over(store, _canonical)
    store.arm()

    at_request_start = _canonical["store"].load_current(_canonical["project_id"])
    capability = bootstrap(
        github_projection_grant_refs=[_canonical["grant_ref"]],
        github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
    )
    assert store.injected, "no unrelated State bump landed, so nothing was distinguished"

    at_return = _canonical["store"].load_current(_canonical["project_id"])
    assert at_return["state_revision"] == at_request_start["state_revision"] + 1
    # Disclosed above: an unrelated record moves the revision and not the semantic fingerprint.
    assert at_return["semantic_fingerprint"] == at_request_start["semantic_fingerprint"]

    context = capability._context
    assert context.state_revision == at_return["state_revision"]
    assert context.semantic_fingerprint == at_return["semantic_fingerprint"]
    assert context.state_revision != at_request_start["state_revision"]

    # Unrelated contention is not this chain's own currency: the admission never moved, and the
    # context still names the Human Authority the Authority evaluation actually ran against.
    assert (
        _admission_pointer(_canonical) == _canonical["admitted"]["runtime_root_admission_ref"]["id"]
    )
    assert context.github_authority_ref == _canonical["human_authority_ref"]


# ---------------------------------------------------------------------------
# P15-R7-F1: the three fields the semantic projection deliberately excludes
# ---------------------------------------------------------------------------
#
# Round 6 made both barriers recompute the resolved body's identity and semantic fingerprint and
# compare them against a composition-time commitment. Both of those recomputations are hashes of
# ``ROOT_ADMISSION_SEMANTIC_FIELDS`` -- a projection that deliberately excludes exactly three of
# the record's own fields, each for a reason that is correct where it is made: the record's own
# declared ``runtime_root_admission_id`` and its own declared
# ``runtime_root_admission_semantic_fingerprint`` (an identity cannot be computed over itself),
# and its entire ``signature`` block (a signature cannot cover its own value).
#
# Those three exclusions are precisely the surface a Store-level substitution could still aim at.
# A body whose every *semantic* field is byte-identical recomputes to exactly the bound id and the
# bound fingerprint however those three excluded fields read -- so every Round 5 and Round 6 check
# passes, and a capability is issued from a record that is no longer, in every observable respect,
# the exact anchor-verified record composition proved.
#
# The four controls below are deliberately **isolated**: each changes exactly one of those
# positions and leaves every other field -- every semantic field, and the other three positions --
# byte-identical to the genuine original. That isolation is what makes each one prove the new
# check specifically, rather than some already-existing check firing coincidentally, and it is
# asserted explicitly in the test body rather than left to the reader, exactly as Round 6's own
# ``test_a_record_body_substituted_under_the_current_id_issues_no_capability`` asserts it for its
# own ``declared_at`` substitution.

#: Every position a P15-R7-F1 substitution may aim at -- the three fields
#: ``ROOT_ADMISSION_SEMANTIC_FIELDS`` excludes, with the ``signature`` block spelled out field by
#: field so that "the other three are byte-identical" is a claim about real, named values rather
#: than about one opaque sub-object.
_EXCLUDED_FROM_THE_SEMANTIC_PROJECTION: tuple[str, ...] = (
    "runtime_root_admission_id",
    "runtime_root_admission_semantic_fingerprint",
    "signature.algorithm",
    "signature.key_id",
    "signature.value",
)


def _read(body: Mapping[str, Any], position: str) -> Any:
    """Read one dotted *position* out of *body* -- ``"signature.value"`` reaches into the
    signature block, a bare name reads a top-level field."""

    if "." in position:
        outer, inner = position.split(".", 1)
        return body[outer][inner]
    return body[position]


def _substituted_body(original: Mapping[str, Any], *, position: str, value: Any) -> dict[str, Any]:
    """Return a copy of *original* with exactly one *position* replaced by *value* and every other
    field carried across unchanged -- including the ``signature`` block's own other members, which
    are copied rather than shared so the original body cannot be mutated by accident."""

    substituted = dict(original)
    if "." in position:
        outer, inner = position.split(".", 1)
        block = dict(substituted[outer])
        block[inner] = value
        substituted[outer] = block
    else:
        substituted[position] = value
    return substituted


def _assert_isolated_to(
    substituted: Mapping[str, Any], original: Mapping[str, Any], *, changed: str
) -> None:
    """Prove, in the test's own body, that this substitution really is isolated to *changed*.

    Every one of ``ROOT_ADMISSION_SEMANTIC_FIELDS`` is byte-identical to the original's -- which
    is what makes the recomputed identity and the recomputed semantic fingerprint still equal the
    composition-time commitment, so Round 5's four checks and Round 6's two both pass -- and every
    *other* position the semantic projection excludes is byte-identical too, so the refusal that
    follows can only be attributable to this one field.
    """

    assert changed in _EXCLUDED_FROM_THE_SEMANTIC_PROJECTION, changed
    assert substituted != original, "a substitution that changes nothing proves nothing"
    for field in ROOT_ADMISSION_SEMANTIC_FIELDS:
        assert substituted[field] == original[field], field
    for position in _EXCLUDED_FROM_THE_SEMANTIC_PROJECTION:
        if position == changed:
            assert _read(substituted, position) != _read(original, position), position
        else:
            assert _read(substituted, position) == _read(original, position), position


def _refused_isolated_substitution(
    world: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    *,
    position: str,
    value: Any,
) -> str:
    """Compose a genuine service against the real ORIGINAL record, then serve an isolated
    single-field substitution under that record's own **current, unmoved** id, and return the
    refusal message.

    Reuses Round 6's own ``_SubstitutedAdmissionBodyStore`` unchanged rather than reinventing a
    substitution mechanism: its constructor already takes the substituted body whole, so an
    isolated single-field substitution is expressed by *what is handed to it*, not by a new
    parameter on it. Everything the four controls share is asserted here once -- zero authorization
    evaluations, zero adapter and therefore zero network calls, the substituted body genuinely
    consulted, and the chain pointer never touched (this is a substitution, not a rotation).
    """

    calls = _counting_bootstrap(monkeypatch)
    adapter = FakeGitHubAdapter()
    original = dict(world["admitted"]["runtime_root_admission"])
    admission_id = str(original["runtime_root_admission_id"])

    substituted = _substituted_body(original, position=position, value=value)
    _assert_isolated_to(substituted, original, changed=position)

    store = _SubstitutedAdmissionBodyStore(
        world["store"], admission_id=admission_id, substituted=substituted
    )
    bootstrap = _compose_over(store, world)  # composed against the genuine ORIGINAL record
    store.armed = True

    with pytest.raises(RuntimeRequirementError) as raised:
        bootstrap(
            github_projection_grant_refs=[world["grant_ref"]],
            github_projection_grant_declaration_refs=[world["declaration_ref"]],
        )

    assert store.substitutions == 1, "the substituted body was never actually consulted"
    assert calls["count"] == 0, "refused before Authority evaluation"
    assert adapter.materialize_call_count == 0
    assert _admission_pointer(world) == admission_id
    return str(raised.value)


def test_a_substituted_declared_admission_id_issues_no_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R7-F1, manifestation 1** (adopted correction items 2 and 4, first bullet): only the
    record's own **declared** ``runtime_root_admission_id`` is changed.

    Disclosed judgment call, since the adopted text says only "some other schema-valid string": the
    substitute keeps the canonical ``RUNTIME-ROOT-ADMISSION-`` prefix and 64 uppercase hex
    characters that ``runtime_root_admission.schema.json`` requires, so
    ``require_valid_root_admission`` genuinely passes and the refusal cannot be a schema refusal in
    disguise. ``"A" * 64`` is chosen because it is unmistakably not a digest anyone computed, and
    its inequality with the genuine id is asserted rather than assumed.

    **Why nothing before Round 7 could see this.** The recomputed id reads
    ``ROOT_ADMISSION_SEMANTIC_FIELDS``, which excludes this very field -- so the recomputation is
    byte-for-byte the composition-time commitment and Round 6's requirement 5 passes. Requirement 6
    likewise. Generation, status, Project and Binding are untouched, so Round 5's four pass. The
    signature is not reverified per call, by design. Every existing check passed a record declaring
    an identity that is not its own.

    **What catches it now.** Requirement 7: the declared id must equal the recomputed id, and both
    must equal the bound id -- a three-way equality, where Round 6 compared only recomputed against
    bound. Adding the declared field to that chain can only ever narrow what passes; it is not the
    self-comparison requirements 5 and 6 rightly refuse to rely on, because the *bound* value is
    still the anchor of the chain.
    """

    original = _canonical["admitted"]["runtime_root_admission"]
    forged_id = "RUNTIME-ROOT-ADMISSION-" + "A" * 64
    assert forged_id != original["runtime_root_admission_id"]

    message = _refused_isolated_substitution(
        _canonical, monkeypatch, position="runtime_root_admission_id", value=forged_id
    )
    assert "own declared identity" in message, message
    assert "does not equal its own recomputed identity" in message, message
    assert "substituted independently of its semantic content" in message, message


def test_a_substituted_declared_semantic_fingerprint_issues_no_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R7-F1, manifestation 2** (adopted correction items 2 and 4, second bullet): only the
    record's own **declared** ``runtime_root_admission_semantic_fingerprint`` is changed.

    Disclosed judgment call, as above: the substitute keeps the ``sha256:`` prefix and the 64
    lowercase hex characters the schema requires, so the record still schema-validates and the
    refusal is the new requirement's, not the validator's. ``"b" * 64`` is again chosen to be
    obviously not a digest anyone computed, and its inequality with the genuine value is asserted.

    The identical blind spot as manifestation 1, one field over: this field too is excluded from
    ``ROOT_ADMISSION_SEMANTIC_FIELDS``, so every Round 5 and Round 6 check reads a value it does
    not affect. Requirement 8 is the three-way declared/recomputed/bound equality for the
    fingerprint, and it is what refuses here.

    Note the ordering this control also pins: requirement 7 passes first (the declared id is
    untouched and still equals the recomputed one), so the refusal genuinely comes from
    requirement 8 and not from its neighbour.
    """

    original = _canonical["admitted"]["runtime_root_admission"]
    forged_fingerprint = "sha256:" + "b" * 64
    assert forged_fingerprint != original["runtime_root_admission_semantic_fingerprint"]

    message = _refused_isolated_substitution(
        _canonical,
        monkeypatch,
        position="runtime_root_admission_semantic_fingerprint",
        value=forged_fingerprint,
    )
    assert "own declared semantic fingerprint" in message, message
    assert "does not equal its own recomputed semantic fingerprint" in message, message
    # ...and not its neighbour: the declared id was untouched, so requirement 7 passed first.
    assert "own declared identity" not in message, message


def test_a_substituted_signature_value_issues_no_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R7-F1, manifestation 3** (adopted correction items 2 and 4, third bullet), and **the
    control that actually proves the full-record commitment does real work**.

    Only ``signature.value`` changes. The signature block is invisible to *every* other check in
    this function: it is excluded from ``ROOT_ADMISSION_SEMANTIC_FIELDS`` (a signature cannot cover
    its own value), so neither recomputation moves; it is not one of the four fields Round 5 reads;
    and it is not reverified per call at all, because the trust anchor is deliberately gone by then
    -- discarded at composition and absent from every request-facing signature. So requirements 1-8
    all pass, including both of Round 7's own declared-versus-recomputed checks, and requirement 9
    is the only thing left that can see the change.

    That is exactly why this control, rather than the two above it, is what establishes the
    full-record commitment as a genuine addition instead of a restatement of the other two.

    Disclosed judgment call: the substitute is ``"c" * 128``, which satisfies the schema's own
    ``^[0-9a-f]{128}$`` signature-value pattern -- so the record is still fully schema-valid and
    still resolves -- while being a value no Ed25519 signing operation would ever produce. The
    point is precisely that the refusal happens *without* anyone verifying the signature: nothing
    here asks whether ``"c" * 128`` is a valid signature, only whether the record is still the
    exact record composition proved.
    """

    original = _canonical["admitted"]["runtime_root_admission"]
    forged_value = "c" * 128
    assert forged_value != original["signature"]["value"]
    assert len(original["signature"]["value"]) == len(forged_value)

    message = _refused_isolated_substitution(
        _canonical, monkeypatch, position="signature.value", value=forged_value
    )
    assert "own full-record commitment" in message, message
    assert "captured at composition" in message, message
    assert "potentially including its signature" in message, message
    # Decisively not one of the narrower checks: both of those passed on this body.
    assert "own declared identity" not in message, message
    assert "own declared semantic fingerprint" not in message, message


def test_a_substituted_signature_key_id_issues_no_capability(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """**P15-R7-F1, manifestation 4** (adopted correction item 4, fourth bullet): the identical
    shape as manifestation 3, aimed at ``signature.key_id`` instead of ``signature.value``.

    It is kept as its own control rather than folded into the one above because the two say
    different things about what a substitution could achieve. Replacing the value re-writes *the
    signature*; replacing the key id re-writes *whose signature this claims to be* -- a record that
    still carries the anchor's own genuine signature bytes while naming an entirely different
    signing key. Both are refused by requirement 9, and neither is visible to anything narrower.

    Disclosed judgment call: the substitute is ``"TRUST-ANCHOR-0002"``, which satisfies
    ``common/identity.schema.json``'s own canonical identity grammar (leading uppercase letter,
    uppercase alphanumeric segments, at least one hyphen) exactly as the genuine
    ``"TRUST-ANCHOR-0001"`` does, so the record remains schema-valid and the refusal is
    requirement 9's alone.
    """

    original = _canonical["admitted"]["runtime_root_admission"]
    forged_key_id = "TRUST-ANCHOR-0002"
    assert forged_key_id != original["signature"]["key_id"]

    message = _refused_isolated_substitution(
        _canonical, monkeypatch, position="signature.key_id", value=forged_key_id
    )
    assert "own full-record commitment" in message, message
    assert "captured at composition" in message, message
    assert "own declared identity" not in message, message
    assert "own declared semantic fingerprint" not in message, message


def test_the_composed_service_binds_the_exact_full_record_commitment(
    _canonical: dict[str, Any],
) -> None:
    """**P15-R7-F1, item 1**, and the non-vacuity control for all four substitutions above.

    Composition captures a *fourth* cell beside the three Rounds 5 and 6 established, and it is
    genuinely a commitment to the **exact full record** rather than to the semantic projection the
    other three come from. Three things are proved here rather than assumed:

    1. all four cells exist, and the three earlier ones are unchanged -- Round 7 adds, it does not
       replace;
    2. the new cell equals a digest recomputed here, independently, over the genuine admission body
       through the repository's own single canonical serialization owner -- so the value is the
       record's, not an artefact of how it was captured;
    3. it is genuinely **broader** than ``bound_semantic_fingerprint``: changing any one of the
       three fields the semantic projection excludes moves the full-record commitment and leaves
       the semantic fingerprint exactly where it was. That inequality is the whole finding, stated
       as an arithmetic fact about the two digests rather than as a claim about the barriers.

    And, still: no raw trust anchor is reachable from the composed service. A record carries a
    signature, never a key, so committing to the full record reintroduces nothing.
    """

    admission = dict(_canonical["admitted"]["runtime_root_admission"])
    bootstrap = _canonical["admitted"]["bootstrap"]
    cells = inspect.getclosurevars(bootstrap).nonlocals

    expected = "sha256:" + hashlib.sha256(canonical_json_bytes(dict(admission))).hexdigest()
    assert cells["bound_full_record_commitment"] == expected
    assert cells["bound_admission_id"] == admission["runtime_root_admission_id"]
    assert cells["bound_generation"] == int(admission["generation"])
    assert (
        cells["bound_semantic_fingerprint"]
        == admission["runtime_root_admission_semantic_fingerprint"]
    )
    assert cells["bound_full_record_commitment"] != cells["bound_semantic_fingerprint"]

    # Broader than the semantic fingerprint, proved field by field over exactly the three positions
    # ROOT_ADMISSION_SEMANTIC_FIELDS excludes.
    for position, value in (
        ("runtime_root_admission_id", "RUNTIME-ROOT-ADMISSION-" + "A" * 64),
        ("runtime_root_admission_semantic_fingerprint", "sha256:" + "b" * 64),
        ("signature.value", "c" * 128),
        ("signature.key_id", "TRUST-ANCHOR-0002"),
    ):
        substituted = _substituted_body(admission, position=position, value=value)
        moved = "sha256:" + hashlib.sha256(canonical_json_bytes(substituted)).hexdigest()
        assert moved != cells["bound_full_record_commitment"], position
        # ...while the narrower, semantic-fields-only digest does not move at all.
        assert (
            runtime_root_admission_semantic_fingerprint(substituted)
            == cells["bound_semantic_fingerprint"]
        ), position

    anchor = trust_anchor_public_key_hex()
    assert not any(anchor in text for text in _reachable_strings(bootstrap))
