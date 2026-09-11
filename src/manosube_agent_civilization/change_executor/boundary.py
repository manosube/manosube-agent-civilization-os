"""Strict inert-data canonicalization, the closed low-risk action vocabulary, and Execution
Boundary validation (Phase 18, Issue #73).

The canonicalizer below is deliberately duplicated from :mod:`manosube_agent_civilization.
url_boot.route`'s own ``_canonicalize_inert_adapter_identity`` rather than imported from it --
the established convention this repository already keeps for every package that needs the
identical strict-inert-data discipline (each package owns its own copy, so no package's own
trust boundary depends on another package's own implementation staying unchanged underneath
it). ``canonicalize_inert_data`` and :func:`deep_freeze` are deliberately two separate steps,
never merged into one function: :func:`deep_freeze` rebuilds ``dict``/``list`` into
``MappingProxyType``/``tuple``, and re-running the canonicalizer's own ``type(x) is dict``/
``type(x) is list`` checks against its own already-frozen output would spuriously refuse
genuinely safe, already-validated data (the exact bug closed in a prior Phase 17 round -- see
``url_boot/route.py``'s own docstring, Structural Review Round 5, P17-R5-F1).

**Composition-time worktree/repository/branch identity verification (Structural Review Round 2,
P18-R2-F2).** Structural Review Round 1 (P18-R1-F3) folded ``worktree_root`` inside the closed
Boundary itself, making it participate in the Boundary fingerprint -- but explicitly disclaimed
proving the directory it names is genuinely a checkout of that same Boundary's own declared
``repository``/``branch`` at all (this package still performs no ``subprocess``/network call, so
it could not previously invoke ``git`` to confirm that association). :func:`validate_execution_
boundary` now closes that gap, entirely through pure, local file reads of the worktree's own
``.git`` metadata -- no ``subprocess``, no network, preserving this package's own
static-conformance guarantee in full:

1. Resolve the real git directory: ``<worktree_root>/.git`` is either a directory (an ordinary
   checkout) directly, or a file (a linked ``git worktree``) whose one ``gitdir: <path>`` line is
   followed, resolving a relative path against *worktree_root*.
2. Read that git directory's own ``HEAD``: it must be ``ref: refs/heads/<branch>`` -- a detached
   HEAD (a bare SHA, no ``ref:`` prefix) fails closed, since it cannot prove a branch identity at
   all.
3. Resolve the *main* repository's own git directory -- for a linked worktree, its own
   ``commondir`` file names the real one, since only the main repository's own git directory
   carries a populated ``config`` (a linked worktree's own git directory does not) -- and read its
   ``config`` (plain INI, via :mod:`configparser`) for ``[remote "origin"] url``, normalized to
   the identical ``owner/repo`` slug form ``execution_boundary["repository"]`` already uses
   (handling both ``https://github.com/owner/repo.git`` and ``git@github.com:owner/repo.git``
   forms, and a bare already-normalized slug unchanged).
4. Require the parsed branch to equal ``execution_boundary["branch"]`` exactly, and the parsed
   repository slug to equal ``execution_boundary["repository"]`` exactly -- any mismatch,
   unparseable ``.git`` metadata, or missing ``.git`` entirely raises
   :class:`~manosube_agent_civilization.change_executor.errors.ExecutionBoundaryError`, at
   composition time, before any request-facing operation can even be obtained.

This closes the gap the prior round's own non-claim named (see ``CHANGE_EXECUTOR_CONTRACT.md``'s
corrected non-claim, which supersedes -- without deleting -- the prior round's own text); the
prior round's own structural claim (a *given* ``worktree_root`` binds to exactly one Boundary
fingerprint/slot) is unaffected and still holds in full.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import configparser
from datetime import datetime
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any

from manosube_agent_civilization.authority.levels import HUMAN_ONLY_ACTION_KINDS
from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as _CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .errors import ExecutionBoundaryError

#: This package's own schema namespace under the repository's single canonical schema root --
#: the identical ``CANONICAL_SCHEMA_BASE + "<package>/"`` convention every other owner
#: (``change/engine.py``, ``runtime/bootstrap.py``) already keeps.
CHANGE_EXECUTOR_SCHEMA_BASE = _CANONICAL_SCHEMA_BASE + "change_executor/"

#: Exact built-in scalar types :func:`canonicalize_inert_data` ever accepts as a leaf value --
#: checked by ``type(x) is <builtin>``, never ``isinstance``, so that a hostile subclass
#: overriding ``__eq__``/``__iter__``/``__getitem__``/a descriptor is refused outright rather
#: than silently accepted as "close enough" (the identical discipline ``url_boot/route.py``'s
#: own ``_INERT_SCALAR_TYPES`` documents in full).
_INERT_SCALAR_TYPES: tuple[type, ...] = (str, int, float, bool, type(None))


def canonicalize_inert_data(value: Any) -> Any:
    """Validate that *value* is genuinely closed, built-in plain data -- exact ``dict``/
    ``list``/``str``/``int``/``float``/``bool``/``None`` only, recursively -- then rebuild a
    genuinely fresh, alias-free copy from it. Returns a plain, still-mutable structure;
    freezing (:func:`deep_freeze`) is a separate, explicit step every caller performs itself.

    This function never calls ``getattr`` on *value* or any of its own nested contents, and
    never invokes a protocol method beyond genuine ``dict.items()``/``list`` iteration on a
    value already confirmed to be an *exact* built-in ``dict``/``list`` -- never a caller-
    defined descendant of one."""

    def _canonicalize(node: Any, path: str) -> Any:
        node_type = type(node)
        if node_type in _INERT_SCALAR_TYPES:
            return node
        if node_type is dict:
            return {
                _canonicalize_key(key, path): _canonicalize(item, f"{path}.{key!r}")
                for key, item in node.items()
            }
        if node_type is list:
            return [_canonicalize(item, f"{path}[{index}]") for index, item in enumerate(node)]
        raise ExecutionBoundaryError(
            f"value{path} is not genuinely closed plain data -- exact type {node_type!r} is "
            "not one of str/int/float/bool/None/dict/list; a Mapping subclass, iterator, "
            "descriptor, or any other caller-defined object is refused before it is ever read"
        )

    def _canonicalize_key(key: Any, path: str) -> str:
        if type(key) is not str:
            raise ExecutionBoundaryError(f"value{path} has a non-str key {key!r} ({type(key)!r})")
        return key

    return _canonicalize(value, "")


def deep_freeze(value: Any) -> Any:
    """Recursively rebuild *value* into an immutable, alias-free equivalent -- ``Mapping ->
    MappingProxyType``, ``Sequence`` (excluding ``str``/``bytes``) ``-> tuple``, any other
    scalar returned as-is. Deliberately duplicated rather than imported from
    :mod:`manosube_agent_civilization.boot.context`'s own ``_deep_freeze`` or any other
    package's own copy -- the identical decoupling every such copy in this repository already
    keeps."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(deep_freeze(item) for item in value)
    return value


#: The closed, low-risk action vocabulary this package will ever admit -- Issue #73's own
#: ``INITIAL_AUTONOMOUS_SCOPE`` (documentation, tests, isolated source, low-risk configuration),
#: expressed as the ``action_kind`` values a canonical Change may carry for this package to ever
#: consider executing it. Every member is checked, at module import time, to be disjoint from
#: :data:`~manosube_agent_civilization.authority.levels.HUMAN_ONLY_ACTION_KINDS` -- defense in
#: depth: this package's own Boundary refuses a Human-only action kind on its own terms, never
#: relying solely on the fact that Authority would already have refused it upstream.
PERMITTED_ACTION_KINDS: frozenset[str] = frozenset(
    {
        "WRITE_DOCUMENTATION_FILE",
        "WRITE_TEST_FILE",
        "WRITE_ISOLATED_SOURCE_FILE",
        "WRITE_LOW_RISK_CONFIGURATION_FILE",
        "DELETE_DOCUMENTATION_FILE",
        "DELETE_TEST_FILE",
        "DELETE_ISOLATED_SOURCE_FILE",
    }
)

assert not (PERMITTED_ACTION_KINDS & HUMAN_ONLY_ACTION_KINDS), (  # noqa: S101
    "PERMITTED_ACTION_KINDS must never overlap HUMAN_ONLY_ACTION_KINDS -- a low-risk, "
    "autonomous action vocabulary that named a Human-only action kind would not be low-risk"
)

#: Every key a closed Execution Boundary must carry, and no other -- ``additionalProperties:
#: false`` in spirit, exactly as :data:`~manosube_agent_civilization.change.engine.
#: REQUIRED_REQUEST_KEYS` closes Change's own request shape, and for the identical reason: an
#: ignored key is still a channel.
REQUIRED_BOUNDARY_KEYS: frozenset[str] = frozenset(
    {
        "permitted_action_kinds",
        "repository",
        "branch",
        "admitted_paths",
        "max_files_changed",
        "max_bytes_changed",
        "max_file_bytes",
        "permit_symlinks",
        "permit_path_traversal",
        "permit_network",
        "permit_subprocess",
        "permit_environment_mutation",
        "permit_credential_access",
        "timeout_seconds",
        "rollback_policy",
        "executor_identity",
        "executor_version",
        "validity_window",
        "worktree_root",
    }
)

#: The only ``rollback_policy`` values this package ever admits.
ROLLBACK_POLICIES: frozenset[str] = frozenset({"NONE", "BEST_EFFORT_DELETE_WRITTEN_FILES"})

#: Every Boundary field that must be exactly the Python value ``False`` -- schema-fixed, never a
#: caller-supplied toggle: this package never permits following/creating a symlink target,
#: traversing outside an admitted path, network access, subprocess execution, environment
#: mutation, or credential access as part of a low-risk operation, and a Boundary supplying
#: ``True`` for any of these is refused outright, not silently downgraded.
_FIXED_FALSE_KEYS: tuple[str, ...] = (
    "permit_symlinks",
    "permit_path_traversal",
    "permit_network",
    "permit_subprocess",
    "permit_environment_mutation",
    "permit_credential_access",
)

_POSITIVE_INT_KEYS: tuple[str, ...] = ("max_files_changed", "max_bytes_changed", "max_file_bytes")


def parse_utc_instant(value: Any, context: str) -> datetime:
    """Parse one RFC3339 ``Z``-suffixed UTC timestamp into a real, comparable instant -- the
    one instant-parsing owner this package has, the identical discipline
    :mod:`manosube_agent_civilization.url_boot.engine`'s own ``parse_utc_instant`` establishes:
    lexicographic string comparison over a timestamp grammar admitting an optional fractional
    part is unsound, so every timestamp-window comparison in this package goes through this one
    function."""

    if not isinstance(value, str) or not value:
        raise ExecutionBoundaryError(f"{context} must be a non-empty RFC3339 string: {value!r}")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ExecutionBoundaryError(
            f"{context} is not a readable UTC instant: {value!r}"
        ) from error
    if parsed.tzinfo is None:
        raise ExecutionBoundaryError(f"{context} carries no UTC designator: {value!r}")
    return parsed


def _require_admitted_relative_path(value: Any, *, context: str) -> str:
    """Require *value* to be a non-empty, genuinely relative POSIX-style path: no leading
    ``/``, no empty segment, and no ``..`` segment anywhere -- a real, segment-aware check, not
    a naive substring test a crafted path (``"a/..b"``, a literal two-character ``".."``
    embedded inside a longer segment) could defeat."""

    if type(value) is not str or not value:
        raise ExecutionBoundaryError(f"{context} must be a non-empty string path: {value!r}")
    if value.startswith("/"):
        raise ExecutionBoundaryError(f"{context} must be relative, not absolute: {value!r}")
    segments = value.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise ExecutionBoundaryError(
            f"{context} must contain no empty, '.', or '..' path segment: {value!r}"
        )
    return value


def path_is_admitted(candidate: str, admitted_paths: Sequence[str]) -> bool:
    """Whether *candidate* equals, or is genuinely nested under, some member of
    *admitted_paths* -- a real, segment-boundary-aware prefix check. Deliberately never a bare
    ``str.startswith``: comparing raw strings would let an admitted path ``"docs"`` wrongly
    admit a sibling directory named ``"docs-private"``, which shares the same first four
    characters but is not nested under ``"docs"`` at all. Comparison is performed on each
    path's own ``"/"``-separated segment tuple instead, so only a genuine ancestor-of segment
    relationship admits."""

    candidate_segments = tuple(candidate.split("/"))
    for admitted in admitted_paths:
        admitted_segments = tuple(admitted.split("/"))
        if candidate_segments[: len(admitted_segments)] == admitted_segments:
            return True
    return False


def _resolve_git_dir(worktree_root: Path) -> Path:
    """Resolve *worktree_root*'s own real git directory -- an ordinary ``.git`` directory
    directly, or (a linked ``git worktree``) the ``gitdir: <path>`` its own ``.git`` *file*
    names, resolved against *worktree_root* when relative."""

    dot_git = worktree_root / ".git"
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        try:
            content = dot_git.read_text(encoding="utf-8")
        except OSError as error:
            raise ExecutionBoundaryError(
                f"execution_boundary.worktree_root's own .git file could not be read: {error}"
            ) from error
        line = content.strip().splitlines()[0].strip() if content.strip() else ""
        prefix = "gitdir:"
        if not line.startswith(prefix):
            raise ExecutionBoundaryError(
                f"execution_boundary.worktree_root's own .git file is not a readable "
                f"'gitdir: <path>' pointer: {content!r}"
            )
        raw_path = line[len(prefix) :].strip()
        gitdir = Path(raw_path)
        gitdir = gitdir if gitdir.is_absolute() else worktree_root / gitdir
        gitdir = gitdir.resolve()
        if not gitdir.is_dir():
            raise ExecutionBoundaryError(
                f"execution_boundary.worktree_root's own .git file names a gitdir that does not "
                f"resolve to a real, existing directory: {gitdir}"
            )
        return gitdir
    raise ExecutionBoundaryError(
        "execution_boundary.worktree_root carries no .git entry at all -- cannot verify it is a "
        f"genuine git checkout of the Boundary's own declared repository/branch: {worktree_root}"
    )


def _read_head_branch(git_dir: Path) -> str:
    """Read *git_dir*'s own ``HEAD`` and require it to name a genuine local branch ref -- a
    detached HEAD (a bare commit SHA, no ``ref:`` prefix) fails closed, since it cannot prove a
    branch identity at all."""

    head_path = git_dir / "HEAD"
    if not head_path.is_file():
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own git directory carries no readable HEAD: "
            f"{git_dir}"
        )
    try:
        content = head_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own HEAD could not be read: {error}"
        ) from error
    prefix = "ref:"
    if not content.startswith(prefix):
        raise ExecutionBoundaryError(
            "execution_boundary.worktree_root is a detached HEAD checkout -- cannot prove a "
            f"branch identity: {content!r}"
        )
    ref = content[len(prefix) :].strip()
    branch_prefix = "refs/heads/"
    if not ref.startswith(branch_prefix):
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own HEAD does not point at a local branch ref: "
            f"{ref!r}"
        )
    branch = ref[len(branch_prefix) :]
    if not branch:
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own HEAD names an empty branch: {content!r}"
        )
    return branch


def _resolve_config_dir(git_dir: Path) -> Path:
    """Return the git directory that actually carries a populated ``config`` -- *git_dir*
    itself, unless it is a linked worktree's own git directory, in which case its own
    ``commondir`` file names the real, main repository's own git directory (a linked worktree's
    own git directory carries no ``[remote ...]`` sections of its own)."""

    commondir_path = git_dir / "commondir"
    if not commondir_path.is_file():
        return git_dir
    try:
        raw = commondir_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own commondir could not be read: {error}"
        ) from error
    common = Path(raw)
    common = common if common.is_absolute() else (git_dir / common)
    common = common.resolve()
    if not common.is_dir():
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own commondir does not resolve to a real, "
            f"existing directory: {common}"
        )
    return common


def _normalize_repository_slug(url: str) -> str:
    """Normalize a git remote URL to the bare ``owner/repo`` slug form
    ``execution_boundary["repository"]`` already uses -- handling
    ``https://github.com/owner/repo.git``, ``git@github.com:owner/repo.git``, and an
    already-bare ``owner/repo`` slug (passed through unchanged, only trimming a trailing
    ``.git``/``/``) alike."""

    value = url.strip()
    if value.endswith(".git"):
        value = value[: -len(".git")]
    if not value:
        raise ExecutionBoundaryError("execution_boundary.worktree_root's own remote url is empty")
    if "://" in value:
        _, _, rest = value.partition("://")
        _, _, path = rest.partition("/")
        if not path:
            raise ExecutionBoundaryError(
                f"execution_boundary.worktree_root's own remote url is not a readable "
                f"owner/repo URL: {url!r}"
            )
        return path.strip("/")
    if "@" in value and ":" in value:
        # scp-like syntax, e.g. git@github.com:owner/repo -- the slug is everything after the
        # first ':' (there is no '/'-only host/path split to make, unlike the '://' form above).
        _, _, rest = value.partition(":")
        if not rest:
            raise ExecutionBoundaryError(
                f"execution_boundary.worktree_root's own remote url is not a readable "
                f"scp-like owner/repo reference: {url!r}"
            )
        return rest.strip("/")
    return value.strip("/")


def _read_origin_remote_slug(config_dir: Path) -> str:
    config_path = config_dir / "config"
    if not config_path.is_file():
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own git config carries no readable file: "
            f"{config_path}"
        )
    parser = configparser.ConfigParser(strict=False)
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error as error:
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root's own git config is not readable INI: {error}"
        ) from error
    section = 'remote "origin"'
    if not parser.has_section(section):
        raise ExecutionBoundaryError(
            'execution_boundary.worktree_root\'s own git config carries no [remote "origin"] '
            "section -- cannot verify its own repository identity"
        )
    url = parser.get(section, "url", fallback=None)
    if not url:
        raise ExecutionBoundaryError(
            'execution_boundary.worktree_root\'s own [remote "origin"] carries no url'
        )
    return _normalize_repository_slug(url)


def _verify_worktree_repository_branch_identity(
    worktree_root: str, repository: str, branch: str
) -> None:
    """(P18-R2-F2) Require *worktree_root* to be a genuine git checkout of exactly *repository*/
    *branch* -- pure, local ``.git`` metadata file reads only, never ``subprocess``/network.
    Raises :class:`ExecutionBoundaryError` on any mismatch, unparseable metadata, or missing
    ``.git`` entirely; see this module's own docstring for the full mechanism."""

    root = Path(worktree_root)
    git_dir = _resolve_git_dir(root)
    actual_branch = _read_head_branch(git_dir)
    if actual_branch != branch:
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root is a git checkout of branch {actual_branch!r}, "
            f"not the Boundary's own declared branch {branch!r} -- refusing (P18-R2-F2)"
        )
    config_dir = _resolve_config_dir(git_dir)
    actual_repository = _read_origin_remote_slug(config_dir)
    if actual_repository != repository:
        raise ExecutionBoundaryError(
            'execution_boundary.worktree_root\'s own [remote "origin"] names repository '
            f"{actual_repository!r}, not the Boundary's own declared repository {repository!r} "
            "-- refusing (P18-R2-F2)"
        )


def validate_execution_boundary(raw: Any) -> dict[str, Any]:
    """Validate *raw* as a closed Execution Boundary, and return a fresh, canonical, plain
    (unfrozen) ``dict``. Every field required by :data:`REQUIRED_BOUNDARY_KEYS` is checked
    individually below; the result is additionally schema-validated against
    ``01_SCHEMA/change_executor/execution_boundary.schema.json`` before being returned, so the
    Python-level checks below and the shipped canonical schema can never silently drift apart.
    """

    canonical = canonicalize_inert_data(raw)
    if type(canonical) is not dict:
        raise ExecutionBoundaryError(f"execution_boundary must be a dict, not {type(raw)!r}")

    unknown = set(canonical) - REQUIRED_BOUNDARY_KEYS
    if unknown:
        raise ExecutionBoundaryError(f"execution_boundary carries unknown keys: {sorted(unknown)}")
    missing = REQUIRED_BOUNDARY_KEYS - set(canonical)
    if missing:
        raise ExecutionBoundaryError(f"execution_boundary omits required keys: {sorted(missing)}")

    permitted_action_kinds = canonical["permitted_action_kinds"]
    if (
        type(permitted_action_kinds) is not list
        or not permitted_action_kinds
        or len(set(permitted_action_kinds)) != len(permitted_action_kinds)
        or not all(
            type(kind) is str and kind in PERMITTED_ACTION_KINDS for kind in permitted_action_kinds
        )
    ):
        raise ExecutionBoundaryError(
            "execution_boundary.permitted_action_kinds must be a non-empty list of unique "
            f"members of PERMITTED_ACTION_KINDS: {permitted_action_kinds!r}"
        )

    for key in ("repository", "branch", "executor_identity", "executor_version"):
        value = canonical[key]
        if type(value) is not str or not value:
            raise ExecutionBoundaryError(f"execution_boundary.{key} must be a non-empty string")

    # worktree_root: folded into the closed Boundary itself (P18-R1-F3, Structural Review Round
    # 1) rather than a separate composition-time parameter alongside it -- validated the identical
    # way every other trust-sensitive string field above is, plus the one check specific to a
    # worktree root: it must resolve to a real, existing directory (moved here, verbatim, from
    # the prior round's own `route._require_existing_worktree_root`, since the identity now lives
    # in the Boundary). Because `execution_boundary_fingerprint` hashes the *entire* canonical
    # boundary dict, this single change makes worktree_root participate in the Boundary
    # fingerprint -- and therefore in every mapping-slot key derived from it -- automatically.
    worktree_root = canonical["worktree_root"]
    if type(worktree_root) is not str or not worktree_root:
        raise ExecutionBoundaryError("execution_boundary.worktree_root must be a non-empty string")
    if not Path(worktree_root).is_dir():
        raise ExecutionBoundaryError(
            f"execution_boundary.worktree_root must resolve to a real, existing directory: "
            f"{worktree_root!r}"
        )
    # (P18-R2-F2, Structural Review Round 2) worktree_root being an existing directory is
    # necessary but not sufficient -- require it to also be verified, via pure local .git
    # metadata reads, as a genuine checkout of this exact Boundary's own repository/branch.
    _verify_worktree_repository_branch_identity(
        worktree_root, canonical["repository"], canonical["branch"]
    )

    admitted_paths = canonical["admitted_paths"]
    if type(admitted_paths) is not list or not admitted_paths:
        raise ExecutionBoundaryError("execution_boundary.admitted_paths must be a non-empty list")
    checked_paths = [
        _require_admitted_relative_path(path, context=f"execution_boundary.admitted_paths[{index}]")
        for index, path in enumerate(admitted_paths)
    ]
    if len(set(checked_paths)) != len(checked_paths):
        raise ExecutionBoundaryError("execution_boundary.admitted_paths must not repeat a path")

    for key in (*_POSITIVE_INT_KEYS, "timeout_seconds"):
        value = canonical[key]
        if type(value) is not int or value <= 0:
            raise ExecutionBoundaryError(
                f"execution_boundary.{key} must be a positive integer: {value!r}"
            )

    for key in _FIXED_FALSE_KEYS:
        value = canonical[key]
        if value is not False:
            raise ExecutionBoundaryError(
                f"execution_boundary.{key} must be exactly False -- this package never permits "
                f"it, and a Boundary supplying {value!r} is refused rather than downgraded"
            )

    rollback_policy = canonical["rollback_policy"]
    if rollback_policy not in ROLLBACK_POLICIES:
        raise ExecutionBoundaryError(
            f"execution_boundary.rollback_policy must be one of {sorted(ROLLBACK_POLICIES)}: "
            f"{rollback_policy!r}"
        )

    validity_window = canonical["validity_window"]
    if type(validity_window) is not dict or set(validity_window) != {"issued_at", "expires_at"}:
        raise ExecutionBoundaryError(
            "execution_boundary.validity_window must carry exactly issued_at and expires_at"
        )
    issued_at = parse_utc_instant(
        validity_window["issued_at"], "execution_boundary.validity_window.issued_at"
    )
    expires_at = parse_utc_instant(
        validity_window["expires_at"], "execution_boundary.validity_window.expires_at"
    )
    if not issued_at < expires_at:
        raise ExecutionBoundaryError(
            "execution_boundary.validity_window is not a genuinely ordered window: "
            f"{validity_window['issued_at']!r} .. {validity_window['expires_at']!r}"
        )

    try:
        _validate_canonical_record(
            canonical, "execution_boundary.schema.json", base=CHANGE_EXECUTOR_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise ExecutionBoundaryError(f"execution_boundary is schema-invalid: {error}") from error

    return canonical


def execution_boundary_fingerprint(boundary: Mapping[str, Any]) -> str:
    """The content digest of a complete, canonical Execution Boundary -- ``"sha256:"`` plus the
    hex digest of :func:`~manosube_agent_civilization.state.canonicalize.canonical_json_bytes`
    over the *entire* boundary mapping (unlike a record's own semantic-field projection, a
    Boundary carries no identity field of its own to exclude)."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(dict(boundary))).hexdigest()


def require_within_time_window(boundary: Mapping[str, Any], instant: str) -> None:
    """Refuse before any adapter call unless *instant* falls within *boundary*'s own declared,
    genuinely ordered, closed ``validity_window`` -- compared as real UTC instants, mirroring
    :mod:`manosube_agent_civilization.url_boot.route`'s own ``_require_within_time_window``."""

    window = boundary["validity_window"]
    issued_at = parse_utc_instant(
        window["issued_at"], "execution_boundary.validity_window.issued_at"
    )
    expires_at = parse_utc_instant(
        window["expires_at"], "execution_boundary.validity_window.expires_at"
    )
    observed = parse_utc_instant(instant, "execution_instant")
    if not issued_at < expires_at:
        raise ExecutionBoundaryError(
            "execution_boundary.validity_window is not a genuinely ordered window -- refusing "
            "before any adapter call"
        )
    if not (issued_at <= observed <= expires_at):
        raise ExecutionBoundaryError(
            f"execution_instant {instant!r} falls outside the Boundary's own declared time "
            f"window [{window['issued_at']!r}, {window['expires_at']!r}] -- refusing before "
            "any adapter call"
        )


__all__ = [
    "CHANGE_EXECUTOR_SCHEMA_BASE",
    "PERMITTED_ACTION_KINDS",
    "REQUIRED_BOUNDARY_KEYS",
    "ROLLBACK_POLICIES",
    "canonicalize_inert_data",
    "deep_freeze",
    "execution_boundary_fingerprint",
    "parse_utc_instant",
    "path_is_admitted",
    "require_within_time_window",
    "validate_execution_boundary",
]
