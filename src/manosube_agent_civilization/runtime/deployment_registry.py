"""The canonical current-deployment-declaration pointer, and the one sanctioned way to move it
(Phase 15 Structural Review Round 3, Issue #64, P15-R3-F2; rebuilt onto a monotonic, signed
transition chain by Round 4, P15-R4-F2).

**The Round 3 defect this module closed, restated.** Round 2 made a
``runtime_deployment_declaration`` signed, status-bound, and cross-checked against the Human
Authority the observing call's own Boot restored. But the record is immutable and
content-addressed, so minting a *new* record carrying ``status="REVOKED"`` never invalidated the
original ``ACTIVE`` one: that record keeps its own unchanged id and stays individually
resolvable, individually signature-valid, and individually schema-valid forever. "Current"
therefore stopped meaning *whatever the caller happens to reference* and started meaning
*whatever Project State's own pointer currently names*:

```text
semantic_state.runtime.claims[<target_key>]  ->  runtime_deployment_declaration_id
```

**The Round 4 defect this module now closes.** Round 3's pointer moved on *any* new declaration
for the target, with no ordering claim of any kind. That left the pointer freely re-pointable in
both directions:

```text
A(ACTIVE) -> B(REVOKED)    a genuine revocation                                     intended
B(REVOKED) -> A(ACTIVE)    replaying the ancestor A moved the pointer straight back  ACCEPTED,
                           and un-revoked a revoked deployment target                and wrong
```

Nothing in Round 3 said a declaration had to name what it replaced, so an already-issued,
already-signed, still-individually-valid ancestor could be re-committed at any later time and
would silently become current again -- and two rotations racing each other could interleave into
whichever order the Store happened to see last. Round 4 makes a declaration's own place in its
target's history a **signed** claim: ``generation`` and ``predecessor_ref`` are now required
fields that participate in the record's own content address, its own semantic fingerprint, and
the Human Authority's own signature over it (see
:data:`~manosube_agent_civilization.runtime.identity.DEPLOYMENT_DECLARATION_SEMANTIC_FIELDS`), and
this committer admits only a legal transition:

```text
genesis      generation=0, predecessor_ref=null, only when the target has no current declaration
successor    generation=current+1 and predecessor_ref naming the EXACT current declaration id
rotation     an ACTIVE successor replacing an ACTIVE current, through the successor rule alone
revocation   a REVOKED successor naming the exact current declaration -- TERMINAL for that target
replay       proposing the already-current declaration is an idempotent no-op, not a transition
```

**The rules themselves are not restated here.** They live in
:mod:`~manosube_agent_civilization.runtime.transition_chain`, the one shared mechanism this
package owns, which the ``runtime_root_admission`` chain (P15-R4-F1) parameterizes in exactly the
same way. This module contributes only what is genuinely specific to a deployment declaration:
its :data:`DEPLOYMENT_DECLARATION_CHAIN`, and the verification below.

**Why this committer now Boots and verifies the Human Authority signature, when Round 3's own
docstring argued against exactly that.** Round 3's committer deliberately skipped signature
verification, on the reasoning that
:func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` re-checks it fresh at
observation time and a second copy could drift into a different notion of "an acceptable
declaration". That reasoning rested on a premise Round 4 removes: Round 3's committer had **no
transition legality to gate at all** -- every declaration simply overwrote the pointer -- so
verifying a signature there would genuinely have bought nothing. Now the committer decides
whether a proposed record may *move the chain*, and it cannot make that decision honestly while
being unable to tell a genuine Human Authority statement from an unsigned or wrongly-signed one.
So the verification exists at two moments, deliberately, for two different questions:

```text
AT COMMIT TIME (here)          may this proposal move this target's own pointer at all?
                               -> fresh Boot, signature verified against the Boot-restored key,
                                  BEFORE any generation/predecessor legality is even considered.

AT OBSERVATION TIME (route.py) may this declaration be trusted to anchor an observation NOW,
                               possibly much later, possibly after a legitimate Human Authority
                               re-binding? -> that call's OWN fresh Boot, its own signature check,
                               its own ACTIVE requirement, its own validity window, its own
                               currency check -- all unchanged and all still required.
```

Neither subsumes the other: a declaration committed under authority X remains committed, while an
observation made after a re-binding to authority Y must refuse it. Round 3's drift concern is
answered by both sites calling the identical
:func:`~manosube_agent_civilization.runtime.deployment_declaration.
verify_runtime_deployment_declaration_signature` over the identical
:func:`~manosube_agent_civilization.runtime.identity.
runtime_deployment_declaration_signing_payload` bytes, rather than by one of them not looking.

**This module is still not a second State owner.** It builds no transition plan of its own and
never touches the Store's committer directly; the shared mechanism does, exactly once, for both
chains. It evaluates no Closure, mints no Authority, derives no Difference/Change/Evidence
content, and holds no key: it persists one already-issued, already-signed Human Authority
statement and the pointer that says which one is current.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.boot import boot_project

from .deployment_declaration import verify_runtime_deployment_declaration_signature
from .engine import require_valid_deployment_declaration
from .errors import RuntimeRequirementError
from .identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_deployment_target_key,
)
from .transition_chain import (
    MonotonicChainSpec,
    commit_chain_transition,
    current_chain_record_id,
)

#: The canonical Store record kind this module commits, and the one
#: :mod:`~manosube_agent_civilization.runtime.route` resolves -- stated once, here, so the two
#: sites can never drift.
DEPLOYMENT_DECLARATION_RECORD_KIND = "runtime_deployment_declaration"

#: Where the current-declaration pointer lives inside Project State. Re-exported unchanged from
#: the shared mechanism so Round 3's own names keep working and there is still exactly one
#: definition of where a pointer lives.
DEPLOYMENT_POINTER_SEMANTIC_DOMAIN = "runtime"
DEPLOYMENT_POINTER_CLAIMS_FIELD = "claims"

#: Everything about a ``runtime_deployment_declaration`` the shared monotonic-chain mechanism
#: needs, and nothing else. The chain *rules* live there; only these bindings live here.
DEPLOYMENT_DECLARATION_CHAIN = MonotonicChainSpec(
    record_kind=DEPLOYMENT_DECLARATION_RECORD_KIND,
    id_field="runtime_deployment_declaration_id",
    semantic_fingerprint_field="runtime_deployment_declaration_semantic_fingerprint",
    require_valid=require_valid_deployment_declaration,
    recompute_id=runtime_deployment_declaration_id,
    recompute_semantic_fingerprint=runtime_deployment_declaration_semantic_fingerprint,
    chain_key_of=runtime_deployment_target_key,
)


def current_deployment_declaration_id(
    current_state: Mapping[str, Any], target_key: str
) -> str | None:
    """Return the ``runtime_deployment_declaration_id`` *current_state*'s own canonical pointer
    names for *target_key*, or ``None`` when no declaration has ever been made current for that
    target through :func:`commit_runtime_deployment_declaration`.

    A pure read over the shared pointer mechanism -- no Store I/O, no resolution, no verification.
    Kept as this module's own name because ``route.py`` reads the pointer through it and should
    not have to know that a second chain kind shares the same map.
    """

    return current_chain_record_id(current_state, target_key)


def _require_declaration_shape_and_signature(
    store: Any, project_id: str, declaration: Mapping[str, Any]
) -> None:
    """Freshly Boot *project_id* and prove *declaration* was genuinely issued by the Human
    Authority that Boot restores -- before any transition legality is considered at all.

    Called once per commit attempt by the shared mechanism, against the State that attempt
    actually loaded, so a commit can never land under an authority that changed while this call
    was contending (the identical per-attempt discipline P15-R1-F5 established for ``route.py``).

    Four requirements, in order:

    1. The declaration's own ``project_binding_ref`` must name a Project Binding that genuinely
       Boots for this project -- so a declaration cannot be committed against a Binding that does
       not exist, or that this project never adopted.
    2. Its ``human_authority_ref`` must equal the one that Boot just restored.
    3. Its ``signature`` must genuinely verify against the ``human_authority_signing_key`` that
       same Boot restored from the current Project Binding -- never a caller-supplied copy, never
       a key read from the declaration itself.
    4. Its validity window must be genuinely ordered (``valid_from <= valid_until``). The window
       is *not* evaluated against a clock here: this module reads none, and whether an
       already-committed declaration is in-window at some later instant is
       :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`'s own question,
       asked against that observation's own ``observed_at``.
    """

    binding_ref = declaration.get("project_binding_ref")
    binding_id = binding_ref.get("id") if isinstance(binding_ref, Mapping) else None
    if not isinstance(binding_id, str) or not binding_id:
        raise RuntimeRequirementError(
            "runtime_deployment_declaration carries no readable project_binding_ref.id -- "
            f"refusing to commit it: {binding_ref!r}"
        )
    boot_context = boot_project(store, project_id=project_id, project_binding_id=binding_id)
    signing_key = boot_context.project_binding.get("human_authority_signing_key")
    if not isinstance(signing_key, Mapping):
        raise RuntimeRequirementError(
            "the Boot-restored project_binding carries no readable human_authority_signing_key"
        )
    if declaration.get("human_authority_ref") != dict(boot_context.human_authority_ref):
        raise RuntimeRequirementError(
            "runtime_deployment_declaration own human_authority_ref does not name the Human "
            "Authority this commit's own Boot just restored: "
            f"{declaration.get('human_authority_ref')!r} != "
            f"{dict(boot_context.human_authority_ref)!r} -- refusing to move this target's own "
            "current-declaration pointer under an authority that is not in force"
        )
    if not verify_runtime_deployment_declaration_signature(
        dict(declaration), signing_key=dict(signing_key)
    ):
        raise RuntimeRequirementError(
            "runtime_deployment_declaration carries no genuine Human Authority signature over "
            "its own adopted semantic fields -- verified against the human_authority_signing_key "
            "this commit's own Boot restored from the current Project Binding. An unsigned, "
            "self-authored, wrong-key, or stale-key declaration may never move a chain: its own "
            "generation and predecessor_ref are part of what that signature covers"
        )
    valid_from = declaration.get("valid_from")
    valid_until = declaration.get("valid_until")
    if not isinstance(valid_from, str) or not isinstance(valid_until, str):
        raise RuntimeRequirementError(
            "runtime_deployment_declaration carries no readable validity window: "
            f"{valid_from!r} .. {valid_until!r}"
        )
    if valid_from > valid_until:
        raise RuntimeRequirementError(
            f"runtime_deployment_declaration own validity window is not genuinely ordered "
            f"({valid_from!r} .. {valid_until!r}) -- refusing to commit it"
        )


def commit_runtime_deployment_declaration(
    store: Any,
    project_id: str,
    declaration: Mapping[str, Any],
    *,
    committed_at: str,
) -> dict[str, Any]:
    """Commit *declaration* **and** make it the current declaration for its own target, in one
    atomic :func:`~manosube_agent_civilization.store.commit.commit_state_transition` call --
    if, and only if, it is a legal monotonic transition from whatever is current right now
    (P15-R3-F2, P15-R4-F2).

    *declaration* must already be a real, complete, Human-Authority-signed record. This function
    proves it schema-valid, independently recomputes its own content address and semantic
    fingerprint, freshly Boots the project and verifies its signature against that Boot-restored
    key, and then requires the transition itself to be legal -- genesis, or a successor whose own
    signed ``generation``/``predecessor_ref`` name exactly the head this chain currently has. It
    **never signs, mints, or repairs anything**: it holds no key and adds no field.

    ```text
    A(ACTIVE, g=0) -> B(REVOKED, g=1, pred=A)     revocation; TERMINAL for this target
    replay A afterwards                            refused; the pointer stays at B
    A(ACTIVE, g=0) -> B(ACTIVE, g=1, pred=A)      rotation
    replay A afterwards                            refused; the pointer stays at B
    proposing B again while B is current           idempotent no-op; no transition, no commit
    two successors racing from the same head       at most one wins; the loser re-evaluates
                                                   against the new head and FAILS CLOSED
    ```

    Returns ``{"runtime_deployment_declaration_ref", "runtime_deployment_target_key",
    "generation", "transition", "committed_state"}``. ``transition`` is ``"GENESIS"``,
    ``"SUCCESSOR"``, or ``"IDEMPOTENT_REPLAY"``; ``committed_state`` is ``None`` for the last of
    those, because nothing was committed.

    *committed_at* is required and caller-supplied: this module reads no clock, the identical
    discipline every other route and committer in this repository already keeps.
    """

    def verify(checked: dict[str, Any], _current_state: Mapping[str, Any]) -> None:
        _require_declaration_shape_and_signature(store, project_id, checked)

    result = commit_chain_transition(
        store,
        project_id,
        declaration,
        spec=DEPLOYMENT_DECLARATION_CHAIN,
        committed_at=committed_at,
        verify=verify,
    )
    return {
        "runtime_deployment_declaration_ref": result["record_ref"],
        "runtime_deployment_target_key": result["chain_key"],
        "generation": result["generation"],
        "transition": result["transition"],
        "committed_state": result["committed_state"],
    }


__all__ = [
    "DEPLOYMENT_DECLARATION_CHAIN",
    "DEPLOYMENT_DECLARATION_RECORD_KIND",
    "commit_runtime_deployment_declaration",
    "current_deployment_declaration_id",
]
