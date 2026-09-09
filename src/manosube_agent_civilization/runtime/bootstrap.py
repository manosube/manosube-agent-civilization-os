"""The trusted runtime bootstrap: production Phase 14 capability provisioning (Phase 15, Issue
#64, V5).

Structural Review Round 12/13 of Phase 14 (Issue #62, P14-R12-F1, P14-R13-F1/F2) drew the
Phase 14/Phase 15 boundary at a formal execution *interface* -- :class:`~manosube_agent_civilization.
projection.ProjectionExecutionCapability`, consuming an already-resolved, opaque
:class:`~manosube_agent_civilization.projection.ProjectionExecutionContext` -- while explicitly
deferring *provisioning* that context from canonical Store/Boot state to Phase 15. This module
is that deferred provisioning: the request-facing operation
:func:`compose_trusted_runtime_deployment_authority` returns is a
production-general adaptation of Phase 14's own V3 test-fixture layer's live-write-authority
resolver (``tests/fixtures/`` -- deliberately not named literally here; see this package's own
static conformance test, which forbids this shipped module from naming that test-only module
even in prose) -- the identical Store-resolve/identity-recompute/
``evaluate_projection_authorization``-once/one-grant-one-declaration-per-kind discipline,
reused rather than reinvented -- with two deliberate differences appropriate to shipped
production code rather than a test-only live-write gate:

- **Dynamic kind set.** The V3 fixture requires exactly the three fixed kinds in its own
  ``V3_PROJECTION_KINDS``. A real deployment may authorize any subset of the closed
  :data:`~manosube_agent_civilization.projection.types.PROJECTION_KINDS` vocabulary a caller's
  own supplied grant references actually name -- the request-facing operation derives the kind
  set from the resolved grants themselves, never a fixed constant.
- **Raises rather than returns ``None``.** The V3 fixture is deliberately a fail-closed gate
  that *never raises*, appropriate to a test harness deciding whether to attempt a live write at
  all. This function is an ordinary production route, like every other canonical route in this
  repository (``boot.boot_project``, ``projection.route.project_to_github``): both halves raise
  :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` (or lets
  ``boot_project``'s/``evaluate_projection_authorization``'s own errors propagate unchanged) on
  any refusal, so a real caller can see *why* provisioning failed.

**Structural Review Round 7 (P15-R7-F1): the per-call barriers now commit to the EXACT FULL
RECORD, not only to a projection of it. Read this before reading the diff.** *(Round 7 keeps
Round 5's closure boundary, Round 6's two-barrier placement and the transition-chain mechanism
entirely, and changes only what each barrier proves.)*

Round 6 made both barriers recompute the resolved body's identity and semantic fingerprint and
compare them against a composition-time commitment. Both of those recomputations are hashes of
``ROOT_ADMISSION_SEMANTIC_FIELDS`` -- and that projection deliberately excludes exactly three of
the record's own fields, for reasons that are correct where they are made: a record's own declared
``runtime_root_admission_id`` and its own declared
``runtime_root_admission_semantic_fingerprint`` (an identity cannot be computed over itself), and
its entire ``signature`` block (a signature cannot cover its own value). Round 7 found those three
exclusions to be precisely the surface a Store-level substitution could still aim at:

```text
change ONLY the declared runtime_root_admission_id to another schema-valid id string
change ONLY the declared runtime_root_admission_semantic_fingerprint to another schema-valid one
change ONLY signature.value (or signature.key_id), keeping a schema-valid shape

    -> require_valid_root_admission passes (shape only)
    -> generation / status / project / binding are untouched, so Round 5's four checks pass
    -> the RECOMPUTED id and fingerprint read the semantic fields, which are untouched, so they
       still equal the composition-time commitment and Round 6's two checks pass
    -> a capability is issued from a record that is no longer, in every observable respect, the
       exact anchor-verified record admitted at composition
```

The correction is one narrow addition, entirely inside this module:

```text
AT COMPOSITION      alongside bound_admission_id / bound_generation /
                    bound_semantic_fingerprint (all three kept), capture
                    bound_full_record_commitment -- a deterministic digest of the EXACT full,
                    schema-valid, anchor-verified record, via this repository's one canonical
                    serialization owner (`state.canonicalize.canonical_json_bytes`, the same
                    function `identity.py` reads for every one of its own derivations). It
                    retains no anchor and reintroduces none.

AT EACH BARRIER     three further requirements, after the existing six and in the established
                    "recompute-and-compare last" order: the resolved record's DECLARED id must
                    equal its RECOMPUTED id and both must equal the BOUND id (three-way, where
                    Round 6 compared only recomputed against bound); the same three-way equality
                    for the semantic fingerprint; and the full-record commitment -- including
                    signature.algorithm, signature.key_id and signature.value -- must equal the
                    composition-time one. NINE requirements now, not six.
```

The request-facing signature is **unchanged again**: still exactly ``github_projection_grant_refs``
and ``github_projection_grant_declaration_refs``, and no new public request parameter of any kind.

**Structural Review Round 6 (P15-R6-F1): the per-call admission recheck runs TWICE -- the second
time immediately before issuance -- and re-establishes the resolved record's *integrity*, not just
how its own fields read. Read this before reading the diff.** *(Round 7 keeps this entirely and
extends only what each barrier proves.)*

Round 5 put one admission barrier at the start of every request-facing call. Round 6 found that
barrier open in two independently reproducible ways, and closes both without changing Round 5's
closure boundary or its timestamp owner:

```text
1. POST-CHECK ROTATION/REVOCATION RACE
   The check ran once, at the start of the request. Grants, declarations and subjects were then
   resolved and every Authority decision evaluated -- real work, taking real time -- and the
   capability was finally built from that SAME ORIGINAL Boot snapshot, with no second barrier.
   A canonical rotation or revocation committing in that window was therefore still followed by a
   newly issued capability, which directly violates the adopted condition that rotation and
   revocation prevent NEW capability issuance.

2. RESOLVED-RECORD INTEGRITY WAS NEVER RE-ESTABLISHED
   The recheck schema-validated the resolved record and then read four of its own self-declared
   fields (generation, status, project_id, project_binding_ref). It never recomputed
   `runtime_root_admission_id` or the semantic fingerprint from the resolved body, and never
   compared that body against the admission admitted at composition. A Store-level substitution
   under the CURRENT id -- an altered `predecessor_ref`, `declared_at` or `signature`, with those
   four fields left exactly as they were -- therefore passed the whole gate. Composition proved
   the ORIGINAL record; the recheck only ever re-proved that certain fields still read a
   particular way.
```

The correction is one bounded forward change, entirely inside this module:

```text
AT COMPOSITION      capture an immutable canonical commitment to the exact anchor-verified
                    admission: its id, its generation, AND its independently recomputed semantic
                    fingerprint (`bound_semantic_fingerprint`, beside the two cells Round 5
                    already held).

ON EVERY REQUEST    _require_bound_admission_still_current now recomputes the currently-resolved
                    record's identity and semantic fingerprint FROM ITS BODY and requires exact
                    equality with that captured commitment -- never with the body's own declared
                    id/fingerprint fields, since a tampered body can declare a forged pair
                    matching its own tampered content and satisfy a self-comparison trivially.
                    Six requirements now, not four.

BEFORE ISSUANCE     after ALL grant/declaration/subject resolution and Authority evaluation, and
                    immediately before the capability is constructed, the operation Boots AGAIN
                    and repeats the FULL check -- identity, fingerprint, generation, status,
                    Project/Binding, all of it. The returned ProjectionExecutionContext's
                    `state_revision`/`semantic_fingerprint` come from that FINAL Boot.
```

*Disclosed judgment call.* Only the **State snapshot** moves to the final Boot.
``human_authority_ref``/``human_authority_signing_key`` -- and therefore the ``decisions``,
``authorities`` and the context's own ``github_authority_ref`` -- remain sourced from the first
Boot, exactly as before, because they are what the Authority evaluation actually ran against and
what the returned capability legitimately represents. Re-deriving them from a later Boot would let
the context claim it was authorized under a Human Authority binding no evaluation ever used, if a
re-binding landed between the two Boots -- a strictly worse defect than the one being closed.

The request-facing signature is **unchanged**: still exactly ``github_projection_grant_refs`` and
``github_projection_grant_declaration_refs``, with no Store, Project, Binding, admission, anchor
or replacement authority object anywhere on it, and no new public request parameter of any kind.

**Structural Review Round 5 (P15-R5-F1, P15-R5-F2): the composition step *returns the bound
request-facing operation itself*, and every new capability issuance rechecks the bound
admission's currency. Read this before reading the diff.** *(Round 6 keeps this entirely and
extends only what the per-call recheck proves, and how many times it runs.)*

*P15-R5-F1 -- the ownership boundary needed a control that is not a type check.* Round 4 moved
every trust-deciding value onto a composition step and handed request-facing code an opaque
``RuntimeDeploymentAuthority``. Round 5 found the boundary still open in one respect: that
authority was an ordinary public frozen dataclass with an ordinary public constructor, and the
request-facing function was a free module-level function whose only defence was an ``isinstance``
check. Any caller able to import this module could therefore construct their **own** authority
over an alternate Store/Project/Binding and hand it straight in:

```python
bootstrap_projection_execution_capability(
    RuntimeDeploymentAuthority(attacker_store, attacker_project, attacker_binding, ...),
    github_projection_grant_refs=[...],
    github_projection_grant_declaration_refs=[...],
)  # a genuine instance of the right type, over an entirely alternate world
```

Making that function a *method* on the same public dataclass would not have closed it either --
a caller can still construct their own instance and call the method on it -- and the review
explicitly rules out a sentinel, a leading-underscore field, a private constructor, an opaque
``repr``, and an ``isinstance`` check as the trust control.

So the type is **deleted**, and the request-facing operation is a genuine Python closure:

```text
compose_trusted_runtime_deployment_authority(store, *, project_id, project_binding_id,
                                             runtime_root_admission_ref,
                                             trust_anchor_public_key_hex)
    -> the request-facing callable ITSELF, defined inside this call's own frame, holding the
       canonical Store, Project, Binding and admitted admission id/generation in closure cells

<returned callable>(*, github_projection_grant_refs, github_projection_grant_declaration_refs)
    -> ProjectionExecutionCapability
```

A closure is not a class. It has **no public constructor**, so there is nothing a caller can
call to fabricate an equivalent operation over an alternate world; the only way to obtain a
working one is to call the composition step, and the composition step runs the full
anchor-signature and currency admission gate (:func:`_require_currently_admitted`, unchanged from
Round 4) before the closure exists at all. The control is not "we check what you passed" but
"deployment composition chose and closed over the authority before the request boundary existed".

*P15-R5-F2 -- currency is now rechecked before every new capability issuance.* Round 4 disclosed
that an already-composed authority behaved like a cached credential: the anchor was verified once
and never again, so a rotation or revocation bound only the *next* composition. Round 5 narrows
that -- without contradicting it -- by separating two genuinely different questions, exactly as
``deployment_registry.py``'s own docstring already separates signature-verification-at-commit
from currency-at-observation:

```text
IS THE ANCHOR STILL THE RIGHT ANCHOR?    still asked exactly once, at composition. The raw anchor
                                         remains absent from every request-facing signature and is
                                         never re-verified per call -- which is what the adopted
                                         contract's "closed over afterward" wording requires.

IS THE ADMISSION THIS SERVICE WAS        now asked FRESHLY ON EVERY CALL, from the canonical
COMPOSED AGAINST STILL THE CURRENT ONE?  Store's own current-admission pointer plus the retained
                                         admission id and generation. No anchor is needed for it:
                                         the record is immutable and content-addressed, and the
                                         pointer is moved only by the anchor-signature-gated
                                         `commit_runtime_root_admission`.
```

:func:`_require_bound_admission_still_current` is that recheck. It runs before any grant is
resolved, before any authorization is evaluated, and therefore before any adapter or network call
could exist, so a rotated or revoked composition authority mints **no new** capability at zero
cost. Capabilities already issued from that service before the rotation are deliberately *not*
retroactively revoked -- the adopted boundary is prevention of new issuance, and that limit is
stated rather than quietly widened.

*Scope, disclosed.* This is a control over *call shapes and obtainability*, not over in-process
memory. Python offers no way to stop code that already holds the returned function object from
rewriting its own closure cells (``__closure__[i].cell_contents``), exactly as nothing stopped
Round 4's frozen dataclass from being rewritten through ``object.__setattr__``. What changed, and
what the decisive controls measure, is that no *call* can name an alternate world and no *public
constructor* can fabricate an equivalent service.

**Structural Review Round 4 (P15-R4-F1): the trust anchor is owned by a composition step, and
never appears on a request-facing signature at all.** *(Round 5 keeps this boundary entirely and
changes only how it is carried: the opaque value type below is replaced by the closure described
above, and the "cached capability" consequence is narrowed by the per-call currency recheck.)*

Round 4 found that Rounds 1-3 had moved the same defect rather than closed it. Round 3's own
correction made `bootstrap_projection_execution_capability` require an admission record verified
against a ``trust_anchor_public_key_hex`` -- but it required that key **as a parameter of the
request-facing call itself**, and took the admission reference as a parameter too. A caller who
could reach that function could therefore still present a complete, internally self-consistent
alternate world *together with the matching attacker anchor*, and every check would pass: the
alternate Store resolves the alternate admission, the alternate admission is genuinely signed by
the alternate anchor, and the function had no way to know which anchor the deployment actually
configured, because the caller supplied that too.

The correction is an ownership boundary, not another check:

```text
TRUSTED_DEPLOYMENT_COMPOSITION   owns the canonical Store handle, project_id,
                                 project_binding_id, the root-admission selection, and the
                                 configured trust-anchor public key. It runs ONCE, before any
                                 request boundary exists.

REQUEST_FACING_BOOTSTRAP         may supply operation-scoped references only -- grants and grant
                                 declarations. It MUST NOT be able to supply or replace the
                                 Store, the Project, the Binding, the anchor, the admission, or
                                 the Human Authority key, and after this round it structurally
                                 cannot: no such parameter exists on its signature.
```

`compose_trusted_runtime_deployment_authority` is that composition step and is the only shipped
function through which a bound request-facing bootstrap can be obtained (Round 4 carried that
binding as an opaque ``RuntimeDeploymentAuthority`` value; Round 5 carries it as the returned
closure itself). It performs every
one of Round 3's admission checks -- resolve, schema-validate, identity-recompute,
fingerprint-recompute, require ACTIVE, require the exact project and Binding, verify the
signature against the deployment-configured anchor -- plus Round 4's own currency requirement
(§13.2: the presented admission must be the one this Project Binding's own admission chain
pointer *currently* names, so a rotated or revoked admission cannot be replayed through its own
still-resolvable reference). It then closes over the result and **discards the raw anchor**: the
anchor value is not retained on the authority, is not reachable from it, and appears nowhere in
its state.

`bootstrap_projection_execution_capability` consumes that already-bound authority. Its signature
carries no ``store``, no ``project_id``, no ``project_binding_id``, no
``trust_anchor_public_key_hex``, and no ``runtime_root_admission_ref`` -- proved by
``inspect.signature`` in ``tests/contract/runtime/test_runtime_static_conformance.py``, not by
eye. There is no call shape through which an alternate world can be substituted into it.

*The disclosed consequence of "closed over afterward".* Because composition Boots and verifies
the anchor exactly once, an already-composed authority stays usable until whoever holds it stops
using it or recomposes -- even if the admission is rotated or revoked afterwards. That is exactly
how a cached credential or capability token behaves in any real system, and it is the direct
consequence of the adopted contract's own wording: the anchor is "closed over afterward" and
"absent from every request-facing execution signature", which rules out per-request
re-verification. Rotation and revocation therefore bind the next composition, not an authority a
deployment already holds. See ``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.5, item 1.

`TrustedRuntimeRoot` is **removed**, not kept beside the new type. It existed only to name a
world, and naming a world is now composition's own job; leaving an inert value behind would give
a future reader two handles with one purpose. Round 2's and Round 3's own static facts survive in
strictly stronger form: the deleted Round 1 minting factory is still absent by name, and the
`TrustedRuntimeRoot` name is now absent from shipped code entirely. Round 5 applies that same
precedent to Round 4's own type: `RuntimeDeploymentAuthority` is deleted rather than kept beside
the closure that replaced it, and its name is likewise absent from every shipped code position.

**Structural Review Round 1 (P15-R1-F4): the trust root is a type, not a parameter list.**
As first delivered, the request-facing ``bootstrap_projection_execution_capability`` took
``store``,
``project_id``, and ``project_binding_id`` as its own free parameters and proved only that the
world *inside* that caller-selected Store was internally self-consistent. That is not a
control: an attacker can assemble an entirely separate Store -- its own Human Authority signing
key, its own project_binding, its own grants, declarations, and subjects, every one of them
genuinely valid on its own terms -- hand it in, and receive a real
:class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability`, because nothing
in the function's own signature distinguished "the canonical adopted Store" from "any
internally consistent Store a caller happens to pass". Adding an environment digest, a
hardcoded repository key, or any other anchor a caller can also select would only move the
same problem one level out.

Round 1's correction was structural rather than evidential: provisioning became two steps, and
the request-facing ``bootstrap_projection_execution_capability`` lost *every* parameter through
which an
alternate Store, Project, or Binding could be named.

**Structural Review Round 3 (P15-R3-F1): possessing a root grants nothing; an externally
anchored admission record is what actually gates access. Read this before reading the diff.**

Round 3 rejected Round 2's deferral outright. Issue #64 assigns this production
runtime-provisioning boundary to *this* Phase, and a bootstrap with no production-legitimate way
to obtain its own required first argument does not satisfy this Phase's own V5 requirement.
Round 3 also observed that the test-only issuer's "structural unavailability" was illusory:
it worked by importing this module's own ``_PROVISIONING_SENTINEL`` and calling
``TrustedRuntimeRoot(..., sentinel)`` directly -- and Python's leading-underscore convention is
not access control, so *any* caller able to import this module could do the identical thing over
an arbitrary Store. The correction therefore failed in both directions at once: legitimate
production composition still could not obtain a root through any supported shipped path, **and**
an untrusted in-process caller could still reproduce the "private" construction trivially.

The fix is not a better-hidden constructor. It is to stop the *type* from being the boundary:

```text
BEFORE (Round 1 / Round 2)   possessing a TrustedRuntimeRoot was SUFFICIENT to reach an
                             adapter, so every question became "who may mint one?" -- a
                             question no shipped library function could answer, and one the
                             sentinel only appeared to answer.

AFTER  (Round 3)             possessing a TrustedRuntimeRoot grants NOTHING BY ITSELF. Every
                             call to bootstrap_projection_execution_capability must ALSO
                             present a runtime_root_admission_ref that resolves, inside that
                             root's own Store, to a canonical, content-addressed, ACTIVE
                             admission record naming exactly that project and that Project
                             Binding, and genuinely signed by the private key matching the
                             trust_anchor_public_key_hex THE CALLER OF THIS FUNCTION SUPPLIES
                             from deployment/composition-time configuration. That check runs on
                             every call, first, regardless of the root's provenance.
```

**This is not a walk-back of Round 2, and the diff should not be read as one.** Round 2's own
mechanical facts are all still literally true and still proved, unchanged, by
``tests/contract/runtime/test_runtime_static_conformance.py``: the deleted
minting factory is *not* reintroduced under its own name or any other; no shipped function
returns a :class:`TrustedRuntimeRoot`; no shipped module constructs one. What changed is that
the type is no longer a capability at all, so a public constructor is no longer a trust
decision -- there is nothing left for a minting function to confer. The sentinel is therefore
dropped rather than replaced: keeping a fake-private gate around a value that grants nothing
would only preserve the illusion Round 3 named. A directly constructed root -- by any caller,
over any Store -- gets exactly zero benefit unless that caller can *also* produce an admission
record signed by a private key it does not have.

*What this does and does not claim.* The mechanism is now complete, shipped, and
production-legitimate: there is a supported path by which a real deployment composition boundary
obtains a capability, and it is not reproducible by a request-path caller who lacks the trust
anchor's private key. This repository still wires no live CLI/agent-runtime entrypoint that
*calls* it (that remains a later, separately authorized concern) -- but that is now a statement
about invocation, not about whether the mechanism itself exists and is correct.

**Structural Review Round 2 (P15-R2-F1): the public minting factory is removed outright.**
*(Historical: superseded in its conclusion by Round 3 above, which reintroduces public
construction only because the type stopped being a capability. Round 2's own findings about the
Round 1 factory remain accurate, and the factory itself is still gone.)*
Round 2 found Round 1's own correction incomplete. ``provision_trusted_runtime_root(store,
project_id, project_binding_id)`` was itself publicly exported and accepted exactly the
caller-controlled Store/Project/Binding tuple the correction was supposed to stop the untrusted
surface from selecting; the module-private sentinel protected only :class:`TrustedRuntimeRoot`'s
own constructor, while the public factory supplied that sentinel for whatever Store a caller
handed it. Moving the same three arguments one call earlier changed the API's shape, not control
of the trust decision -- and Round 1's own regression suite *demonstrated* the bypass rather than
closing it, by provisioning a root over an independently built alternate Store and obtaining a
real capability from it.

This repository has, genuinely, no live deployment/CLI/agent-runtime composition boundary wired
to Runtime yet (Phase 16+ is not authorized; ``RUNTIME_CREDENTIAL_USE_AUTHORITY=false``). The
only structurally honest correction achievable at the library level is therefore the one applied
here: **shipped code contains no function, anywhere, that takes a caller-supplied
store/project/binding and returns a legitimately-typed** :class:`TrustedRuntimeRoot`. The
minting function is deleted rather than renamed -- a same-shaped function under a new name would
reproduce the exact defect the review named.

```text
TrustedRuntimeRoot(store, project_id, project_binding_id)
    -> TrustedRuntimeRoot            an ordinary, public, frozen value naming WHICH world is in
                                     play. It verifies nothing, holds no verdict, confers no
                                     access, and anyone may construct one (Round 3, P15-R3-F1).

bootstrap_projection_execution_capability(
    trusted_runtime_root, *, runtime_root_admission_ref, trust_anchor_public_key_hex,
    grant refs, declaration refs)
    -> ProjectionExecutionCapability  reads the store/project/binding from the root alone,
                                      resolves every reference exclusively within it, and
                                      admits the root at all ONLY against an externally
                                      supplied trust anchor.
```

The type is deliberately **kept**, and is now genuinely public: it is exactly the shape a real
deployment composition boundary names, and since it grants nothing, restricting its construction
would protect nothing.

``trust_anchor_public_key_hex`` is a required keyword argument, and it **must** come from
deployment/composition-time configuration -- the boundary that decides which world is canonical
at all. It is never read from the Store being admitted, never derived from anything on the
request path, and never hardcoded as a specific real-world key in shipped source. This package
holds no private key and mints no signature; it only ever verifies (see
:mod:`~manosube_agent_civilization.runtime.root_admission`).

This module imports no ``tests.*`` module (proved by static conformance -- the identical
discipline ``projection/execution.py``'s own static conformance test already establishes),
constructs no :class:`~manosube_agent_civilization.store.file_store.FileStateStore` of its own
(``store`` is always the caller-injected, already-open object -- the identical discipline
Phase 14 Round 11, P14-R11-F1, already established), mints no Authority record of any kind
(it only resolves and independently reverifies grants/declarations a Human Authority already
issued and a Store already committed), and accepts no authoritative record body directly --
only ``{"kind", "id"}`` references, resolved exclusively within the injected *store*. It makes
zero live network calls of its own; the adapter that later reaches a network at all is supplied
by :meth:`~manosube_agent_civilization.projection.ProjectionExecutionCapability.execute`'s own
caller, never by this module.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.authority import (
    PROJECTION_AUTHORIZED,
    evaluate_projection_authorization,
)
from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding.identity import (
    verify_github_projection_grant_declaration_identity,
)
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change.identity import (
    change_id as _change_id,
    change_semantic_fingerprint as _change_semantic_fingerprint,
)
from manosube_agent_civilization.difference.identity import difference_id as _difference_id
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.evidence.identity import (
    evidence_semantic_fingerprint as _evidence_semantic_fingerprint,
)
from manosube_agent_civilization.projection import (
    PreIssuedProjectionAuthority,
    ProjectionExecutionCapability,
    ProjectionExecutionContext,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .admission_registry import ROOT_ADMISSION_RECORD_KIND, current_root_admission_id
from .engine import require_valid_root_admission
from .errors import RuntimeRequirementError
from .identity import (
    runtime_root_admission_id,
    runtime_root_admission_semantic_fingerprint,
    runtime_root_admission_target_key,
)
from .root_admission import verify_runtime_root_admission_signature

_GRANT_RECORD_KIND = "github_projection_grant"
_DECLARATION_RECORD_KIND = "github_projection_grant_declaration"
_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"
_DIFFERENCE_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "difference/"
_CHANGE_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "change/"

#: Which real canonical subject kind each projection kind's own pre-issued grant must name --
#: the identical pairing :mod:`~manosube_agent_civilization.projection.route` itself enforces.
_SUBJECT_KIND_FOR_PROJECTION_KIND: dict[str, str] = {
    "DIFFERENCE_ISSUE": "difference",
    "CHANGE_PULL_REQUEST": "change",
    "EVIDENCE_ARTIFACT": "observation_evidence",
}


#: The canonical record kind whose ACTIVE, externally-anchored, genuinely signed, *currently
#: pointed-to* instance is what actually admits a deployment composition (Round 3, P15-R3-F1;
#: currency added by Round 4, P15-R4-F1). Read from the one module that owns the chain, so this
#: file and that one can never name two different kinds.
_ROOT_ADMISSION_RECORD_KIND = ROOT_ADMISSION_RECORD_KIND
#: The one ``status`` a Runtime Root Admission may carry and still admit a root. The closed
#: vocabulary itself -- ``ACTIVE``/``REVOKED`` -- is owned by
#: ``01_SCHEMA/runtime/runtime_root_admission.schema.json``, exactly as this package's own
#: ``runtime_deployment_declaration`` already is.
_ADMISSION_ACTIVE_STATUS = "ACTIVE"


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise RuntimeRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _boot(store: Any, project_id: str, project_binding_id: str) -> Any:
    """The one literal ``boot_project`` call site in this module (the identical single-site
    discipline ``route.py`` already keeps, so no second, drifting way of restoring a project can
    appear beside it).

    Reached from exactly three points: once at composition time, to prove the world a deployment
    is binding is genuinely restorable and to read the State its admission pointer lives in; once
    at the start of every request-facing call, freshly, for the same grant/declaration-freshness
    reasons Rounds 1-3 established; and once more (P15-R6-F1) at the end of that same call,
    immediately before the capability is constructed, so the pre-issuance admission barrier reads
    a State that is current *then* rather than one read before all the resolution and
    authorization work happened. None of the three has anything to do with the trust decision --
    composition made that once, and the anchor is gone by then.
    """

    return boot_project(store, project_id=project_id, project_binding_id=project_binding_id)


def _require_reference(value: Any, *, context: str, kind: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"{context} must be an explicit reference object: {value!r}")
    if value.get("kind") != kind:
        raise RuntimeRequirementError(f"{context} does not name kind={kind!r}: {value!r}")
    record_id = value.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise RuntimeRequirementError(f"{context} carries no readable id: {value!r}")
    return {"kind": kind, "id": record_id}


def _full_admission_record_commitment(admission: Mapping[str, Any]) -> str:
    """The exact, complete, schema-valid record -- including its own declared
    ``runtime_root_admission_id``, ``runtime_root_admission_semantic_fingerprint``, and its
    entire ``signature`` block -- reduced to one deterministic digest, via this repository's one
    canonical serialization owner (P15-R7-F1). Deliberately broader than
    :func:`~manosube_agent_civilization.runtime.identity.
    runtime_root_admission_semantic_fingerprint`, which is a hash of
    :data:`~manosube_agent_civilization.runtime.identity.ROOT_ADMISSION_SEMANTIC_FIELDS` alone and
    excludes exactly the three fields a Store-level substitution could otherwise change without
    moving that narrower hash: the record's own declared id, its own declared semantic fingerprint,
    and its signature.

    It reuses ``state.canonicalize.canonical_json_bytes`` -- the single serialization owner
    ``identity.py`` itself reads for every one of its own id/fingerprint derivations -- rather than
    introducing a second way to turn a canonical record into bytes. Two serialization owners would
    be two notions of "what this record is", and the whole point of this commitment is that there
    is exactly one.

    It retains no trust anchor and reintroduces none: the digest is computed over the record alone,
    which carries a ``signature`` block but never a key. Verifying that signature still requires the
    anchor, and the anchor is still consumed exactly once, at composition, and discarded there.
    """

    return "sha256:" + hashlib.sha256(canonical_json_bytes(dict(admission))).hexdigest()


def _require_currently_admitted(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    current_state: Mapping[str, Any],
    runtime_root_admission_ref: Any,
    trust_anchor_public_key_hex: Any,
) -> dict[str, Any]:
    """Admit this deployment composition -- or refuse everything (Round 3, P15-R3-F1; currency
    added by Round 4, P15-R4-F1, item 5).

    This is the control that replaced "possessing a root is sufficient", and it now runs at
    *composition* time rather than on every request-facing call, because Round 4 moved the anchor
    off the request-facing signature entirely. It is deliberately **inside**
    :func:`compose_trusted_runtime_deployment_authority` rather than a separate pre-step a caller
    could forget, discard, or bypass, and it runs before the request-facing closure this
    composition returns can exist at all -- so every refusal here costs zero adapter calls, zero
    grant resolutions, and zero authorization evaluations.

    Seven requirements, in order:

    1. *runtime_root_admission_ref* must be a well-formed reference of kind
       ``runtime_root_admission``.
    2. The record must resolve inside the bound Store, be schema-valid, and its own independently
       recomputed content address and semantic fingerprint must equal its own declared values.
    3. ``status`` must be ``"ACTIVE"``.
    4. Its ``project_id`` and ``project_binding_ref`` must **exactly** equal the ones being
       composed -- one admission artifact anchors exactly one project and one Binding, never an
       unbounded trust grant reusable across arbitrary Stores.
    5. Its ``signature`` must genuinely verify against *trust_anchor_public_key_hex*.
    6. This Project Binding's own admission chain must have a **current** admission at all --
       ``semantic_state.runtime.claims["ROOT-ADMISSION:<project_binding_id>"]``, moved only by
       :func:`~manosube_agent_civilization.runtime.admission_registry.
       commit_runtime_root_admission`. Nothing admitted means nothing is admitted, however many
       individually valid admission records happen to sit in the Store.
    7. The presented reference must name **exactly** that current admission. This is Round 4's own
       addition: an admission that was rotated or revoked at the composition level keeps its own
       unchanged content address and stays individually resolvable, individually schema-valid, and
       individually anchor-signed forever, and presenting it again must be refused on currency
       alone.

    **Why currency is checked last, deliberately.** It is the identical ordering
    ``route._resolve_deployment_declaration`` already uses for its own sibling pointer, and for
    the identical reason: a forged, foreign-signed, tampered, wrong-project, or wrong-Binding
    admission can never *become* current -- the committer that moves the pointer verifies the
    anchor signature before it will move anything -- so if currency ran first, every one of those
    refusals would collapse into a single indistinguishable "not current" message and stop proving
    what it claims to prove. Ordering it last keeps each control refusing for exactly its own
    reason, and leaves the currency control isolated by the rotation and revocation cases, where
    the presented record is perfectly genuine in every other respect.

    Requirement 5 is what makes the record-level checks mean anything. The anchor key is supplied by the
    deployment/composition boundary itself, from its own configuration -- never read from the
    Store being admitted, never derived from anything on the request path, and never a constant in
    shipped source. An attacker holding a complete, internally valid alternate world can mint an
    admission record inside it and self-sign it with that world's own genuinely legitimate key; it
    fails here, because the key that decides is one that world never had.
    """

    if not isinstance(trust_anchor_public_key_hex, str) or not trust_anchor_public_key_hex:
        raise RuntimeRequirementError(
            "trust_anchor_public_key_hex must be a non-empty hex-encoded Ed25519 public key, "
            "supplied by the deployment/composition boundary itself -- never read from the "
            "Store being admitted, and never derived from anything on the request path"
        )
    checked_ref = _require_reference(
        runtime_root_admission_ref,
        context="runtime_root_admission_ref",
        kind=_ROOT_ADMISSION_RECORD_KIND,
    )
    resolved = store.resolve_record(project_id, _ROOT_ADMISSION_RECORD_KIND, checked_ref["id"])
    if resolved is None:
        raise RuntimeRequirementError(
            "runtime_root_admission_ref does not resolve to a committed runtime_root_admission "
            f"for project {project_id!r}: {checked_ref['id']!r} -- an unadmitted deployment "
            "composition provisions nothing"
        )
    admission = require_valid_root_admission(resolved)
    if runtime_root_admission_id(admission) != admission.get("runtime_root_admission_id"):
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} own recomputed identity "
            "does not equal its own declared value -- refusing to trust it"
        )
    if runtime_root_admission_semantic_fingerprint(admission) != admission.get(
        "runtime_root_admission_semantic_fingerprint"
    ):
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust it"
        )
    if admission.get("status") != _ADMISSION_ACTIVE_STATUS:
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} is not ACTIVE "
            f"({admission.get('status')!r}) -- a revoked admission admits nothing, and a revoked "
            "head is terminal for its own chain"
        )
    if admission.get("project_id") != project_id:
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} admits a different project "
            f"than this composition names: {admission.get('project_id')!r} != {project_id!r}"
        )
    expected_binding_ref = {"kind": "project_binding", "id": project_binding_id}
    if admission.get("project_binding_ref") != expected_binding_ref:
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} admits a different Project "
            f"Binding than this composition names: {admission.get('project_binding_ref')!r} != "
            f"{expected_binding_ref!r} -- one admission artifact anchors exactly one project and "
            "one Binding, never an unbounded trust grant"
        )
    if not verify_runtime_root_admission_signature(
        admission, trust_anchor_public_key_hex=trust_anchor_public_key_hex
    ):
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} carries no genuine signature "
            "over its own adopted semantic fields by the externally supplied trust anchor -- an "
            "unsigned, self-authored, or foreign-world-signed admission admits nothing, and this "
            "is the one check an internally self-consistent alternate world cannot satisfy"
        )
    chain_key = runtime_root_admission_target_key(
        {"project_binding_ref": {"kind": "project_binding", "id": project_binding_id}}
    )
    current_id = current_root_admission_id(current_state, chain_key)
    if current_id is None:
        raise RuntimeRequirementError(
            "no runtime_root_admission is currently admitted for this Project Binding -- "
            f"refusing to compose a deployment authority for {project_binding_id!r}: an "
            "admission record that was never made current through the canonical "
            "commit-and-supersede path admits nothing, however individually genuine it is"
        )
    if current_id != checked_ref["id"]:
        raise RuntimeRequirementError(
            f"the presented runtime_root_admission {checked_ref['id']!r} is no longer the current "
            f"one for this Project Binding ({current_id!r} is) -- refusing to compose a "
            "deployment authority: it has been rotated or revoked, and its own content, "
            "signature, and resolvability remaining genuine does not make it current again"
        )
    return admission


def _require_bound_admission_still_current(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    current_state: Mapping[str, Any],
    bound_admission_id: str,
    bound_generation: int,
    bound_semantic_fingerprint: str,
    bound_full_record_commitment: str,
) -> None:
    """P15-R5-F2, completed by P15-R6-F1 and P15-R7-F1: before issuing any NEW capability from a
    bound service,
    freshly prove the root admission that service was composed against is still this Project
    Binding's own current one -- with no raw trust anchor in this call's own signature. The
    admission was cryptographically admitted once, at composition
    (:func:`_require_currently_admitted`); this recheck only asks whether the canonical Store's own
    current-admission pointer -- moved exclusively by
    :func:`~manosube_agent_civilization.runtime.admission_registry.commit_runtime_root_admission`,
    itself anchor-signature-gated -- still names that exact record, and whether the record now
    resolving under that id is still, in every observable respect, the exact record composition
    proved. Already-issued downstream capabilities are not retroactively revoked by this check; it
    only gates whether THIS call may mint a new one.

    **Nine requirements**, each stated and checked separately -- the four the Round 5 contract
    listed, the two P15-R6-F1 added, and the three P15-R7-F1 adds:

    1. the pointer still names the exact admission id captured at composition;
    2. the resolved current admission carries the exact captured ``generation``;
    3. the current admission is still ``ACTIVE``;
    4. it still restates this bound service's own Project and Project Binding;
    5. its identity, **independently recomputed from the body now resolving**, equals the exact
       identity captured at composition;
    6. its semantic fingerprint, likewise independently recomputed from that body, equals the
       exact fingerprint captured at composition;
    7. its own **declared** ``runtime_root_admission_id`` equals that recomputed identity -- so
       declared, recomputed and bound are all one value, not two out of three;
    8. its own **declared** ``runtime_root_admission_semantic_fingerprint`` equals that recomputed
       fingerprint -- the same three-way equality, for the same reason;
    9. the **exact full-record commitment** over the body now resolving -- every field it carries,
       including ``signature.algorithm``, ``signature.key_id`` and ``signature.value`` -- equals
       the commitment captured at composition over the exact anchor-verified record.

    They are deliberately *not* collapsed into one another even where an implication is visible
    (a content-addressed record's ``generation``, ``status`` and Binding are all covered by its
    own id, so requirement 5 arguably implies 2-4 for an untampered Store; and requirement 9
    arguably implies 5-8 for any body at all). Each is what it says, and each refuses with its own
    message, so a future edit that changes what "current" resolves through cannot silently take
    eight checks with it.

    **Why 5 and 6 recompute from the body rather than reading the body's own declared fields, and
    why that is what closes the substitution gap.** Round 5 checked only requirements 1-4, and
    every one of them reads *fields the resolved record declares about itself*. A Store-level
    substitution under the current id -- an altered ``predecessor_ref``, ``declared_at``, or
    ``signature``, with ``generation``/``status``/``project_id``/``project_binding_ref`` left
    exactly as they were -- therefore passed the whole gate: composition proved the ORIGINAL
    record, and the recheck never re-proved that the currently-resolved body is still that same
    record, only that certain of its fields still read a particular way. Requirements 5 and 6
    close exactly that, and they anchor to the *composition-time-captured* commitment rather than
    to the body's own ``runtime_root_admission_id``/
    ``runtime_root_admission_semantic_fingerprint`` fields, because a tampered body could
    self-consistently declare a forged id and fingerprint matching its own tampered content and so
    satisfy a self-comparison trivially. The reference these recomputations are compared against
    is the one this service closed over before any request boundary existed.

    **Why requirements 7-9 exist at all, and what each of them alone can see (P15-R7-F1).**
    Requirements 5 and 6 recompute from
    :data:`~manosube_agent_civilization.runtime.identity.ROOT_ADMISSION_SEMANTIC_FIELDS`, and that
    projection deliberately **excludes** three of the record's own fields: its declared
    ``runtime_root_admission_id``, its declared ``runtime_root_admission_semantic_fingerprint``
    (an identity cannot be computed over itself), and its entire ``signature`` block (a signature
    cannot cover its own value). Those exclusions are correct where they are made -- and they are
    precisely the blind spot a Store-level substitution can aim at, because a body whose *semantic*
    fields are untouched recomputes to exactly the bound id and the bound fingerprint however those
    three excluded fields read:

    ```text
    substitute ONLY the declared runtime_root_admission_id
        -> requirements 1-6 all pass (the pointer moved nothing, and the recomputation reads
           different fields entirely)                                  CAUGHT BY 7
    substitute ONLY the declared runtime_root_admission_semantic_fingerprint
        -> requirements 1-7 all pass                                   CAUGHT BY 8
    substitute ONLY signature.value (or signature.key_id)
        -> requirements 1-8 all pass: the signature block is invisible to every one of them, and
           it is not reverified here either -- the anchor is gone by then, by design
                                                                       CAUGHT BY 9
    ```

    So 7 and 8 close the gap where a substitution changes only the record's own *self-declared*
    id/fingerprint fields, by demanding a **three-way** equality -- declared == recomputed ==
    bound -- rather than the recomputed-versus-bound pair alone. That is not the self-comparison
    5 and 6 rightly refuse to rely on: the bound value is still the anchor of the chain of
    equalities, and adding the declared field to it can only ever *narrow* what passes. And
    requirement 9 is the one that actually reaches the signature, because a full-record commitment
    is the only thing here computed over the complete record rather than over a projection that
    excludes exactly what a substitution would move.

    **Why they are checked last, deliberately.** It is the identical ordering
    :func:`_require_currently_admitted` already keeps for its own currency check, and for the
    identical reason: requirements 2-4 each name a specific, independently meaningful way the
    current admission can have stopped being what this service was composed against, and any body
    that fails one of them necessarily also fails 5. Recomputing first would collapse every one of
    those refusals into a single indistinguishable "identity mismatch" message and stop each
    control proving what it claims to prove; recomputing last leaves requirements 5 and 6 isolated
    by exactly the case nothing else can see -- a substituted body whose declared
    generation/status/Project/Binding are untouched. P15-R7-F1's own three requirements extend
    that same ordering rationale one step further and are therefore placed after 5 and 6 rather
    than before them: requirement 9 is the broadest check in this function -- every body that fails
    any of 5-8 necessarily also fails 9 -- so putting it first would collapse all of them into one
    indistinguishable "full-record commitment mismatch", and 7 and 8 would never refuse for their
    own reason. Checked last, requirement 9 is isolated by exactly the case nothing narrower can
    see: a body whose every semantic field, whose own declared id and whose own declared
    fingerprint are all untouched, and whose ``signature`` alone was replaced.

    Reached twice per request-facing call (P15-R6-F1, item 3): once before any grant reference is
    resolved -- so a rotated or revoked service refuses before any adapter or network call could
    exist, the identical refuse-at-zero-cost ordering :func:`_require_currently_admitted` already
    keeps at composition -- and once again immediately before the capability is constructed, from
    a second, fresh Boot, so a rotation or revocation committing *between* those two points cannot
    still be followed by a new issuance.
    """

    chain_key = runtime_root_admission_target_key(
        {"project_binding_ref": {"kind": "project_binding", "id": project_binding_id}}
    )
    current_id = current_root_admission_id(current_state, chain_key)
    if current_id != bound_admission_id:
        raise RuntimeRequirementError(
            f"the runtime_root_admission this bound service was composed against "
            f"({bound_admission_id!r}) is no longer the current one for this Project Binding "
            f"({current_id!r} is) -- refusing to issue a new capability from a no-longer-current "
            "composition authority"
        )
    resolved = store.resolve_record(project_id, _ROOT_ADMISSION_RECORD_KIND, current_id)
    if resolved is None:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} no longer resolves in the bound "
            "Store -- refusing to issue a new capability"
        )
    admission = require_valid_root_admission(resolved)
    if int(admission.get("generation", -1)) != bound_generation:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} no longer carries the exact "
            f"generation this bound service was composed against ({bound_generation!r}) -- "
            "refusing to issue a new capability"
        )
    if admission.get("status") != _ADMISSION_ACTIVE_STATUS:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} is not ACTIVE "
            f"({admission.get('status')!r}) -- refusing to issue a new capability"
        )
    if admission.get("project_id") != project_id or admission.get("project_binding_ref") != {
        "kind": "project_binding",
        "id": project_binding_id,
    }:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} no longer restates this bound "
            "service's own Project/Binding -- refusing to issue a new capability"
        )
    recomputed_id = runtime_root_admission_id(admission)
    if recomputed_id != bound_admission_id:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} own recomputed identity "
            f"({recomputed_id!r}) does not equal the identity this bound service was composed "
            "against -- refusing to issue a new capability: the resolved record no longer matches "
            "the exact admission composition proved, however its own self-declared fields read"
        )
    recomputed_fingerprint = runtime_root_admission_semantic_fingerprint(admission)
    if recomputed_fingerprint != bound_semantic_fingerprint:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} own recomputed semantic "
            f"fingerprint ({recomputed_fingerprint!r}) does not equal the fingerprint this bound "
            "service was composed against -- refusing to issue a new capability"
        )
    # P15-R7-F1, requirements 7-9. Everything above reads, or recomputes from, the semantic-fields
    # projection alone -- which deliberately excludes the record's own declared id, its own
    # declared semantic fingerprint, and its signature. These three requirements are what reach
    # exactly those excluded fields.
    declared_id = admission.get("runtime_root_admission_id")
    if declared_id != recomputed_id:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} own declared identity "
            f"({declared_id!r}) does not equal its own recomputed identity ({recomputed_id!r}) -- "
            "refusing to issue a new capability: the resolved record's declared id has been "
            "substituted independently of its semantic content"
        )
    declared_fingerprint = admission.get("runtime_root_admission_semantic_fingerprint")
    if declared_fingerprint != recomputed_fingerprint:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} own declared semantic fingerprint "
            f"({declared_fingerprint!r}) does not equal its own recomputed semantic fingerprint "
            f"({recomputed_fingerprint!r}) -- refusing to issue a new capability: the resolved "
            "record's declared fingerprint has been substituted independently of its semantic "
            "content"
        )
    full_record_commitment = _full_admission_record_commitment(admission)
    if full_record_commitment != bound_full_record_commitment:
        raise RuntimeRequirementError(
            f"the current runtime_root_admission {current_id!r} own full-record commitment does "
            "not equal the exact anchor-verified record commitment captured at composition -- "
            "refusing to issue a new capability: some field of the resolved record (potentially "
            "including its signature) no longer matches the exact record composition proved"
        )


def _resolve_grant(store: Any, project_id: str, ref: Any, *, context: str) -> dict[str, Any]:
    checked = _require_reference(ref, context=context, kind=_GRANT_RECORD_KIND)
    resolved = store.resolve_record(project_id, _GRANT_RECORD_KIND, checked["id"])
    if resolved is None:
        raise RuntimeRequirementError(
            f"{context} does not resolve for project {project_id!r}: {checked}"
        )
    body = dict(resolved)
    if github_projection_grant_id(body) != body.get("github_projection_grant_id"):
        raise RuntimeRequirementError(
            f"{context} resolved a grant whose own recomputed identity does not match its "
            "declared value -- refusing to trust it"
        )
    return body


def _resolve_declaration(store: Any, project_id: str, ref: Any, *, context: str) -> dict[str, Any]:
    checked = _require_reference(ref, context=context, kind=_DECLARATION_RECORD_KIND)
    resolved = store.resolve_record(project_id, _DECLARATION_RECORD_KIND, checked["id"])
    if resolved is None:
        raise RuntimeRequirementError(
            f"{context} does not resolve for project {project_id!r}: {checked}"
        )
    body = dict(resolved)
    verify_github_projection_grant_declaration_identity(body)
    return body


def _resolve_subject(
    store: Any, project_id: str, subject_ref: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    kind = subject_ref.get("kind")
    record_id = subject_ref.get("id")
    if kind not in _SUBJECT_KIND_FOR_PROJECTION_KIND.values():
        raise RuntimeRequirementError(f"subject_ref names an unrecognized kind: {subject_ref!r}")
    if not isinstance(record_id, str) or not record_id:
        raise RuntimeRequirementError(f"subject_ref carries no readable id: {subject_ref!r}")
    resolved = store.resolve_record(project_id, kind, record_id)
    if resolved is None:
        raise RuntimeRequirementError(
            f"subject_ref does not resolve for project {project_id!r}: {kind}/{record_id}"
        )
    body = dict(resolved)

    if kind == "difference":
        if body.get("project_id") != project_id:
            raise RuntimeRequirementError("subject_record.project_id does not match project_id")
        _validate_canonical_record(body, "difference.schema.json", base=_DIFFERENCE_SCHEMA_BASE)
        real_id = _difference_id(body)
        if record_id != real_id:
            raise RuntimeRequirementError(
                "subject_ref does not name the real, recomputed identity of subject_record"
            )
        real_fingerprint = "sha256:" + hashlib.sha256(real_id.encode("utf-8")).hexdigest()
    elif kind == "change":
        if body.get("project_id") != project_id:
            raise RuntimeRequirementError("subject_record.project_id does not match project_id")
        _validate_canonical_record(body, "change.schema.json", base=_CHANGE_SCHEMA_BASE)
        real_id = _change_id(body)
        if record_id != real_id:
            raise RuntimeRequirementError(
                "subject_ref does not name the real, recomputed identity of subject_record"
            )
        real_fingerprint = _change_semantic_fingerprint(body)
    else:
        real_fingerprint = _evidence_semantic_fingerprint(body)

    return body, real_fingerprint


def compose_trusted_runtime_deployment_authority(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    runtime_root_admission_ref: Mapping[str, str],
    trust_anchor_public_key_hex: str,
) -> Callable[..., ProjectionExecutionCapability]:
    """**The** shipped, production, trusted-composition entry point (Round 4, P15-R4-F1, item 1;
    rebuilt as a bound request-facing service by Round 5, P15-R5-F1): bind one canonical Store,
    Project, Project Binding, exact root admission, and configured trust anchor, and return the
    **request-facing operation itself**, already closed over every one of them.

    This is the boundary that decides *which world is canonical at all*, and it is the only place
    in shipped request-reachable code where a raw trust anchor is ever named. It is called once,
    by a real deployment's own composition boundary, before any request boundary exists -- never
    from a request path, and never with configuration read here: this function reads no
    environment variable, no file, and no registry. Every value it needs is injected by its
    caller, which is the deployment itself.

    ```python
    bootstrap = compose_trusted_runtime_deployment_authority(
        store,  # the canonical, already-open Store handle
        project_id=project_id,
        project_binding_id=project_binding_id,
        runtime_root_admission_ref=ref,  # must be the CURRENTLY admitted one
        trust_anchor_public_key_hex=configured,  # deployment configuration; never from `store`
    )
    # ... hand `bootstrap` -- and nothing else -- to request-facing code, which can name only
    # operation-scoped references:
    capability = bootstrap(
        github_projection_grant_refs=[...],
        github_projection_grant_declaration_refs=[...],
    )
    ```

    What it proves before returning anything: the Project and Project Binding genuinely Boot; this
    Project Binding's own admission chain has a current admission; *runtime_root_admission_ref*
    names exactly that current admission (so a rotated or revoked one cannot be replayed through
    its own still-valid reference); the resolved record is schema-valid and its own recomputed
    identity and semantic fingerprint match its own declared values; it is ``ACTIVE``; it restates
    exactly this project and this Binding; and its signature genuinely verifies against
    *trust_anchor_public_key_hex*. See :func:`_require_currently_admitted` for the full ordering
    and the reasoning behind each step.

    The anchor is used here and **discarded**: it is not stored anywhere on the returned
    operation, is not reachable from it, and is never re-verified per call. What *is* retained,
    in the returned operation's own closure, is the admitted record's id, generation and
    independently recomputed semantic fingerprint (P15-R6-F1, item 1) -- and, since Round 7
    (P15-R7-F1, item 1), a deterministic digest of the **exact full record** those three are a
    projection of, computed by :func:`_full_admission_record_commitment` over the very object this
    function's own admission gate proved. Together they are the immutable canonical commitment to
    the exact anchor-verified admission. That is exactly what the per-call
    currency-and-commitment recheck needs, and exactly what it may have without reintroducing a
    raw anchor anywhere downstream of this call: a record carries a signature, never a key.

    Raises :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` on any
    refusal; every :class:`~manosube_agent_civilization.boot.errors.BootError`/
    :class:`~manosube_agent_civilization.store.errors.StoreError` a resolved owner itself raises
    propagates unchanged. Mints nothing, signs nothing, commits nothing, and holds no private key.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    boot_context = _boot(store, project_id, project_binding_id)
    admission = _require_currently_admitted(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        current_state=boot_context.current_state,
        runtime_root_admission_ref=runtime_root_admission_ref,
        trust_anchor_public_key_hex=trust_anchor_public_key_hex,
    )
    bound_admission_id = str(admission["runtime_root_admission_id"])
    bound_generation = int(admission["generation"])
    # P15-R6-F1, item 1: the immutable canonical commitment to the *exact* anchor-verified
    # admission. Not only id and generation, but the semantic fingerprint too -- already
    # independently recomputed from this record's own body, and already proved equal to its own
    # declared value, by _require_currently_admitted's own checks above. Captured in a closure cell
    # exactly as the other two are, so every per-call recheck can anchor to a reference chosen
    # before any request boundary existed rather than to whatever the Store hands back later.
    bound_semantic_fingerprint = str(admission["runtime_root_admission_semantic_fingerprint"])
    # P15-R7-F1, item 1: the commitment to the EXACT full record, beside -- never instead of --
    # the three semantic cells above. It is computed over the very object
    # ``_require_currently_admitted`` returned, which is the record composition actually proved
    # (schema-valid, anchor-signature-verified, currently pointed to), rather than over a
    # re-resolved copy, so composition's own commitment is over the record it saw and no other.
    bound_full_record_commitment = _full_admission_record_commitment(admission)

    def bootstrap_projection_execution_capability(
        *,
        github_projection_grant_refs: list[Mapping[str, str]] | tuple[Mapping[str, str], ...],
        github_projection_grant_declaration_refs: list[Mapping[str, str]]
        | tuple[Mapping[str, str], ...],
    ) -> ProjectionExecutionCapability:
        """The **request-facing** operation (Round 4, P15-R4-F1, items 2-3; bound to its world by
        Round 5, P15-R5-F1): resolve *github_projection_grant_refs*/
        *github_projection_grant_declaration_refs* -- references only, never record bodies --
        exclusively within the Store the enclosing composition was built around, an already-open
        object this operation never opens, selects, or constructs.

        **This signature carries no ``deployment_authority``, no ``store``, no ``project_id``, no
        ``project_binding_id``, no ``runtime_root_admission_ref``, and no
        ``trust_anchor_public_key_hex``.** There is no call shape at all -- not one refused at
        runtime, one that does not exist -- through which a caller could name an alternate Store,
        Project, Binding, admission, or trust anchor, and no object to substitute in place of one
        either, because the world is not an argument: it lives in this function's own closure
        cells, written once by the composition call that created this function object and
        unnameable from any call site. A fully self-consistent attacker world, complete with its
        own Binding, Authority, grants, subjects, a correctly signed root admission and the
        matching attacker public key, has nowhere to go.

        Every call freshly Boots, for exactly the grant/declaration-freshness reasons Rounds 1-3
        established (no authority may ever be carried forward as a stale verdict), and then --
        P15-R5-F2 -- freshly rechecks that the admission this service was composed against is
        still this Project Binding's own current one, before resolving a single grant.

        **Two barriers, not one (P15-R6-F1).** That opening recheck is necessary and was not
        sufficient: it ran once, at the start of the request, and the capability was then built
        from that same original snapshot after all the grant/declaration/subject resolution and
        Authority evaluation in between -- so a canonical rotation or revocation committing during
        that window was still followed by a newly issued capability. This operation therefore
        Boots a **second** time and repeats the entire
        :func:`_require_bound_admission_still_current` check -- identity, fingerprint, generation,
        status, Project/Binding, the declared-versus-recomputed pair and the full-record
        commitment, all nine requirements (P15-R7-F1) -- immediately before the
        :class:`~manosube_agent_civilization.projection.ProjectionExecutionContext` is
        constructed, and builds that context's ``state_revision``/``semantic_fingerprint`` from
        the final Boot rather than the initial one. No Boot here has anything to do with the
        *trust* decision, which composition made once and whose anchor is, deliberately, no longer
        reachable from anywhere.

        Returns one :class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability`
        bound to a freshly constructed :class:`~manosube_agent_civilization.projection.
        ProjectionExecutionContext` -- if, and only if, exactly one resolved grant and exactly one
        anchoring declaration exist for each distinct ``projection_kind`` the resolved grants
        themselves name, each grant's own ``subject_ref`` resolves to a real subject record within
        that same bound Store whose independently recomputed identity/fingerprint matches both
        *subject_ref* and the grant's own claimed ``subject_fingerprint``, and each genuinely
        authorizes ``MATERIALIZE_PROJECTION`` through
        :func:`~manosube_agent_civilization.authority.evaluate_projection_authorization` -- the
        same function a production projection call already trusts.

        Raises :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` on any
        malformed input or refusal; every
        :class:`~manosube_agent_civilization.boot.errors.BootError`/
        :class:`~manosube_agent_civilization.store.errors.StoreError`/
        :class:`~manosube_agent_civilization.binding.errors.BindingError`/
        :class:`~manosube_agent_civilization.authority.errors.AuthorityError` any resolved owner
        itself raises propagates unchanged. Never mints, signs, or commits anything, and never
        accepts a caller-supplied subject or grant/declaration body of any kind -- every record
        consumed here was already externally issued, committed, and Store-resolved before this
        call.
        """

        request_boot_context = _boot(store, project_id, project_binding_id)
        _require_bound_admission_still_current(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            current_state=request_boot_context.current_state,
            bound_admission_id=bound_admission_id,
            bound_generation=bound_generation,
            bound_semantic_fingerprint=bound_semantic_fingerprint,
            bound_full_record_commitment=bound_full_record_commitment,
        )

        if not github_projection_grant_refs:
            raise RuntimeRequirementError(
                "github_projection_grant_refs must name at least one grant"
            )

        human_authority_ref = request_boot_context.human_authority_ref
        human_authority_signing_key = request_boot_context.project_binding.get(
            "human_authority_signing_key"
        )
        if not isinstance(human_authority_signing_key, Mapping):
            raise RuntimeRequirementError(
                "the Boot-restored project_binding carries no readable human_authority_signing_key"
            )

        grants = [
            _resolve_grant(
                store, project_id, ref, context=f"github_projection_grant_refs[{position}]"
            )
            for position, ref in enumerate(github_projection_grant_refs)
        ]
        declarations = [
            _resolve_declaration(
                store,
                project_id,
                ref,
                context=f"github_projection_grant_declaration_refs[{position}]",
            )
            for position, ref in enumerate(github_projection_grant_declaration_refs)
        ]

        # Dynamic kind set (this module's own deliberate divergence from the V3 test fixture's
        # fixed three-kind requirement -- see this module's own docstring): whatever
        # projection_kind values the resolved grants themselves name, each still requiring exactly
        # one grant and exactly one anchoring declaration.
        distinct_projection_kinds: set[str] = set()
        for grant in grants:
            kind = grant.get("projection_kind")
            if not isinstance(kind, str) or not kind:
                raise RuntimeRequirementError(
                    f"a resolved grant carries no readable projection_kind: {grant!r}"
                )
            distinct_projection_kinds.add(kind)
        projection_kinds = sorted(distinct_projection_kinds)

        decisions: dict[str, Mapping[str, Any]] = {}
        authorities: dict[str, PreIssuedProjectionAuthority] = {}
        for projection_kind in projection_kinds:
            if projection_kind not in _SUBJECT_KIND_FOR_PROJECTION_KIND:
                raise RuntimeRequirementError(
                    f"a resolved grant names an unrecognized projection_kind: {projection_kind!r}"
                )
            matching_grants = [g for g in grants if g.get("projection_kind") == projection_kind]
            if len(matching_grants) != 1:
                raise RuntimeRequirementError(
                    f"exactly one grant is required per projection_kind, found "
                    f"{len(matching_grants)} for {projection_kind!r}"
                )
            grant = matching_grants[0]

            subject_ref = grant.get("subject_ref")
            target_repository = grant.get("target_repository")
            grant_id = grant.get("github_projection_grant_id")
            if not isinstance(subject_ref, Mapping) or not isinstance(target_repository, Mapping):
                raise RuntimeRequirementError(
                    f"grant {grant_id!r} carries no readable subject_ref/target_repository"
                )
            if subject_ref.get("kind") != _SUBJECT_KIND_FOR_PROJECTION_KIND[projection_kind]:
                raise RuntimeRequirementError(
                    f"grant {grant_id!r} subject_ref names a kind inconsistent with its own "
                    f"projection_kind: {subject_ref.get('kind')!r}"
                )
            if not isinstance(grant_id, str) or not grant_id:
                raise RuntimeRequirementError(
                    "grant carries no readable github_projection_grant_id"
                )

            subject_record, real_subject_fingerprint = _resolve_subject(
                store, project_id, subject_ref
            )
            if grant.get("subject_fingerprint") != real_subject_fingerprint:
                raise RuntimeRequirementError(
                    f"grant {grant_id!r} own subject_fingerprint does not match the real, "
                    "recomputed subject fingerprint"
                )

            matching_declarations = [
                d
                for d in declarations
                if isinstance(d.get("grant_ref"), Mapping) and d["grant_ref"].get("id") == grant_id
            ]
            if len(matching_declarations) != 1:
                raise RuntimeRequirementError(
                    f"exactly one anchoring declaration is required per grant, found "
                    f"{len(matching_declarations)} for grant {grant_id!r}"
                )
            declaration = matching_declarations[0]
            declaration_id = declaration.get("github_projection_grant_declaration_id")
            if not isinstance(declaration_id, str) or not declaration_id:
                raise RuntimeRequirementError("declaration carries no readable identity")

            request = {
                "schema_version": "0.1",
                "project_id": project_id,
                "subject_ref": dict(subject_ref),
                "subject_fingerprint": real_subject_fingerprint,
                "projection_kind": projection_kind,
                "target_repository": dict(target_repository),
                "payload_fingerprint": grant.get("payload_fingerprint"),
                "permitted_action": _PERMITTED_ACTION,
                "human_authority_ref": dict(human_authority_ref),
                "human_authority_signing_key": dict(human_authority_signing_key),
                "grants": [grant],
                "grant_declarations": [declaration],
            }
            decision = evaluate_projection_authorization(request)
            if decision.get("decision") != PROJECTION_AUTHORIZED:
                raise RuntimeRequirementError(
                    f"no genuine github_projection_grant authorizes projection_kind={projection_kind!r} "
                    f"for project {project_id!r}; decision reason codes: {decision.get('decision_reason_codes')}"
                )

            decisions[projection_kind] = decision
            authorities[projection_kind] = PreIssuedProjectionAuthority(
                projection_kind=projection_kind,
                subject_ref=dict(subject_ref),
                subject_record=subject_record,
                github_projection_grant_ref={"kind": _GRANT_RECORD_KIND, "id": grant_id},
                github_projection_grant_declaration_ref={
                    "kind": _DECLARATION_RECORD_KIND,
                    "id": declaration_id,
                },
            )

        # P15-R6-F1, items 3-4: the pre-issuance barrier. Every grant, declaration and subject has
        # now been resolved and every Authority decision evaluated -- all of it work that takes
        # real time, during which a canonical rotation or revocation can genuinely commit. Boot
        # again, freshly, and repeat the FULL commitment check (identity, fingerprint, generation,
        # status, Project/Binding, declared-versus-recomputed identity and fingerprint, and the
        # exact full-record commitment -- all nine requirements, not a subset) immediately before a
        # capability is constructed, so that "rotation or revocation prevents new capability
        # issuance" holds at the moment of issuance rather than only at the moment the request
        # started.
        final_boot_context = _boot(store, project_id, project_binding_id)
        _require_bound_admission_still_current(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            current_state=final_boot_context.current_state,
            bound_admission_id=bound_admission_id,
            bound_generation=bound_generation,
            bound_semantic_fingerprint=bound_semantic_fingerprint,
            bound_full_record_commitment=bound_full_record_commitment,
        )

        # The returned context's State snapshot comes from THIS final Boot, never the initial one:
        # a capability must describe the State that was current when it was issued.
        #
        # Disclosed judgment call (P15-R6-F1): ``human_authority_ref``/
        # ``human_authority_signing_key`` -- and therefore ``decisions``/``authorities`` and the
        # context's own ``github_authority_ref`` -- deliberately remain sourced from the FIRST
        # Boot. They are what the Authority evaluation above actually ran against, and what the
        # returned capability legitimately represents. Re-deriving them from a later Boot after
        # the fact would make the context claim it was authorized under a Human Authority binding
        # no evaluation ever used, if a re-binding landed between the two Boots -- a strictly
        # worse defect than the one this barrier closes. Only the STATE SNAPSHOT moves.
        current_state = final_boot_context.current_state
        context = ProjectionExecutionContext(
            store=store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            github_authority_ref=human_authority_ref,
            authorities=authorities,
            state_revision=current_state["state_revision"],
            semantic_fingerprint=current_state["semantic_fingerprint"],
            decisions=decisions,
        )
        return ProjectionExecutionCapability(context)

    return bootstrap_projection_execution_capability


__all__ = ["compose_trusted_runtime_deployment_authority"]
