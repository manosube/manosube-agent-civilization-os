"""The one Kernel-owned immutable canonical schema validation context (Phase 9 Binding
security hardening, Issue #75, ``D-KERNEL-VERIFIED-SCHEMA-BYTE-INJECTION``).

Every schema-validating owner in this package -- Observation, Binding, State, Store -- has
until now resolved the canonical ``01_SCHEMA`` set by *reading the filesystem again* at the
moment it needed a validator: :func:`~manosube_agent_civilization.observation.schemas.
validators` through a zero-argument ``lru_cache`` whose public ``cache_clear()`` permits a
reload, :func:`~manosube_agent_civilization.binding.validation._validators` through an
``lru_cache`` keyed by a *directory path*, and :func:`~manosube_agent_civilization.state.
canonicalize._schema_registry` through an uncached ``rglob`` on every single call. A caller
that has already captured and digest-verified the canonical schema bytes therefore had no
way to make those exact bytes be the bytes that actually validate anything:

``SCHEMA_PATH_EQUALITY_ALONE_IS_NOT_BYTE_IDENTITY=true`` -- pointing every
``schema_root``-accepting entry point at a freshly materialized copy of the verified buffers
narrows, but does not close, the verify/use window: the copy is still an owner-writable
filesystem read surface, still re-read after the digest, and the zero-argument registry
cannot be redirected at all. Pinning that cache is not byte identity either, because the
cache remains publicly reloadable.

:class:`CanonicalSchemaContext` is the one mechanism that closes it. It is constructed once,
by Kernel code, from a closed mapping of *relative path -> captured bytes*; it parses those
exact bytes and constructs every :class:`jsonschema.Draft202012Validator` immediately; and it
then exposes **validation operations only** -- never a schema document, never a mutable
mapping, never a reload, cache-clear, or fall-back-to-filesystem path:

``VERIFIED_SCHEMA_BYTES_ARE_VALIDATION_BYTES=true``.

After construction succeeds, nothing that happens to the original ``01_SCHEMA`` tree, to any
materialized copy, to the current working directory, to import-relative paths, or to the
caller's own input mapping can alter a single validation outcome in that context
(``SCHEMA_FILESYSTEM_READ_COUNT_AFTER_CONTEXT_CONSTRUCTION=0``). The secure route never
requires materializing schemas to a path at all.

There is exactly one such owner (``PARALLEL_SCHEMA_OWNER=false``). This module deliberately
lives at the top level, sibling to every domain package and to :mod:`~manosube_agent_
civilization.topology`, for the same reason that module gives: the canonical ``01_SCHEMA``
set is not owned by any one domain, and a context every domain must be able to accept cannot
live inside one of them without inverting the established package layering. It imports no
domain module at all, so it participates in no dependency cycle.

Schema *meaning* and *identity* remain exactly where they already were
(``SCHEMA_MEANING_CHANGE=false``, ``SCHEMA_RELAXATION=false``): this module decides nothing
about what any schema says, only about which bytes the already-canonical schemas are read
from -- once, up front, under the caller's own verified digest.

Public surface (the documented downstream integration route):

.. code-block:: python

    from pathlib import Path

    from manosube_agent_civilization.schema_context import (
        CanonicalSchemaContext,
        capture_canonical_schema_bytes,
        schema_set_digest,
    )

    captured = capture_canonical_schema_bytes(Path("01_SCHEMA"))  # the one filesystem read
    adopted_digest = schema_set_digest(captured)  # verify against your own pinned value
    context = CanonicalSchemaContext(captured, expected_digest=adopted_digest)

    store = FileStateStore(backend_root, schema_context=context)
    bind_project(store, ..., schema_context=context)

No private function, ``lru_cache`` internal, monkeypatch, import hook, or CPython-specific
cache behaviour is part of that route (``KSI-C6``).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource


class SchemaContextError(ValueError):
    """A canonical schema validation context cannot be constructed, or may not be used.

    Fail-closed, like every other refusal in this package: a context that does not
    reproduce the adopted schema digest, count, or ``$id`` set never comes into existence,
    so it cannot validate anything, cannot reach a Store constructor, and cannot precede a
    write.
    """


#: The one filename suffix the canonical schema set is expressed in -- the identical
#: ``*.schema.json`` glob every existing registry in this package already uses, stated once
#: here rather than restated by each capture site.
CANONICAL_SCHEMA_SUFFIX: Final = ".schema.json"

#: ``MANOSUBE-SCHEMA-SET-SHA256-0.1`` -- the same ``sha256`` + domain-separator + named
#: profile convention :data:`~manosube_agent_civilization.state.fingerprint.
#: FINGERPRINT_PROFILE` and ``store.file_store``'s own genesis manifest digest already use,
#: applied here to a captured schema set's own exact bytes. A distinct domain separator keeps
#: this digest space from ever colliding with either of those.
SCHEMA_SET_DIGEST_PROFILE: Final = "MANOSUBE-SCHEMA-SET-SHA256-0.1"
_SCHEMA_SET_DIGEST_DOMAIN: Final = b"MANOSUBE_AGENT_CIVILIZATION_OS\x00SCHEMA_SET\x000.1\x00"


def _reject_unsafe_relative_schema_path(relative_path: str) -> None:
    """Fail closed unless *relative_path* is a plain, relative, traversal-free canonical
    schema path -- the identical path hygiene ``binding.engine._reject_unsafe_relative_path``
    already applies to a declared Boundary root, applied here to a capture key.

    The key never resolves anything (the bytes are already in hand); it is hashed into
    :func:`schema_set_digest`, so it must be a stable, unambiguous name rather than an
    absolute or escaping path that would make two captures of the same tree digest
    differently on two machines.
    """

    if not relative_path:
        raise SchemaContextError("captured schema path is empty")
    if relative_path.startswith(("/", "~")):
        raise SchemaContextError(f"captured schema path must be relative: {relative_path!r}")
    if len(relative_path) >= 2 and relative_path[1] == ":" and relative_path[0].isalpha():
        raise SchemaContextError(f"captured schema path must be relative: {relative_path!r}")
    segments = relative_path.replace("\\", "/").split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise SchemaContextError(
            f"captured schema path carries an empty or traversal segment: {relative_path!r}"
        )
    if not relative_path.endswith(CANONICAL_SCHEMA_SUFFIX):
        raise SchemaContextError(
            f"captured schema path is not a canonical {CANONICAL_SCHEMA_SUFFIX} path: "
            f"{relative_path!r}"
        )


def schema_set_digest(captured: Mapping[str, bytes]) -> str:
    """Return the ``MANOSUBE-SCHEMA-SET-SHA256-0.1`` digest of *captured*'s exact bytes.

    A commitment to the whole closed set at once: every relative path, and the ``sha256`` of
    the bytes captured at it, length-prefixed so no path/content boundary is ambiguous and no
    two different sets can frame to the same preimage. Order-independent (the paths are
    sorted first), so two captures of the identical tree always agree, while a removed,
    added, renamed, or byte-changed schema always disagrees.

    Public so a caller can verify the buffers it holds *before* handing them to
    :class:`CanonicalSchemaContext` -- and then hand in those same buffers, rather than a
    path that would be read again later.
    """

    payload = b"".join(
        len(path.encode("utf-8")).to_bytes(8, "big")
        + path.encode("utf-8")
        + hashlib.sha256(_require_bytes(path, captured[path])).digest()
        for path in sorted(captured)
    )
    return "sha256:" + hashlib.sha256(_SCHEMA_SET_DIGEST_DOMAIN + payload).hexdigest()


def _require_bytes(relative_path: str, content: object) -> bytes:
    """Fail closed unless *content* is real, immutable ``bytes``.

    A ``str`` has no single byte representation until an encoding is chosen, and a
    ``bytearray`` is mutable -- neither is "the captured bytes", and silently coercing either
    would reintroduce exactly the byte-identity ambiguity this module exists to remove.
    """

    if not isinstance(content, bytes):
        raise SchemaContextError(
            f"captured schema content must be bytes, not {type(content).__name__}: "
            f"{relative_path!r}"
        )
    return content


def capture_canonical_schema_bytes(schema_root: Path) -> dict[str, bytes]:
    """Read every canonical ``*.schema.json`` under *schema_root* once, returning the closed
    ``relative posix path -> exact bytes`` mapping :class:`CanonicalSchemaContext` consumes.

    This is the **only** filesystem read the secure route ever performs, and it happens
    strictly before the context exists. Everything after it -- digest verification, validator
    construction, and every validation in a whole Product Binding genesis transaction --
    works from the returned buffers alone.

    A caller that already holds verified buffers (from a Git object, a signed archive, an
    embedded resource) does not need this function at all: it may build the mapping itself
    and hand it straight to the context. The context never requires the schemas to have been
    materialized to a path (``KSI-C4``).
    """

    root = schema_root.resolve()
    if not root.is_dir():
        raise SchemaContextError(f"canonical schema root is unavailable: {schema_root}")
    captured: dict[str, bytes] = {}
    for path in sorted(root.rglob("*" + CANONICAL_SCHEMA_SUFFIX)):
        relative_path = path.relative_to(root).as_posix()
        captured[relative_path] = path.read_bytes()
    if not captured:
        raise SchemaContextError(f"canonical schema root carries no schema: {schema_root}")
    return captured


def _parse_schema_document(relative_path: str, content: bytes) -> tuple[str, dict[str, Any]]:
    """Parse one captured schema's exact bytes into ``($id, document)``, failing closed."""

    try:
        document = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchemaContextError(
            f"captured schema bytes are not valid UTF-8 JSON: {relative_path!r}"
        ) from exc
    if not isinstance(document, dict):
        raise SchemaContextError(f"captured schema is not a JSON object: {relative_path!r}")
    schema_id = document.get("$id")
    if not isinstance(schema_id, str) or not schema_id:
        raise SchemaContextError(f"captured schema has no stable $id: {relative_path!r}")
    return schema_id, document


class CanonicalSchemaContext:
    """One immutable, alias-free, non-reloadable canonical schema validation context.

    Constructed from a closed mapping of relative path to captured bytes. Every schema is
    parsed, and every :class:`jsonschema.Draft202012Validator` constructed, *here*, from
    those exact bytes -- so the documents this context validates against exist only as
    freshly built objects it alone holds, never as the caller's own objects and never as a
    file some later call reads again.

    Immutability is enforced three ways, because each covers a different attack in the
    Issue #75 matrix:

    - the caller's input mapping (and every nested value in it) is consumed once, at
      construction, and never retained: mutating it afterwards changes nothing;
    - no schema document, validator, or internal mapping is ever returned, so there is no
      exposed reference through which a nested schema value could be mutated (only
      validation *operations* are public);
    - :meth:`__setattr__`/:meth:`__delattr__` refuse outright, so a context attribute cannot
      be rebound to a weakened registry after the fact.

    There is deliberately no ``cache_clear``, ``reload``, ``with_schema_root``, or
    filesystem fallback of any kind. Equality is identity: two contexts built from identical
    bytes are still two contexts, which is what lets a caller prove that *one* context was
    used end to end rather than merely that two contexts happened to agree.
    """

    __slots__ = ("_digest", "_relative_paths", "_schema_ids", "_validators")

    _digest: str
    _relative_paths: tuple[str, ...]
    _schema_ids: tuple[str, ...]
    _validators: Mapping[str, Draft202012Validator]

    def __init__(
        self,
        captured: Mapping[str, bytes],
        *,
        expected_digest: str | None = None,
        expected_schema_count: int | None = None,
        expected_schema_ids: Collection[str] | None = None,
    ) -> None:
        """Verify and adopt *captured* as this context's one and only schema set.

        *expected_digest*, *expected_schema_count* and *expected_schema_ids*, when supplied,
        are checked before any validator is built: a set that does not reproduce the adopted
        digest, count, or ``$id`` set is refused here -- before validation, before Store
        construction, before any write (``KSI-C5``).

        Refused unconditionally, whether or not an expectation was supplied: an empty set, a
        non-``bytes`` value, an absolute or traversing path key, a key that is not a
        canonical ``*.schema.json`` path, bytes that are not UTF-8 JSON, a schema that is not
        a JSON object or carries no stable string ``$id``, and a ``$id`` claimed by more than
        one captured path.

        *captured* is read exactly once per key, into this constructor's own private
        ``snapshot``, before anything is checked or parsed. Everything afterwards -- hygiene,
        digest, parse, validator construction -- works from that snapshot, so the bytes this
        context digests are provably the same bytes it validates against even when *captured*
        is an exotic ``Mapping`` whose ``__getitem__`` would answer differently on a second
        read. Digesting one set of bytes and then parsing another is exactly the verify/use
        window this class exists to close; it must not be reintroduced inside the closure
        itself.
        """

        if not captured:
            raise SchemaContextError("captured canonical schema set is empty")

        snapshot: dict[str, bytes] = {}
        for relative_path in sorted(captured):
            _reject_unsafe_relative_schema_path(relative_path)
            snapshot[relative_path] = _require_bytes(relative_path, captured[relative_path])
        relative_paths = tuple(snapshot)

        digest = schema_set_digest(snapshot)
        if expected_digest is not None and digest != expected_digest:
            raise SchemaContextError(
                f"captured canonical schema set does not reproduce the expected "
                f"{SCHEMA_SET_DIGEST_PROFILE} digest: {digest} != {expected_digest}"
            )
        if expected_schema_count is not None and len(relative_paths) != expected_schema_count:
            raise SchemaContextError(
                f"captured canonical schema set carries {len(relative_paths)} schemas, "
                f"not the expected {expected_schema_count}"
            )

        documents: dict[str, dict[str, Any]] = {}
        for relative_path in relative_paths:
            schema_id, document = _parse_schema_document(relative_path, snapshot[relative_path])
            if schema_id in documents:
                raise SchemaContextError(
                    f"captured canonical schema set declares one $id more than once: {schema_id}"
                )
            documents[schema_id] = document

        if expected_schema_ids is not None and set(documents) != set(expected_schema_ids):
            missing = sorted(set(expected_schema_ids) - set(documents))
            unexpected = sorted(set(documents) - set(expected_schema_ids))
            raise SchemaContextError(
                f"captured canonical schema set is not the expected $id set -- "
                f"missing={missing} unexpected={unexpected}"
            )

        registry: Registry[Any] = Registry().with_resources(
            (schema_id, Resource.from_contents(document))
            for schema_id, document in documents.items()
        )
        validators = {
            schema_id: Draft202012Validator(
                document, registry=registry, format_checker=FormatChecker()
            )
            for schema_id, document in documents.items()
        }
        object.__setattr__(self, "_validators", MappingProxyType(validators))
        object.__setattr__(self, "_digest", digest)
        object.__setattr__(self, "_schema_ids", tuple(sorted(documents)))
        object.__setattr__(self, "_relative_paths", relative_paths)

    @classmethod
    def from_schema_root(
        cls,
        schema_root: Path,
        *,
        expected_digest: str | None = None,
        expected_schema_count: int | None = None,
        expected_schema_ids: Collection[str] | None = None,
    ) -> CanonicalSchemaContext:
        """Capture *schema_root* once (:func:`capture_canonical_schema_bytes`) and adopt the
        result -- the convenience form for a caller whose verified bytes happen to still be
        on disk.

        The filesystem is read exactly once, here, before the returned context exists; the
        context itself never reads it again, so a later mutation of *schema_root* changes no
        validation outcome in the returned context.
        """

        return cls(
            capture_canonical_schema_bytes(schema_root),
            expected_digest=expected_digest,
            expected_schema_count=expected_schema_count,
            expected_schema_ids=expected_schema_ids,
        )

    @property
    def digest(self) -> str:
        """The ``MANOSUBE-SCHEMA-SET-SHA256-0.1`` digest of the exact adopted bytes."""

        return self._digest

    @property
    def schema_ids(self) -> tuple[str, ...]:
        """Every canonical schema ``$id`` this context can validate against, sorted."""

        return self._schema_ids

    @property
    def relative_paths(self) -> tuple[str, ...]:
        """Every relative path the adopted bytes were captured at, sorted."""

        return self._relative_paths

    @property
    def schema_count(self) -> int:
        """How many canonical schemas this context adopted."""

        return len(self._schema_ids)

    def knows_schema(self, schema_id: str) -> bool:
        """Whether *schema_id* is part of this context's adopted, closed schema set."""

        return schema_id in self._validators

    def validation_errors(self, instance: Any, schema_id: str) -> list[ValidationError]:
        """Return every validation error *instance* produces against *schema_id*.

        A validation *operation* -- the caller receives errors, never the schema document
        that produced them, and never the validator object holding it. Each call returns a
        freshly built list, so a caller cannot retain or mutate anything this context owns.

        Raises :class:`SchemaContextError` when *schema_id* is outside the adopted set: a
        context fails closed rather than silently validating against nothing.
        """

        validator = self._validators.get(schema_id)
        if validator is None:
            raise SchemaContextError(
                f"canonical schema is unavailable in this validation context: {schema_id}"
            )
        return list(validator.iter_errors(instance))

    def __setattr__(self, name: str, value: object) -> None:
        raise SchemaContextError(
            f"a canonical schema validation context is immutable: cannot rebind {name!r}"
        )

    def __delattr__(self, name: str) -> None:
        raise SchemaContextError(
            f"a canonical schema validation context is immutable: cannot delete {name!r}"
        )

    def __repr__(self) -> str:
        return f"CanonicalSchemaContext(schema_count={self.schema_count}, digest={self._digest})"
