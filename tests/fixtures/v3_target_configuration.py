"""The real V3 GitHub target configuration (Structural Review Round 3, Issue #62, P14-R3-F3).

Round 2 replaced the V3 harness's own impossible hardcoded refs (``head_ref=
"agent/v3-harness"``, ``base_ref="main"``, ``head_sha="a" * 40``) with nothing -- they simply
stayed hardcoded, because no validated configuration object existed to source real values
from. Round 3 requires that gap closed: an explicit, validated configuration contract that
accepts the exact target repository, existing PR head/base refs, the real target commit SHA,
artifact naming, and an explicit cleanup/no-merge confirmation, entirely from the environment
-- so this file, and the V3 harness that reads it, can never accidentally default to a real
repository, and so that once a later round supplies genuine values, the three real-adapter
tests become executable *without any source edit* to this module or to the harness itself.

**Fail closed before any network access.** :func:`load_v3_target_configuration` performs pure,
local validation only -- no Store, no adapter, no ``urllib`` import anywhere in this module
(consistent with this package's own reserved-transport-surface discipline). Missing,
malformed, or internally inconsistent configuration raises :class:`V3ConfigurationError`
before the caller could ever reach a network call. The one exception is the *fully absent*
case: if every one of these variables is unset, :func:`load_v3_target_configuration` returns
``None`` rather than raising -- the expected, safe state of every CI and local environment
this delivery runs in. A *partially* configured environment (some variables set, others not,
or one malformed) is never silently treated as "unconfigured": it fails closed instead.

**Full frozen boundary, not merely a shape (Structural Review Round 4, Issue #62,
P14-R4-F3).** Round 3's own configuration validated repository/refs/SHA/naming but silently
discarded its own ``cleanup``/``no-merge`` confirmation booleans after checking them once, and
bound no ``artifact_kinds``/``artifact_count`` boundary at all -- so nothing downstream could
verify *which* artifact kinds, or how many artifacts, this authorization actually covers.
:class:`V3TargetConfiguration` now carries ``cleanup_confirmed``, ``no_merge_confirmed``,
``authorized_artifact_kinds``, and ``authorized_artifact_count`` as real fields of the
returned, bound configuration -- never checked-then-thrown-away.

**Live-write authority is separate from configuration validity, and is owned by a dedicated
module.** A fully valid, fully bound :class:`V3TargetConfiguration` still never itself
authorizes a live network call. Through Structural Review Round 5 (Issue #62, P14-R5-F2),
that authority was an unscoped-then-fingerprint-bound boolean owned by this module
(``v3_live_write_authorized``/``LIVE_WRITE_AUTHORIZED_ENV``) -- but a caller-computable
configuration digest is still not itself a Human Authority, only a shape a genuine one could
also satisfy. Structural Review Round 6 (Issue #62, P14-R6-F2) replaces it with a genuine,
Ed25519-signed V3 Live Write Authority record, verified against one fixed, non-caller-
controlled public key: see :mod:`tests.fixtures.v3_live_write_authority`, whose own
``v3_live_write_authorized(config, authority_record, evaluation_time=...)`` is what the V3
harness's own real-adapter tests now gate on (see
``test_v3_real_github_vertical_proof.py``'s own ``_v3_live_authorized``).
:attr:`V3TargetConfiguration.configuration_fingerprint` (below) remains this module's own
contribution to that binding -- the canonical, deterministic digest of every bound field
except the secret ``token`` -- now one of several fields a genuine authority record must
itself carry and be signed over, rather than the caller-supplied comparison value itself. The
two gates (configuration validity, live-write authority) remain deliberately decoupled:
configuration can be fully frozen and validated with live-write authority still withheld
(this delivery's own state), but never the reverse. ``V3_LIVE_EXTERNAL_WRITE_AUTHORITY=false``
remains this delivery's own state throughout.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import os
import re

from manosube_agent_civilization.projection.types import ARTIFACT_KINDS
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: One repository-relative identifier segment (an owner or a repo name) -- GitHub's own
#: allowed character set for both, conservatively: alphanumerics, hyphens, underscores, dots,
#: never empty, never starting/ending with a separator-adjacent empty segment.
_OWNER_OR_REPO_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")

#: A real Git commit SHA -- exactly 40 lowercase hex characters, the identical grammar this
#: repository's own ``test_source_freshness_drift_detection.py`` already uses for the same
#: real-world value.
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

#: A non-empty Git ref name -- deliberately permissive (refs may contain ``/``), but never
#: empty and never carrying control/whitespace characters a real ref name cannot contain.
_REF_PATTERN = re.compile(r"^[^\s\x00-\x1f]+$")

TARGET_REPOSITORY_ENV = "MANOSUBE_P14_V3_TARGET_REPOSITORY"
TOKEN_ENV = "MANOSUBE_P14_V3_GITHUB_TOKEN"  # noqa: S105 -- an env var *name*, not a secret
CHANGE_HEAD_REF_ENV = "MANOSUBE_P14_V3_CHANGE_HEAD_REF"
CHANGE_BASE_REF_ENV = "MANOSUBE_P14_V3_CHANGE_BASE_REF"
EVIDENCE_HEAD_SHA_ENV = "MANOSUBE_P14_V3_EVIDENCE_HEAD_SHA"
ARTIFACT_NAMING_PREFIX_ENV = "MANOSUBE_P14_V3_ARTIFACT_NAMING_PREFIX"
CLEANUP_CONFIRMED_ENV = "MANOSUBE_P14_V3_CLEANUP_CONFIRMED"
NO_MERGE_CONFIRMED_ENV = "MANOSUBE_P14_V3_NO_MERGE_CONFIRMED"
#: Comma-separated ``artifact_kind`` values (Structural Review Round 4, P14-R4-F3) this
#: authorization actually permits materializing -- binds the frozen boundary's own artifact
#: *kinds*, never left to whatever the harness happens to attempt.
AUTHORIZED_ARTIFACT_KINDS_ENV = "MANOSUBE_P14_V3_AUTHORIZED_ARTIFACT_KINDS"
#: The maximum total artifact count this authorization permits across the entire V3 run --
#: binds the frozen boundary's own artifact *count*, never left unbounded.
AUTHORIZED_ARTIFACT_COUNT_ENV = "MANOSUBE_P14_V3_AUTHORIZED_ARTIFACT_COUNT"

#: Every environment variable this configuration contract reads -- used both to detect the
#: fully-unconfigured case and to enumerate what a partially-configured environment is
#: missing.
ALL_V3_ENV_VARS: tuple[str, ...] = (
    TARGET_REPOSITORY_ENV,
    TOKEN_ENV,
    CHANGE_HEAD_REF_ENV,
    CHANGE_BASE_REF_ENV,
    EVIDENCE_HEAD_SHA_ENV,
    ARTIFACT_NAMING_PREFIX_ENV,
    CLEANUP_CONFIRMED_ENV,
    NO_MERGE_CONFIRMED_ENV,
    AUTHORIZED_ARTIFACT_KINDS_ENV,
    AUTHORIZED_ARTIFACT_COUNT_ENV,
)

#: The one literal value that counts as an explicit confirmation -- anything else (unset,
#: empty, ``"false"``, ``"yes"``, mixed case) fails closed rather than being coerced.
_CONFIRMED_LITERAL = "true"


class V3ConfigurationError(RuntimeError):
    """The V3 target configuration is missing, malformed, unfrozen, cross-repository, or
    internally inconsistent -- raised before any network access is ever attempted."""


@dataclass(frozen=True, slots=True)
class V3TargetConfiguration:
    """One fully validated, target-bound V3 configuration -- every value a real
    ``RealGitHubAdapter`` call against the frozen target boundary needs, and nothing this
    module did not itself validate.

    ``cleanup_confirmed``/``no_merge_confirmed`` and ``authorized_artifact_kinds``/
    ``authorized_artifact_count`` (Structural Review Round 4, Issue #62, P14-R4-F3) are real,
    bound fields of the returned configuration -- never validated once and then discarded, so
    a later caller can re-verify exactly what this frozen boundary actually authorizes rather
    than trusting that the check happened."""

    owner: str
    repo: str
    token: str
    change_head_ref: str
    change_base_ref: str
    evidence_head_sha: str
    artifact_naming_prefix: str
    cleanup_confirmed: bool
    no_merge_confirmed: bool
    authorized_artifact_kinds: frozenset[str]
    authorized_artifact_count: int

    @property
    def target_repository(self) -> dict[str, str]:
        return {"host": "github", "owner": self.owner, "repo": self.repo}

    @property
    def configuration_fingerprint(self) -> str:
        """The deterministic digest of every field this configuration binds *except* the
        secret ``token`` (Structural Review Round 5, Issue #62, P14-R5-F2) -- what
        :func:`v3_live_write_authorized` requires a caller's own authorization value to equal
        before treating this exact configuration as live-write authorized. Changing any one
        bound field (a different repository, a different SHA, a widened artifact count, a
        renamed naming prefix, a flipped cleanup/no-merge confirmation) changes this digest,
        so an authorization value copied for a prior configuration never silently carries over
        to a changed one."""

        payload = {
            "owner": self.owner,
            "repo": self.repo,
            "change_head_ref": self.change_head_ref,
            "change_base_ref": self.change_base_ref,
            "evidence_head_sha": self.evidence_head_sha,
            "artifact_naming_prefix": self.artifact_naming_prefix,
            "cleanup_confirmed": self.cleanup_confirmed,
            "no_merge_confirmed": self.no_merge_confirmed,
            "authorized_artifact_kinds": sorted(self.authorized_artifact_kinds),
            "authorized_artifact_count": self.authorized_artifact_count,
        }
        return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _require_nonempty(env_var: str, value: str | None) -> str:
    if value is None or not value.strip():
        raise V3ConfigurationError(
            f"{env_var} is required once any V3 configuration variable is set, but is "
            f"missing or empty: {value!r}"
        )
    return value.strip()


def load_v3_target_configuration(
    env: Mapping[str, str] | None = None,
) -> V3TargetConfiguration | None:
    """Return one fully validated :class:`V3TargetConfiguration`, or ``None`` if the V3
    target is genuinely unconfigured in this environment (every one of
    :data:`ALL_V3_ENV_VARS` unset) -- the safe, expected state of every CI and local
    environment this delivery runs in.

    Raises :class:`V3ConfigurationError` -- always before any network access -- the moment
    *any* required variable is set but another is missing, or any single value fails its own
    grammar/consistency check: a *partially* configured environment is never silently treated
    as unconfigured. *env* defaults to :data:`os.environ`; a caller may supply an explicit
    mapping instead (this module performs no I/O of its own either way) -- the identical
    dependency-injection shape :mod:`tests.fixtures.product_binding` already uses for its own
    deterministic fixtures.
    """

    source = env if env is not None else os.environ
    values = {key: source.get(key) for key in ALL_V3_ENV_VARS}
    if all(value is None for value in values.values()):
        return None

    owner_repo = _require_nonempty(TARGET_REPOSITORY_ENV, values[TARGET_REPOSITORY_ENV])
    if "/" not in owner_repo:
        raise V3ConfigurationError(f"{TARGET_REPOSITORY_ENV} must be 'owner/repo': {owner_repo!r}")
    owner, _, repo = owner_repo.partition("/")
    if "/" in repo:
        raise V3ConfigurationError(
            f"{TARGET_REPOSITORY_ENV} must name exactly one owner/repo pair, not a longer "
            f"path: {owner_repo!r}"
        )
    if not _OWNER_OR_REPO_PATTERN.match(owner) or not _OWNER_OR_REPO_PATTERN.match(repo):
        raise V3ConfigurationError(
            f"{TARGET_REPOSITORY_ENV} names an invalid owner/repo grammar: {owner_repo!r}"
        )

    token = _require_nonempty(TOKEN_ENV, values[TOKEN_ENV])

    change_head_ref = _require_nonempty(CHANGE_HEAD_REF_ENV, values[CHANGE_HEAD_REF_ENV])
    if not _REF_PATTERN.match(change_head_ref):
        raise V3ConfigurationError(
            f"{CHANGE_HEAD_REF_ENV} is not a well-formed ref name: {change_head_ref!r}"
        )
    change_base_ref = _require_nonempty(CHANGE_BASE_REF_ENV, values[CHANGE_BASE_REF_ENV])
    if not _REF_PATTERN.match(change_base_ref):
        raise V3ConfigurationError(
            f"{CHANGE_BASE_REF_ENV} is not a well-formed ref name: {change_base_ref!r}"
        )
    if change_head_ref == change_base_ref:
        raise V3ConfigurationError(
            "change_head_ref and change_base_ref must name distinct refs -- a Pull Request "
            f"cannot merge a ref into itself: both are {change_head_ref!r}"
        )

    evidence_head_sha = _require_nonempty(EVIDENCE_HEAD_SHA_ENV, values[EVIDENCE_HEAD_SHA_ENV])
    if not _COMMIT_SHA_PATTERN.match(evidence_head_sha):
        raise V3ConfigurationError(
            f"{EVIDENCE_HEAD_SHA_ENV} must be exactly 40 lowercase hex characters, a real "
            f"target commit SHA -- never a placeholder: {evidence_head_sha!r}"
        )

    artifact_naming_prefix = _require_nonempty(
        ARTIFACT_NAMING_PREFIX_ENV, values[ARTIFACT_NAMING_PREFIX_ENV]
    )

    cleanup_confirmed = values[CLEANUP_CONFIRMED_ENV]
    if cleanup_confirmed != _CONFIRMED_LITERAL:
        raise V3ConfigurationError(
            f"{CLEANUP_CONFIRMED_ENV} must be the exact literal {_CONFIRMED_LITERAL!r} to "
            f"explicitly confirm the cleanup boundary -- refusing an unconfirmed or "
            f"ambiguous value: {cleanup_confirmed!r}"
        )
    no_merge_confirmed = values[NO_MERGE_CONFIRMED_ENV]
    if no_merge_confirmed != _CONFIRMED_LITERAL:
        raise V3ConfigurationError(
            f"{NO_MERGE_CONFIRMED_ENV} must be the exact literal {_CONFIRMED_LITERAL!r} to "
            f"explicitly confirm the no-merge boundary -- refusing an unconfirmed or "
            f"ambiguous value: {no_merge_confirmed!r}"
        )

    # Structural Review Round 4 (P14-R4-F3): bind exactly which artifact kinds, and how many
    # artifacts total, this authorization actually permits -- never left implicit.
    raw_artifact_kinds = _require_nonempty(
        AUTHORIZED_ARTIFACT_KINDS_ENV, values[AUTHORIZED_ARTIFACT_KINDS_ENV]
    )
    authorized_artifact_kinds = frozenset(
        kind.strip() for kind in raw_artifact_kinds.split(",") if kind.strip()
    )
    if not authorized_artifact_kinds or not authorized_artifact_kinds <= ARTIFACT_KINDS:
        raise V3ConfigurationError(
            f"{AUTHORIZED_ARTIFACT_KINDS_ENV} must be a non-empty, comma-separated list drawn "
            f"only from {sorted(ARTIFACT_KINDS)}: {raw_artifact_kinds!r}"
        )

    raw_artifact_count = _require_nonempty(
        AUTHORIZED_ARTIFACT_COUNT_ENV, values[AUTHORIZED_ARTIFACT_COUNT_ENV]
    )
    if not raw_artifact_count.isdigit() or int(raw_artifact_count) < 1:
        raise V3ConfigurationError(
            f"{AUTHORIZED_ARTIFACT_COUNT_ENV} must be a positive integer: {raw_artifact_count!r}"
        )
    authorized_artifact_count = int(raw_artifact_count)

    return V3TargetConfiguration(
        owner=owner,
        repo=repo,
        token=token,
        change_head_ref=change_head_ref,
        change_base_ref=change_base_ref,
        evidence_head_sha=evidence_head_sha,
        artifact_naming_prefix=artifact_naming_prefix,
        cleanup_confirmed=True,
        no_merge_confirmed=True,
        authorized_artifact_kinds=authorized_artifact_kinds,
        authorized_artifact_count=authorized_artifact_count,
    )
