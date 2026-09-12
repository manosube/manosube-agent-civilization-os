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

#: The Kernel's own independently adopted identity for the canonical ``01_SCHEMA`` set
#: (Issue #75, P79-R1-F2 Round 2): a source-committed, human-reviewed constant, not a value
#: any caller supplies or that this module recomputes from whatever bytes it is handed.
#: :attr:`CanonicalSchemaContext.verified` compares a context's own measured
#: :attr:`~CanonicalSchemaContext.digest` against exactly this constant -- never against a
#: caller-declared ``expected_digest`` -- so a context built from weakened bytes cannot
#: become "verified" merely because its own self-computed digest was passed back in as the
#: expectation. Bump this value only in the same commit that changes ``01_SCHEMA`` itself,
#: exactly like ``scripts/validate_schemas.py``'s own asserted schema count.
ADOPTED_SCHEMA_SET_DIGEST: Final = (
    "sha256:31e4d1166cc5856e525243dfdd8aff937fc210c91375c686aa9d4c975d1d5e4e"
)


class _FrozenSchemaMapping(dict):  # type: ignore[type-arg]
    """A real ``dict`` -- ``isinstance(x, dict)`` holds, ``dict(x)``/``**x``/``.copy()`` all
    behave exactly as :mod:`jsonschema` and :mod:`referencing` require internally (Round 2's
    first attempt used :class:`~types.MappingProxyType` here, which is not a ``dict`` at all;
    ``jsonschema``'s own ``unevaluatedProperties`` resolution walks ``$ref``/``allOf`` subschemas
    with ``isinstance(..., dict)`` checks that a proxy fails, silently treating every
    already-evaluated property as unevaluated) -- except that every mutating method raises
    instead of changing this document.
    """

    def __setitem__(self, key: Any, value: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot set an item")

    def __delitem__(self, key: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot delete an item")

    def clear(self) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot clear")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise SchemaContextError("a canonical schema document is immutable: cannot pop")

    def popitem(self) -> Any:
        raise SchemaContextError("a canonical schema document is immutable: cannot pop")

    def setdefault(self, *args: Any, **kwargs: Any) -> Any:
        raise SchemaContextError("a canonical schema document is immutable: cannot setdefault")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot update")

    def __ior__(self, other: Any) -> _FrozenSchemaMapping:  # type: ignore[misc]
        raise SchemaContextError("a canonical schema document is immutable: cannot update")

    def __deepcopy__(self, memo: dict[int, Any]) -> _FrozenSchemaMapping:
        return self

    def __copy__(self) -> _FrozenSchemaMapping:
        return self


class _FrozenSchemaSequence(list):  # type: ignore[type-arg]
    """The ``list`` analog of :class:`_FrozenSchemaMapping`, for the same reason: a real
    ``list`` for every read-only purpose, immutable against every mutating method."""

    def __setitem__(self, index: Any, value: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot set an item")

    def __delitem__(self, index: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot delete an item")

    def append(self, value: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot append")

    def extend(self, values: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot extend")

    def insert(self, index: Any, value: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot insert")

    def remove(self, value: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot remove")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise SchemaContextError("a canonical schema document is immutable: cannot pop")

    def clear(self) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot clear")

    def sort(self, *args: Any, **kwargs: Any) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot sort")

    def reverse(self) -> None:
        raise SchemaContextError("a canonical schema document is immutable: cannot reverse")

    def __iadd__(self, other: Any) -> _FrozenSchemaSequence:  # type: ignore[misc]
        raise SchemaContextError("a canonical schema document is immutable: cannot extend")

    def __imul__(self, other: Any) -> _FrozenSchemaSequence:  # type: ignore[misc]
        raise SchemaContextError("a canonical schema document is immutable: cannot extend")

    def __deepcopy__(self, memo: dict[int, Any]) -> _FrozenSchemaSequence:
        return self

    def __copy__(self) -> _FrozenSchemaSequence:
        return self


def _deep_freeze(value: Any) -> Any:
    """Recursively convert *value* into an immutable analog: ``dict`` to
    :class:`_FrozenSchemaMapping`, ``list`` to :class:`_FrozenSchemaSequence`, everything else
    returned unchanged.

    Applied to every parsed schema document before it is ever handed to a
    :class:`jsonschema.Draft202012Validator` (Issue #75, P79-R1-F1 Round 2): a validator's
    own ``.schema`` attribute is not a copy of what it was constructed with, it *is* that
    same object, so mutating it in place (``context._validators[schema_id].schema[...] =
    ...``) previously changed every future validation this context performs. A frozen
    document raises on that same attempt instead -- while remaining a real ``dict``/``list``
    for every read this module, ``jsonschema``, and ``referencing`` still need to perform.
    """

    if isinstance(value, dict):
        return _FrozenSchemaMapping({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return _FrozenSchemaSequence(_deep_freeze(item) for item in value)
    return value


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

    Immutability is enforced several ways, because each covers a different attack in the
    Issue #75 matrix:

    - the caller's input mapping (and every nested value in it) is consumed once, at
      construction, and never retained: mutating it afterwards changes nothing;
    - no schema document, validator, or internal mapping is ever returned as *itself*
      mutable -- only validation *operations* are public;
    - every parsed schema document is recursively frozen (dicts to
      :class:`_FrozenSchemaMapping`, lists to :class:`_FrozenSchemaSequence` -- real
      ``dict``/``list`` subclasses so ``jsonschema`` and ``referencing`` still treat them as
      such, but every mutating method raises) *before* it is ever handed to a
      :class:`jsonschema.Draft202012Validator`, so even a caller who reaches
      ``context._validators[schema_id].schema`` directly, or a caller mutating a
      ``.schema`` reachable from a returned :class:`~jsonschema.exceptions.ValidationError`,
      gets a structure that raises on assignment rather than one that silently mutates every
      future validation this context performs (Issue #75, P79-R1-F1 Round 2) -- which is
      also why :meth:`validation_errors` no longer needs to deep-copy what it returns: there
      is nothing left reachable from a returned error that mutation could reach;
    - :meth:`__setattr__`/:meth:`__delattr__` refuse outright, so a context attribute cannot
      be rebound to a weakened registry after the fact;
    - :attr:`verified` is a computed property, not a stored flag -- there is no boolean for
      ``object.__setattr__`` (which bypasses ``__setattr__`` by design, the same mechanism
      this class's own constructor uses to set its slots) to promote from ``False`` to
      ``True`` (Issue #75, P79-R1-F2 Round 2).

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

        frozen_documents = {
            schema_id: _deep_freeze(document) for schema_id, document in documents.items()
        }
        registry: Registry[Any] = Registry().with_resources(
            (schema_id, Resource.from_contents(document))
            for schema_id, document in frozen_documents.items()
        )
        validators = {
            schema_id: Draft202012Validator(
                document, registry=registry, format_checker=FormatChecker()
            )
            for schema_id, document in frozen_documents.items()
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

    @property
    def verified(self) -> bool:
        """Whether this context's own measured :attr:`digest` reproduces the Kernel's
        independently adopted :data:`ADOPTED_SCHEMA_SET_DIGEST` (Issue #75, P79-R1-F2
        Round 2).

        Computed fresh on every access from ``self._digest`` -- never stored as a separate
        flag -- so there is no boolean to promote: unlike the Round 1 shape, reaching in
        with ``object.__setattr__(context, "_verified", True)`` has no attribute left to
        set (this class no longer declares one), and cannot make an unverified context's
        ``verified`` read ``True``.

        Deliberately independent of whatever *expected_digest* a caller supplied at
        construction: a caller cannot make an arbitrary (including deliberately weakened)
        capture "verified" merely by recomputing that capture's own digest and passing it
        back in as its own expectation -- that closes the Round 1 counterexample where a
        self-computed digest was accepted as if it were an independently adopted identity.
        The only way ``verified`` is ``True`` is for the captured bytes to actually
        reproduce the exact canonical ``01_SCHEMA`` set this module's own source commits
        to. :class:`~manosube_agent_civilization.store.file_store.FileStateStore` and
        :func:`~manosube_agent_civilization.binding.route.bind_project` both refuse a
        *schema_context* whose ``verified`` is ``False``, so an unverified context can
        never reach validation, Store construction, or a write.
        """

        return self._digest == ADOPTED_SCHEMA_SET_DIGEST

    def validation_errors(self, instance: Any, schema_id: str) -> list[ValidationError]:
        """Return every validation error *instance* produces against *schema_id*.

        A validation *operation* -- the caller receives errors, never a mutable schema
        document, and never the validator object holding one. A raw
        :class:`jsonschema.ValidationError`'s own ``.schema`` attribute is not a copy but a
        direct reference into the schema document node it was raised against (Issue #75,
        P79-R1-F1). Round 1 tried to close that by deep-copying every returned error; Round 2
        found the real reachable state one layer deeper -- ``context._validators[schema_id]
        .schema`` itself, never returned to any caller at all, was still a plain mutable
        ``dict`` that in-place mutation could reach and change, with no return value ever
        needed (an independently reproduced counterexample: ``context._validators[schema_id]
        .schema["properties"][...]`` reached and flipped directly, with no error object
        involved, then made this same context, and a real ``bind_project`` genesis
        transaction carrying the identical invalid body, incorrectly accept it).

        That is closed structurally, not by copying: every parsed schema document is
        recursively frozen (:func:`_deep_freeze` -- nested ``dict`` to
        :class:`_FrozenSchemaMapping`, nested ``list`` to :class:`_FrozenSchemaSequence`, both
        real ``dict``/``list`` subclasses so ``jsonschema``'s and ``referencing``'s own
        internal ``isinstance(..., dict)``/``isinstance(..., list)`` checks -- including the
        ``unevaluatedProperties`` keyword's ``$ref``/``allOf`` subschema walk -- keep working
        exactly as they do over a plain document) before any
        :class:`~jsonschema.Draft202012Validator` is ever constructed from it, so the
        document a validator holds -- and therefore every ``error.schema`` reachable from
        any error it raises, at any nesting depth -- is already immutable. Attempting the
        counterexample above now raises :class:`SchemaContextError` at the mutation itself,
        whether reached through a returned error or through ``context._validators``
        directly; there is no longer a plain mutable dict or list anywhere on the path a
        caller (or an attacker with a bare reference to this context) can reach. Freezing,
        not per-call copying, is what makes returning errors by direct reference safe:
        nothing reachable from a returned error can mutate this context's own validators or
        documents, so no deep-copy is needed -- and none is performed here.

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
