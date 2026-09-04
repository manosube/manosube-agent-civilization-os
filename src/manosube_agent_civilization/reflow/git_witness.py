"""Pure verification of an immutable Git object witness -- R4-F3 (Phase 7 round 4).

CLOSURE_POLICY.md's G19 section requires ``APPLICABLE_V0_1_MANDATORY_INVARIANTS`` to bind
to the exact ``kernel_source_ref_evaluated.commit_sha``/``tree_sha`` a candidate was
evaluated against -- proving the pinned ``KERNEL_INVARIANTS_BLOB_SHA``
(:mod:`.invariant_registry`) is not merely *a* copy of the file, but the exact blob that
commit's tree names at ``00_KERNEL/KERNEL_INVARIANTS.md``. Structural review round 4
(``R4_F3_GIT_PROVENANCE=PURE_IMMUTABLE_GIT_OBJECT_WITNESS``) rejects the three weaker
alternatives named in round 3's escalation: this module never reads the filesystem or a
live Git object database (``LIVE_FILESYSTEM_AS_SEMANTIC_AUTHORITY=false``), never trusts a
caller's bare claim about what a commit/tree contains
(``CALLER_ASSERTION_ONLY_ALLOWED=false``), and is never optional or degrading
(``OPTIONAL_OR_DEGRADING_PROVENANCE_ALLOWED=false``).

What makes a *pure* verification possible at all: a Git object's own id is nothing but the
SHA-1 of its own header-prefixed bytes (``git hash-object``'s definition, not a Reflow
invention). A caller supplies the raw immutable object bytes for exactly the
commit/tree/.../blob chain ``GIT_PROOF_REQUIRED_GRAPH=COMMIT_TO_TREE_TO_PATH_TO_BLOB``
names, and this module only ever recomputes each object's own content address and walks
the path graph the objects *themselves* assert (a tree object's own entries, a commit
object's own ``tree`` line) -- the same content-addressed-witness pattern every other
identity in this vertical already uses, applied to Git's own object model instead of this
Kernel's domain-separated SHA-256 profiles. A witness that does not independently
recompute to the exact pinned ``commit_sha``/``tree_sha``/``blob_sha`` proves nothing and is
refused; there is no partial credit for "close" or "probably".
"""

from __future__ import annotations

import hashlib
from typing import Any

from .errors import ReflowValidationError


def _git_object_sha1(kind: bytes, content: bytes) -> str:
    """Return the Git object id: SHA-1 of ``"<kind> <len>\\0" + content`` -- Git's own
    content-addressing definition, unrelated to this Kernel's own SHA-256 profiles and
    never used here for anything but reproducing Git's own object identity.
    """

    header = kind + b" " + str(len(content)).encode("ascii") + b"\0"
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324 - Git's own object-naming hash


def blob_sha1(content: bytes) -> str:
    return _git_object_sha1(b"blob", content)


def tree_sha1(content: bytes) -> str:
    return _git_object_sha1(b"tree", content)


def commit_sha1(content: bytes) -> str:
    return _git_object_sha1(b"commit", content)


def parse_tree_entries(tree_object: bytes) -> dict[str, tuple[str, str]]:
    """Return ``{name: (mode, sha1_hex)}`` for one raw Git tree object's own entries.

    A tree object's wire format is a flat sequence of ``"<mode> <name>\\0<20-byte-sha1>"``
    entries with no separator between them -- parsed here byte-for-byte, not assumed.
    """

    entries: dict[str, tuple[str, str]] = {}
    index = 0
    length = len(tree_object)
    while index < length:
        space = tree_object.find(b" ", index)
        if space == -1:
            raise ReflowValidationError("malformed git tree object: missing mode separator")
        mode = tree_object[index:space].decode("ascii", errors="strict")
        nul = tree_object.find(b"\0", space + 1)
        if nul == -1:
            raise ReflowValidationError("malformed git tree object: missing name terminator")
        name = tree_object[space + 1 : nul].decode("utf-8", errors="strict")
        sha_bytes = tree_object[nul + 1 : nul + 21]
        if len(sha_bytes) != 20:
            raise ReflowValidationError("malformed git tree object: truncated entry sha")
        if name in entries:
            raise ReflowValidationError(f"malformed git tree object: duplicate entry {name!r}")
        entries[name] = (mode, sha_bytes.hex())
        index = nul + 21
    return entries


def parse_commit_tree_sha(commit_object: bytes) -> str:
    """Return the ``tree <sha>`` header line's sha from a raw Git commit object."""

    text = commit_object.decode("utf-8", errors="strict")
    for line in text.splitlines():
        if line == "":
            break
        if line.startswith("tree "):
            candidate = line[len("tree ") :].strip()
            if len(candidate) != 40 or any(c not in "0123456789abcdef" for c in candidate):
                raise ReflowValidationError("malformed git commit object: invalid tree line")
            return candidate
    raise ReflowValidationError("malformed git commit object: no tree header line found")


def _decode_hex_field(witness: dict[str, Any], key: str) -> bytes:
    value = witness.get(key)
    if not isinstance(value, str) or not value:
        raise ReflowValidationError(f"kernel_source_witness.{key} must be a non-empty hex string")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ReflowValidationError(f"kernel_source_witness.{key} is not valid hex") from error


def verify_kernel_source_witness(
    *,
    witness: dict[str, Any],
    expected_commit_sha: str,
    expected_tree_sha: str,
    expected_blob_sha: str,
    path: str,
) -> None:
    """Prove ``COMMIT -> TREE -> PATH -> BLOB`` from *witness* alone, or fail closed.

    *witness* is the caller-supplied bundle: ``{"commit_object": <hex>, "tree_objects":
    {<tree_sha_hex>: <hex>, ...}, "blob_object": <hex>}`` -- every referenced object's raw
    bytes, hex-encoded for JSON transport. Verified, in order:

    1. ``commit_object`` independently hashes to *expected_commit_sha*.
    2. The commit object's own ``tree`` line names *expected_tree_sha* -- not a caller
       assertion, the commit object's own asserted content.
    3. Each path segment of *path* resolves through a chain of tree objects supplied in
       ``tree_objects``, keyed by each tree's own sha -- each tree object independently
       hashes to its own key before its entries are trusted, and the final segment's
       resolved blob sha must equal *expected_blob_sha* exactly.
    4. ``blob_object`` independently hashes to *expected_blob_sha*.

    Any missing object, any object whose recomputed hash does not equal its own claimed
    key, any path segment absent from its parent tree, or any final blob sha mismatch
    raises :class:`~manosube_agent_civilization.reflow.errors.ReflowValidationError`.
    """

    commit_object = _decode_hex_field(witness, "commit_object")
    if commit_sha1(commit_object) != expected_commit_sha:
        raise ReflowValidationError(
            "kernel_source_witness.commit_object does not hash to the expected commit_sha"
        )
    commit_tree_sha = parse_commit_tree_sha(commit_object)
    if commit_tree_sha != expected_tree_sha:
        raise ReflowValidationError(
            "kernel_source_witness.commit_object's own tree does not match the expected tree_sha"
        )

    tree_objects = witness.get("tree_objects")
    if not isinstance(tree_objects, dict):
        raise ReflowValidationError("kernel_source_witness.tree_objects must be an object")

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        raise ReflowValidationError("kernel_source_witness path must be non-empty")

    current_sha = expected_tree_sha
    for position, segment in enumerate(segments):
        raw = tree_objects.get(current_sha)
        if not isinstance(raw, str):
            raise ReflowValidationError(
                f"kernel_source_witness.tree_objects is missing tree object {current_sha}"
            )
        try:
            tree_bytes = bytes.fromhex(raw)
        except ValueError as error:
            raise ReflowValidationError(
                f"kernel_source_witness.tree_objects[{current_sha!r}] is not valid hex"
            ) from error
        if tree_sha1(tree_bytes) != current_sha:
            raise ReflowValidationError(
                f"kernel_source_witness tree object does not hash to its own claimed key: {current_sha}"
            )
        entries = parse_tree_entries(tree_bytes)
        entry = entries.get(segment)
        if entry is None:
            raise ReflowValidationError(
                f"kernel_source_witness tree {current_sha} has no entry for path segment {segment!r}"
            )
        _mode, current_sha = entry
        if position == len(segments) - 1 and current_sha != expected_blob_sha:
            raise ReflowValidationError(
                "kernel_source_witness path resolves to a blob other than the pinned blob_sha"
            )

    blob_object = _decode_hex_field(witness, "blob_object")
    if blob_sha1(blob_object) != expected_blob_sha:
        raise ReflowValidationError(
            "kernel_source_witness.blob_object does not hash to the expected blob_sha"
        )
