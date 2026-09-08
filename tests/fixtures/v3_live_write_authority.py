"""Genuine, canonically-issuable SHUKOU/Human Authority for V3 live-write execution
(Structural Review Round 6, Issue #62, P14-R6-F2; external trust anchor, Round 7, P14-R7-F1;
canonical issuable authority, Round 8, P14-R8-F1).

Round 6 replaced a caller-computable digest with a genuinely Ed25519-signed record, but kept
the matching private key in the same importable module as the verifier. Round 7 removed that
private key entirely, replacing it with a fixed public trust anchor whose matching private key
was deliberately generated once and discarded -- closing self-issuance, but in the wrong
direction: with no possible legitimate issuer either, the gate could never be activated even by
a genuine future SHUKOU decision, and the "genuine record" it verified was never itself routed
through any canonical Authority/Binding owner.

Structural Review Round 8 corrects both defects at once by **reusing the existing canonical
Project Binding / Human Authority / signed Grant Declaration / Authority Decision route
verbatim** -- the identical mechanism :func:`~manosube_agent_civilization.authority.
projection_authorization.evaluate_projection_authorization` already provides for every real
GitHub projection operation (Structural Review Round 1, P14-R1-F1; signed declaration anchor,
Round 2, P14-R2-F1) -- rather than inventing any V3-specific verification mechanism, schema, or
trust anchor of its own.

This module holds no private key, no signing helper, and no V3-specific action literal: it
consumes a real, content-address-verifiable ``project_binding`` record (whose own
``human_authority_signing_key`` names the one public key ever consulted -- exactly the
discipline :mod:`manosube_agent_civilization.binding.signature`'s own docstring already states:
"the Human's own private key never touches this system at all, only the public verification
key") plus ``github_projection_grant``/``github_projection_grant_declaration`` records SHUKOU
externally signs against that same key, and asks the real Authority owner
(:func:`~manosube_agent_civilization.authority.projection_authorization.
evaluate_projection_authorization`) whether they authorize ``MATERIALIZE_PROJECTION`` -- the
one closed action literal every real projection call already uses -- for a V3-configuration-
shaped subject, independently for each of the three projection kinds the V3 harness exercises.

No new Authority owner, private-key registry, signing service, or persistence surface is
created here: the only new concept is *what subject* is being authorized (the V3 target
configuration itself, addressed by its own ``configuration_fingerprint``), never *how* that
authorization is verified.

This module is deliberately test/harness-only, exactly as :mod:`tests.fixtures.
v3_target_configuration` already is for the configuration it binds -- a genuine live grant
must still be issued entirely outside this repository, by whoever genuinely holds the real
Project Binding's Human Authority private key.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
from typing import Any

from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.authority.projection_authorization import (
    evaluate_projection_authorization,
)
from manosube_agent_civilization.binding.errors import BindingIdentityError
from manosube_agent_civilization.binding.identity import verify_project_binding_identity

from .v3_target_configuration import V3TargetConfiguration

#: The one closed permitted-action literal every real GitHub projection operation already uses
#: (``authority/projection_authorization.py``'s own ``_PERMITTED_ACTIONS``) -- V3's own live
#: execution authorizes ``MATERIALIZE_PROJECTION`` exactly as a production projection call
#: does. No V3-specific action literal exists, and none is introduced here.
V3_PERMITTED_ACTION = "MATERIALIZE_PROJECTION"

#: The subject kind this module's own V3-configuration-shaped ``subject_ref`` names --
#: distinct from ``"difference"``/``"change"``/``"observation_evidence"``, the subject kinds a
#: *production* projection's own ``subject_ref`` names, so a V3 harness's own grant/
#: declaration/decision can never be mistaken for -- or substituted into -- a production
#: projection's own authorization, and vice versa.
V3_CONFIGURATION_SUBJECT_KIND = "v3_target_configuration"

#: Every projection kind the V3 harness exercises. An authorized V3 execution requires an
#: independent ``evaluate_projection_authorization`` ``PROJECTION_AUTHORIZED`` decision for
#: *each* of these -- one grant standing in for all three is never sufficient.
V3_PROJECTION_KINDS: tuple[str, ...] = (
    "DIFFERENCE_ISSUE",
    "CHANGE_PULL_REQUEST",
    "EVIDENCE_ARTIFACT",
)

#: The environment variable carrying the complete, JSON-encoded V3 live-write authority
#: material: a real, content-address-verifiable ``project_binding`` record, plus the
#: ``github_projection_grant``/``github_projection_grant_declaration`` records SHUKOU
#: externally signed against that project_binding's own ``human_authority_signing_key`` --
#: never a parallel, ad-hoc record shape (Structural Review Round 8, P14-R8-F1, superseding
#: Round 6/7's own now-removed ``V3_LIVE_WRITE_AUTHORITY_RECORD_ENV``/``V3_LIVE_TRUST_ANCHOR``).
V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV = "MANOSUBE_P14_V3_LIVE_WRITE_AUTHORITY_MATERIAL"


def v3_configuration_subject_ref(config: V3TargetConfiguration) -> dict[str, str]:
    """The V3-configuration-shaped ``subject_ref`` every grant/declaration/decision this
    module consumes must name -- content-addressed by the configuration's own
    ``configuration_fingerprint`` (already covering every bound field: repository, refs, SHA,
    artifact kinds/count, naming, cleanup, no-merge -- see ``v3_target_configuration.py``)."""

    return {"kind": V3_CONFIGURATION_SUBJECT_KIND, "id": config.configuration_fingerprint}


def v3_projection_authorization_request(
    config: V3TargetConfiguration,
    *,
    projection_kind: str,
    project_id: str,
    human_authority_ref: Mapping[str, Any],
    human_authority_signing_key: Mapping[str, Any],
    grants: list[Any],
    grant_declarations: list[Any],
) -> dict[str, Any]:
    """One exact ``evaluate_projection_authorization`` request binding *config* and
    *projection_kind* -- the identical request shape a production projection call builds,
    applied here to the V3-configuration subject instead of a Difference/Change/Evidence one."""

    return {
        "schema_version": "0.1",
        "project_id": project_id,
        "subject_ref": v3_configuration_subject_ref(config),
        "subject_fingerprint": config.configuration_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(config.target_repository),
        "payload_fingerprint": config.configuration_fingerprint,
        "permitted_action": V3_PERMITTED_ACTION,
        "human_authority_ref": dict(human_authority_ref),
        "human_authority_signing_key": dict(human_authority_signing_key),
        "grants": list(grants),
        "grant_declarations": list(grant_declarations),
    }


def load_v3_live_write_authority_material(
    env: Mapping[str, str] | None = None,
) -> Mapping[str, Any] | None:
    """Read and JSON-decode :data:`V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV`, or return ``None``
    if unset, unparseable, or not a JSON object -- the identical "malformed input is simply no
    authority, never an exception" discipline every other check here applies. *env* defaults
    to :data:`os.environ`; performs no network access, identically to
    :mod:`tests.fixtures.v3_target_configuration`. The one I/O boundary this module has."""

    source = env if env is not None else os.environ
    raw = source.get(V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV)
    if raw is None:
        return None
    try:
        material = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return material if isinstance(material, dict) else None


def _verified_project_binding(material: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Independently recompute *material*'s own ``project_binding``'s content address --
    never trust a caller-supplied ``human_authority_ref``/``human_authority_signing_key``
    directly; both are read only from a project_binding that reproduces its own claimed
    identity from its own declared fields."""

    project_binding = material.get("project_binding")
    if not isinstance(project_binding, Mapping):
        return None
    try:
        verify_project_binding_identity(dict(project_binding))
    except (BindingIdentityError, KeyError, TypeError):
        return None
    return project_binding


def v3_live_write_authorized(
    config: V3TargetConfiguration | None,
    material: Mapping[str, Any] | None,
) -> bool:
    """Whether *material* genuinely authorizes live V3 execution of *config*, through the
    identical canonical Authority/Binding route
    (:func:`~manosube_agent_civilization.authority.projection_authorization.
    evaluate_projection_authorization`) a real GitHub projection call already uses -- never a
    parallel, V3-only verification mechanism (Structural Review Round 8, P14-R8-F1).

    Requires, independently for *every* projection kind in :data:`V3_PROJECTION_KINDS`:

    - *material*'s own ``project_binding`` reproduces its own claimed ``project_binding_id``
      from its own declared fields
      (:func:`~manosube_agent_civilization.binding.identity.verify_project_binding_identity`)
      -- its ``human_authority_ref``/``human_authority_signing_key`` are read only from this
      verified record, never independently caller-supplied;
    - a ``github_projection_grant`` among *material*'s own ``grants`` binds exactly this
      V3-configuration subject/target/payload/action for this kind, is ``ACTIVE``, and is
      anchored by a matching, ``ACTIVE``, genuinely Ed25519-signed
      ``github_projection_grant_declaration`` -- verified by
      :func:`~manosube_agent_civilization.authority.projection_authorization.
      evaluate_projection_authorization` itself, the same function a production projection
      call already trusts.

    Performs no I/O and no network access of its own -- pure recomputation and delegation.
    ``config=None`` or *material* not even a mapping refuse immediately. A malformed grant,
    declaration, or request raises inside ``evaluate_projection_authorization`` as
    :class:`~manosube_agent_civilization.authority.errors.AuthorityError`; caught here and
    treated as refusal, since a live-write gate must never raise."""

    if config is None or not isinstance(material, Mapping):
        return False

    project_binding = _verified_project_binding(material)
    if project_binding is None:
        return False

    project_id = material.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        return False
    if project_binding.get("project_id") != project_id:
        return False

    grants = material.get("grants")
    grant_declarations = material.get("grant_declarations")
    if not isinstance(grants, list) or not isinstance(grant_declarations, list):
        return False

    human_authority_ref = project_binding.get("human_authority_ref")
    human_authority_signing_key = project_binding.get("human_authority_signing_key")
    if not isinstance(human_authority_ref, Mapping) or not isinstance(
        human_authority_signing_key, Mapping
    ):
        return False

    for projection_kind in V3_PROJECTION_KINDS:
        request = v3_projection_authorization_request(
            config,
            projection_kind=projection_kind,
            project_id=project_id,
            human_authority_ref=human_authority_ref,
            human_authority_signing_key=human_authority_signing_key,
            grants=grants,
            grant_declarations=grant_declarations,
        )
        try:
            decision = evaluate_projection_authorization(request)
        except AuthorityError:
            return False
        if decision["decision"] != "PROJECTION_AUTHORIZED":
            return False
    return True
