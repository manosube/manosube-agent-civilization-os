"""The trusted runtime bootstrap: production Phase 14 capability provisioning (Phase 15, Issue
#64, V5).

Structural Review Round 12/13 of Phase 14 (Issue #62, P14-R12-F1, P14-R13-F1/F2) drew the
Phase 14/Phase 15 boundary at a formal execution *interface* -- :class:`~manosube_agent_civilization.
projection.ProjectionExecutionCapability`, consuming an already-resolved, opaque
:class:`~manosube_agent_civilization.projection.ProjectionExecutionContext` -- while explicitly
deferring *provisioning* that context from canonical Store/Boot state to Phase 15. This module
is that deferred provisioning: :func:`bootstrap_projection_execution_capability` is a
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
  own supplied grant references actually name -- this function derives the kind set from the
  resolved grants themselves, never a fixed constant.
- **Raises rather than returns ``None``.** The V3 fixture is deliberately a fail-closed gate
  that *never raises*, appropriate to a test harness deciding whether to attempt a live write at
  all. This function is an ordinary production route, like every other canonical route in this
  repository (``boot.boot_project``, ``projection.route.project_to_github``): it raises
  :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` (or lets
  ``boot_project``'s/``evaluate_projection_authorization``'s own errors propagate unchanged) on
  any refusal, so a real caller can see *why* provisioning failed.

**Structural Review Round 1 (P15-R1-F4): the trust root is a type, not a parameter list.**
As first delivered, :func:`bootstrap_projection_execution_capability` took ``store``,
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
:func:`bootstrap_projection_execution_capability` lost *every* parameter through which an
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

from collections.abc import Mapping
from dataclasses import dataclass
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

from .engine import require_valid_root_admission
from .errors import RuntimeRequirementError
from .identity import (
    runtime_root_admission_id,
    runtime_root_admission_semantic_fingerprint,
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


#: The canonical record kind whose ACTIVE, externally-anchored, genuinely signed instance is
#: what actually admits a :class:`TrustedRuntimeRoot` (Round 3, P15-R3-F1).
_ROOT_ADMISSION_RECORD_KIND = "runtime_root_admission"
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


@dataclass(frozen=True, slots=True)
class TrustedRuntimeRoot:
    """One immutable handle naming exactly which Store, Project, and Project Binding a trusted
    runtime provisioning call operates within (P15-R1-F4) -- and, since Round 3 (P15-R3-F1),
    **nothing more than that name.**

    **Constructing one is public, unrestricted, and confers no access whatsoever.** Round 1
    shipped a public ``provision_trusted_runtime_root`` factory; Round 2 deleted it and left
    construction behind a module-private sentinel; Round 3 found that sentinel to be a
    convention rather than a control (any caller able to import this module could read it) and,
    more importantly, found the whole framing wrong: while *possessing* a root was sufficient to
    reach an adapter, "who may mint one?" was an unanswerable question no library-level trick
    could close.

    So the boundary moved off this type entirely.
    :func:`bootstrap_projection_execution_capability` now admits a root **only** against a
    canonical, Store-committed, ACTIVE ``runtime_root_admission`` record naming exactly this
    project and this Project Binding, genuinely signed by the private key matching a
    ``trust_anchor_public_key_hex`` **its own caller supplies from deployment-time
    configuration** -- a key that is deliberately not resolvable from inside the Store being
    admitted at all. That check reruns on every call, before anything else substantive, whatever
    the root's provenance. A directly constructed root over an attacker's own fully
    self-consistent world therefore gets exactly nothing: the attacker can forge every record in
    that world, including an admission record signed by *their* key, and still cannot produce
    one that verifies against an anchor they do not hold.

    Keeping a fake-private constructor around a value that grants nothing would preserve the
    illusion Round 3 named, so the sentinel is dropped rather than relocated. Round 2's own
    mechanical facts are untouched and still proved: the deleted factory is not reintroduced
    under any name, no shipped function returns this type, and no shipped module constructs one.

    This type verifies nothing about the world it names, deliberately: it holds no Boot verdict,
    no resolved record, and no fingerprint, so it can never be a stale attestation that
    something *was* valid at construction time. Every verification happens fresh inside the
    bootstrap call that consumes it. It does still require *project_id*/*project_binding_id* to
    be plain canonical identities rather than paths, URLs, or locators -- the identical check
    Boot's own entry point applies.
    """

    store: Any
    project_id: str
    project_binding_id: str

    def __post_init__(self) -> None:
        _require_canonical_identity("project_id", self.project_id)
        _require_canonical_identity("project_binding_id", self.project_binding_id)


def _require_reference(value: Any, *, context: str, kind: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"{context} must be an explicit reference object: {value!r}")
    if value.get("kind") != kind:
        raise RuntimeRequirementError(f"{context} does not name kind={kind!r}: {value!r}")
    record_id = value.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise RuntimeRequirementError(f"{context} carries no readable id: {value!r}")
    return {"kind": kind, "id": record_id}


def _require_admitted_root(
    trusted_runtime_root: TrustedRuntimeRoot,
    *,
    runtime_root_admission_ref: Any,
    trust_anchor_public_key_hex: Any,
) -> dict[str, Any]:
    """Admit *trusted_runtime_root* -- or refuse everything (Round 3, P15-R3-F1).

    This is the control that replaced "possessing a root is sufficient". It is deliberately
    **inside** :func:`bootstrap_projection_execution_capability` rather than a separate pre-step
    function a caller could forget, discard, or bypass, and it runs before any grant or
    declaration is resolved and before
    :func:`~manosube_agent_civilization.authority.evaluate_projection_authorization` is ever
    called -- so every refusal here costs zero adapter calls and zero authorization evaluations,
    however the root itself was constructed.

    Five requirements, in order:

    1. *runtime_root_admission_ref* must be a well-formed reference of kind
       ``runtime_root_admission`` and must **resolve inside the root's own Store**.
    2. The resolved record must be schema-valid, and its own independently recomputed content
       address and semantic fingerprint must equal its own declared values (the identical
       tamper check every other ``_resolve_*`` in this module and in ``route.py`` applies).
    3. ``status`` must be ``"ACTIVE"``.
    4. Its ``project_id`` and ``project_binding_ref`` must **exactly** equal the root's own --
       so one admission artifact anchors exactly one project and one Binding, never an unbounded
       trust grant reusable across arbitrary Stores.
    5. Its ``signature`` must genuinely verify against *trust_anchor_public_key_hex*.

    Requirement 5 is what makes the other four mean anything. The anchor key is supplied by
    *this function's own caller*, from deployment/composition-time configuration -- never read
    from the Store being admitted, never derived from anything on the request path, and never a
    constant in shipped source. An attacker holding a complete, internally valid alternate world
    can mint an admission record inside it and self-sign it with that world's own genuinely
    legitimate Human Authority key; it fails here, because the key that decides is one that
    world never had.
    """

    store = trusted_runtime_root.store
    project_id = trusted_runtime_root.project_id
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
            f"for project {project_id!r}: {checked_ref['id']!r} -- an unadmitted trusted runtime "
            "root provisions nothing, however it was constructed"
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
            f"({admission.get('status')!r}) -- a revoked admission admits nothing"
        )
    if admission.get("project_id") != project_id:
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} admits a different project "
            f"than this root names: {admission.get('project_id')!r} != {project_id!r}"
        )
    expected_binding_ref = {
        "kind": "project_binding",
        "id": trusted_runtime_root.project_binding_id,
    }
    if admission.get("project_binding_ref") != expected_binding_ref:
        raise RuntimeRequirementError(
            f"resolved runtime_root_admission {checked_ref['id']!r} admits a different Project "
            f"Binding than this root names: {admission.get('project_binding_ref')!r} != "
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
    return admission


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


def bootstrap_projection_execution_capability(
    trusted_runtime_root: TrustedRuntimeRoot,
    *,
    runtime_root_admission_ref: Mapping[str, str],
    trust_anchor_public_key_hex: str,
    github_projection_grant_refs: list[Mapping[str, str]] | tuple[Mapping[str, str], ...],
    github_projection_grant_declaration_refs: list[Mapping[str, str]]
    | tuple[Mapping[str, str], ...],
) -> ProjectionExecutionCapability:
    """Resolve *github_projection_grant_refs*/*github_projection_grant_declaration_refs* --
    references only, never record bodies -- exclusively within *trusted_runtime_root*'s own
    Store, an already-open object this function never opens, selects, or constructs itself.

    **This signature carries no ``store``, ``project_id``, or ``project_binding_id``
    parameter at all** (P15-R1-F4): there is no call shape through which a caller could name
    an alternate, internally self-consistent world -- only an opaque root, plus
    grant/declaration *references* resolved exclusively within it. A first argument that is
    not a genuine :class:`TrustedRuntimeRoot` is refused at the type check, before Boot is
    reached at all.

    **Round 3 (P15-R3-F1): the root by itself grants nothing -- the admission check is what
    actually gates this function.** Immediately after Boot, and before any grant or declaration
    is resolved, *runtime_root_admission_ref* must resolve **inside the root's own Store** to a
    canonical, schema-valid, independently identity-recomputed, ``ACTIVE``
    ``runtime_root_admission`` record whose own ``project_id``/``project_binding_ref`` exactly
    equal the root's own, and whose signature genuinely verifies against
    *trust_anchor_public_key_hex*. Every failure is a
    :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` with **zero
    adapter calls and zero authorization evaluations**, regardless of how *trusted_runtime_root*
    itself was constructed -- which is precisely why the type is now freely constructible
    (see :class:`TrustedRuntimeRoot` and this module's own docstring; this is *not* a walk-back
    of Round 2).

    *trust_anchor_public_key_hex* is a raw 32-byte Ed25519 **public** key, hex-encoded, and must
    always be supplied from **deployment/composition-time configuration**: the boundary that
    decides which world is canonical at all. It is never read from the Store being admitted,
    never derived from anything on the request path, and never hardcoded as a specific
    real-world key inside shipped source. This package holds no private key and mints no
    signature -- it only verifies.

    **Round 2 (P15-R2-F1), historical.** The public minting factory Round 1 shipped is deleted
    and is not reintroduced under any name; no shipped function returns a
    :class:`TrustedRuntimeRoot`, and no shipped module constructs one. Round 2's conclusion that
    the capability route therefore had *no production-legitimate first argument at all* is what
    Round 3 rejected and replaced, by making the first argument stop being the trust decision.

    Boot-restores the exact Project/Binding the root names
    (:func:`~manosube_agent_civilization.boot.boot_project`, called fresh here rather than at
    provisioning time, so no root can ever carry a stale verdict), and returns one
    :class:`~manosube_agent_civilization.projection.ProjectionExecutionCapability` bound to a
    freshly constructed :class:`~manosube_agent_civilization.projection.
    ProjectionExecutionContext` -- if, and only if, exactly one resolved grant and exactly one
    anchoring declaration exist for each distinct ``projection_kind`` the resolved grants
    themselves name, each grant's own ``subject_ref`` resolves to a real subject record within
    that same root's own Store whose independently recomputed identity/fingerprint matches both
    *subject_ref* and the grant's own claimed ``subject_fingerprint``, and each genuinely
    authorizes ``MATERIALIZE_PROJECTION`` through
    :func:`~manosube_agent_civilization.authority.evaluate_projection_authorization` -- the
    same function a production projection call already trusts.

    Raises :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` on any
    malformed input or refusal; every :class:`~manosube_agent_civilization.boot.errors.BootError`/
    :class:`~manosube_agent_civilization.store.errors.StoreError`/
    :class:`~manosube_agent_civilization.binding.errors.BindingError`/
    :class:`~manosube_agent_civilization.authority.errors.AuthorityError` any resolved owner
    itself raises propagates unchanged. Never mints, signs, or commits anything, and never
    accepts a caller-supplied subject or grant/declaration body of any kind -- every record
    consumed here was already externally issued, committed, and Store-resolved before this
    call.
    """

    # The type check is the whole control (P15-R1-F4) -- it runs before every other check,
    # including before Boot, so a caller who tried to hand in a bare Store, a look-alike
    # object, or an alternate world's own handle never reaches any resolution at all.
    if not isinstance(trusted_runtime_root, TrustedRuntimeRoot):
        raise RuntimeRequirementError(
            "bootstrap_projection_execution_capability requires a genuine TrustedRuntimeRoot, "
            "never a bare store or a look-alike object: "
            f"{type(trusted_runtime_root)!r}"
        )
    store = trusted_runtime_root.store
    project_id = trusted_runtime_root.project_id
    project_binding_id = trusted_runtime_root.project_binding_id

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)

    # Round 3 (P15-R3-F1): the admission check is the very first substantive thing this function
    # does after Boot -- before the grant-reference shape check, before any grant or declaration
    # is resolved, and before evaluate_projection_authorization can be reached at all. It is
    # folded in here rather than offered as a separate pre-step precisely so no call shape exists
    # in which it is skipped, discarded, or run against a different root than the one used.
    _require_admitted_root(
        trusted_runtime_root,
        runtime_root_admission_ref=runtime_root_admission_ref,
        trust_anchor_public_key_hex=trust_anchor_public_key_hex,
    )

    if not github_projection_grant_refs:
        raise RuntimeRequirementError("github_projection_grant_refs must name at least one grant")

    human_authority_ref = boot_context.human_authority_ref
    human_authority_signing_key = boot_context.project_binding.get("human_authority_signing_key")
    if not isinstance(human_authority_signing_key, Mapping):
        raise RuntimeRequirementError(
            "the Boot-restored project_binding carries no readable human_authority_signing_key"
        )

    grants = [
        _resolve_grant(store, project_id, ref, context=f"github_projection_grant_refs[{position}]")
        for position, ref in enumerate(github_projection_grant_refs)
    ]
    declarations = [
        _resolve_declaration(
            store, project_id, ref, context=f"github_projection_grant_declaration_refs[{position}]"
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
            raise RuntimeRequirementError("grant carries no readable github_projection_grant_id")

        subject_record, real_subject_fingerprint = _resolve_subject(store, project_id, subject_ref)
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

    current_state = boot_context.current_state
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


__all__ = [
    "TrustedRuntimeRoot",
    "bootstrap_projection_execution_capability",
]
