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

from collections.abc import Collection, Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from jsonschema.validators import extend as _extend_validator
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


class _FrozenSchemaMapping(Mapping[str, Any]):
    """Marker base for every frozen schema-document mapping node (Issue #75, P79-R3-F1).

    Round 2 froze schema documents into real ``dict`` *subclasses* whose mutating methods
    raised. That closed ordinary assignment (``node["x"] = y``, ``node.update(...)``), but a
    ``dict`` subclass is still, underneath, a real ``dict``: its mutating slots are
    C-implemented on the base type and operate on the instance's own storage regardless of
    which Python-level methods the subclass defines. Calling the *base type's* method
    directly -- ``dict.__setitem__(node, "unevaluatedProperties", True)`` -- bypasses every
    subclass override entirely and reaches the same live storage every validator built from
    it reads (independently reproduced: this exact call on the top-level Objective Revision
    schema's already-admitted validator flipped an invalid record's error count from 1 to 0,
    and a real ``bind_project`` genesis transaction then committed it).

    There is no way to override that for an actual ``dict``/``list`` instance -- so this
    class is not one. It implements only :class:`collections.abc.Mapping`'s read protocol
    (``__getitem__``/``__iter__``/``__len__``, with ``.get``/``.keys``/``.items``/``.values``/
    ``__contains__`` supplied by the ABC from those three) and declares no ``__setitem__`` or
    any other mutating method at all -- not overridden-to-raise, *absent*. There is no base
    type whose mutating slot a caller could reach through this class, by any name, because no
    such slot exists on any class in its MRO.
    """

    __slots__ = ()


class _FrozenSchemaSequence(Sequence[Any]):
    """The ``list`` analog of :class:`_FrozenSchemaMapping`, for the identical reason: a real
    ``list`` subclass's mutating slots (``list.__setitem__``, ``list.append``, ...) remain
    reachable by calling the base type directly regardless of subclass overrides, so this
    implements only :class:`collections.abc.Sequence`'s read protocol
    (``__getitem__``/``__len__``, with ``__contains__``/``__iter__``/``__reversed__``/
    ``index``/``count`` supplied by the ABC) and defines no mutating method anywhere in its
    MRO.
    """

    __slots__ = ()


def _freeze_mapping(data: Mapping[str, Any]) -> _FrozenSchemaMapping:
    """Recursively freeze *data* into a :class:`_FrozenSchemaMapping`.

    The frozen key/value pairs live only in a closure captured by this one instance's own
    ``__getitem__``/``__iter__``/``__len__`` -- never as a named instance attribute (no
    ``__dict__``, no ``__slots__`` entry) and never as a module-level or otherwise shared
    mutable object. There is therefore no attribute name a caller could reach with
    ``object.__setattr__`` (which bypasses a *subclass's own* ``__setattr__`` override by
    design, but cannot conjure an attribute a class never declares) to replace or reach this
    mapping's backing storage, in addition to there being no mutating method to call in the
    first place.
    """

    frozen = {key: _deep_freeze(value) for key, value in data.items()}

    class _Frozen(_FrozenSchemaMapping):
        __slots__ = ()

        def __getitem__(self, key: str) -> Any:
            return frozen[key]

        def __iter__(self) -> Any:
            return iter(frozen)

        def __len__(self) -> int:
            return len(frozen)

        def __repr__(self) -> str:
            return f"_FrozenSchemaMapping({frozen!r})"

    return _Frozen()


def _freeze_sequence(data: Sequence[Any]) -> _FrozenSchemaSequence:
    """The :func:`_freeze_mapping` analog for a JSON array node -- see there for why the
    frozen items live only in a closure, never as a reachable attribute."""

    frozen = tuple(_deep_freeze(item) for item in data)

    class _Frozen(_FrozenSchemaSequence):
        __slots__ = ()

        def __getitem__(self, index: Any) -> Any:
            return frozen[index]

        def __len__(self) -> int:
            return len(frozen)

        def __repr__(self) -> str:
            return f"_FrozenSchemaSequence({frozen!r})"

    return _Frozen()


def _deep_freeze(value: Any) -> Any:
    """Recursively convert *value* into an immutable analog: ``dict`` to
    :class:`_FrozenSchemaMapping`, ``list`` to :class:`_FrozenSchemaSequence`, everything else
    returned unchanged.

    Applied to every parsed schema document before it is ever handed to a validator (Issue
    #75, P79-R1-F1 Round 2, hardened P79-R3-F1 Round 3): a validator's own ``.schema``
    attribute is not a copy of what it was constructed with, it *is* that same object, so
    mutating it in place -- directly, or by calling the base ``dict``/``list`` type's own
    mutating method on it -- previously changed every future validation this context
    performs. Neither is possible against the frozen structures this function now returns,
    because they are not ``dict``/``list`` instances at all (see
    :class:`_FrozenSchemaMapping`).
    """

    if isinstance(value, dict):
        return _freeze_mapping(value)
    if isinstance(value, list):
        return _freeze_sequence(value)
    return value


def _is_object_type(checker: Any, instance: Any) -> bool:
    """``jsonschema``'s default ``"object"`` type check is ``isinstance(instance, dict)``
    (:mod:`jsonschema._types`) -- true of the real JSON *instance* a caller validates, which
    is never frozen, but false of a frozen schema *document* node such as the value of a
    schema's own ``"properties"`` key. ``unevaluatedProperties``'s own subschema walk
    (:func:`jsonschema._utils.find_evaluated_property_keys_by_schema`) checks exactly that
    (``validator.is_type(properties, "object")``) to decide whether a schema's ``properties``
    keyword counts as declaring evaluated keys; against a real ``dict`` this is ``True``,
    against Round 2's :class:`~types.MappingProxyType` attempt it was silently ``False`` --
    which is why that attempt turned every already-evaluated property into an "unevaluated"
    one and broke validation outright, independent of any freezing/mutation question. This
    predicate, installed on a validator built via :func:`jsonschema.validators.extend`, adds
    exactly that one case back without touching how any real JSON instance is type-checked.
    """

    return isinstance(instance, (dict, _FrozenSchemaMapping))


def _is_array_type(checker: Any, instance: Any) -> bool:
    """The :func:`_is_object_type` analog for ``"array"`` -- no call site in ``jsonschema``
    currently type-checks a schema-level list node this way, but this closes the same class
    of gap defensively, at no cost to real-instance array validation.
    """

    return isinstance(instance, (list, _FrozenSchemaSequence))


_FROZEN_AWARE_TYPE_CHECKER = Draft202012Validator.TYPE_CHECKER.redefine_many(
    {"object": _is_object_type, "array": _is_array_type}
)

#: A ``Draft202012Validator`` that additionally recognizes :class:`_FrozenSchemaMapping` and
#: :class:`_FrozenSchemaSequence` as JSON ``"object"``/``"array"`` instances, via
#: ``jsonschema``'s own documented ``validators.extend`` customization point -- not a private
#: monkeypatch of the shared default validator or its module-level ``TYPE_CHECKER``.
_FrozenAwareValidator = _extend_validator(
    Draft202012Validator, type_checker=_FROZEN_AWARE_TYPE_CHECKER
)


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
    - every parsed schema document is recursively frozen into :class:`_FrozenSchemaMapping`/
      :class:`_FrozenSchemaSequence` nodes -- not ``dict``/``list`` subclasses (Round 3
      found that a ``dict`` subclass's own mutating slots stay reachable by calling the base
      type directly, e.g. ``dict.__setitem__(node, ...)``, bypassing every subclass
      override), but :class:`collections.abc.Mapping`/``Sequence`` implementations with no
      mutating method anywhere in their MRO at all -- *before* any validator is built from
      them, so no reachable node, however it is reached, can be mutated (Issue #75,
      P79-R1-F1 Round 2, hardened P79-R3-F1 Round 3). This is also why
      :meth:`validation_errors` does not need to deep-copy what it returns: there is nothing
      reachable from a returned error that mutation could reach;
    - :meth:`__setattr__`/:meth:`__delattr__` refuse outright, so a context attribute cannot
      be rebound to a weakened registry after the fact;
    - :attr:`verified`, :meth:`knows_schema` and :meth:`validation_errors` are bound once, at
      construction, as closures over this one construction's own adopted-identity comparison
      and validator mapping -- never read back through a named instance attribute at all.
      Round 2 made ``verified`` a property computed from ``self._digest``, which closed the
      Round 1 stored-flag promotion but left two other named, independently replaceable
      targets: ``object.__setattr__(context, "_digest", ADOPTED_SCHEMA_SET_DIGEST)`` promotes
      a weakened context by replacing the comparison's left side to match its right, and
      ``object.__setattr__(context, "_validators", weakened_validators)`` (or rebinding the
      module-level :data:`ADOPTED_SCHEMA_SET_DIGEST` global itself, which ``Final`` does not
      make immutable at runtime) splits what ``verified`` reports from what
      :meth:`validation_errors` actually validates against. None of the three has a named
      attribute left to target after construction (Issue #75, P79-R1-F2 Round 2, hardened
      P79-R3-F2 Round 3).

    There is deliberately no ``cache_clear``, ``reload``, ``with_schema_root``, or
    filesystem fallback of any kind. Equality is identity: two contexts built from identical
    bytes are still two contexts, which is what lets a caller prove that *one* context was
    used end to end rather than merely that two contexts happened to agree.
    """

    __slots__ = ("_digest", "_relative_paths", "_schema_ids")

    _digest: str
    _relative_paths: tuple[str, ...]
    _schema_ids: tuple[str, ...]

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
            schema_id: _FrozenAwareValidator(
                document, registry=registry, format_checker=FormatChecker()
            )
            for schema_id, document in frozen_documents.items()
        }
        object.__setattr__(self, "_digest", digest)
        object.__setattr__(self, "_schema_ids", tuple(sorted(documents)))
        object.__setattr__(self, "_relative_paths", relative_paths)
        object.__setattr__(
            self,
            "__class__",
            _bind_adopted_identity(digest == ADOPTED_SCHEMA_SET_DIGEST, validators),
        )

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
        """Whether *schema_id* is part of this context's adopted, closed schema set.

        This base-class body is a fail-closed default that is never actually reached: every
        instance's own ``__class__`` is retyped, at the end of construction, to a fresh
        per-instance subclass whose :meth:`knows_schema`/:meth:`validation_errors`/
        :attr:`verified` are closures over that one construction's own validator mapping and
        adopted-identity comparison (see :func:`_bind_adopted_identity`, Issue #75,
        P79-R1-F2 Round 2, hardened P79-R3-F2 Round 3) -- there is no ``_validators`` instance
        attribute here to consult, by design.
        """

        return False

    @property
    def verified(self) -> bool:
        """Whether this context's captured bytes reproduce the Kernel's independently
        adopted :data:`ADOPTED_SCHEMA_SET_DIGEST` (Issue #75, P79-R1-F2 Round 2, hardened
        P79-R3-F2 Round 3).

        This base-class body is a fail-closed default (``False``) that is never actually
        reached for a fully constructed context -- see :meth:`knows_schema`. It matters only
        in that it fixes what happens if a caller ever did strip a context's per-instance
        override back off (``object.__setattr__(context, "__class__",
        CanonicalSchemaContext)``): the result is always the conservative ``False``, never a
        promotion, because *this* body never reads any instance attribute at all.

        Round 2 made ``verified`` a property computed fresh from ``self._digest`` on every
        access, comparing it against the module-level :data:`ADOPTED_SCHEMA_SET_DIGEST`.
        That closed the Round 1 stored-``_verified``-flag promotion, but left three other
        independently replaceable targets, each an exact-head reproduced counterexample:
        ``object.__setattr__(context, "_digest", ADOPTED_SCHEMA_SET_DIGEST)`` replaces the
        comparison's left side to match its right and promotes a weakened context;
        ``object.__setattr__(context, "_validators", weakened_validators)`` leaves the
        (correct) comparison alone but splices in validators built from different bytes, so
        ``verified`` stays ``True`` while :meth:`validation_errors` no longer validates
        against what was actually adopted; and rebinding the module global
        ``ADOPTED_SCHEMA_SET_DIGEST`` itself (``Final`` is a static-analysis annotation, not
        a runtime enforcement) changes what *every* context, including ones already
        constructed and already found unverified, reports thereafter, since Round 2's
        property re-read that global on every single access.

        The per-instance closure this property is overridden with (see
        :func:`_bind_adopted_identity`) closes all three at once: ``verified_flag`` is read
        from the module global exactly once, at construction, and from then on lives only in
        a closure cell no instance attribute names -- there is nothing for
        ``object.__setattr__`` to replace, on this object or on the module, that changes an
        already-constructed context's answer. The same closure also supplies the validator
        mapping :meth:`validation_errors` actually uses, so the two can never independently
        drift: what ``verified`` reports and what actually validates come from the exact same
        construction event. :class:`~manosube_agent_civilization.store.file_store.
        FileStateStore` and :func:`~manosube_agent_civilization.binding.route.bind_project`
        both refuse a *schema_context* whose ``verified`` is ``False``, so an unverified
        context can never reach validation, Store construction, or a write.
        """

        return False

    def validation_errors(self, instance: Any, schema_id: str) -> list[ValidationError]:
        """Return every validation error *instance* produces against *schema_id*.

        This base-class body is a fail-closed default that is never actually reached -- see
        :meth:`knows_schema`. A validation *operation* -- the caller receives errors, never a
        mutable schema document, and never the validator object holding one. A raw
        :class:`jsonschema.ValidationError`'s own ``.schema`` attribute is not a copy but a
        direct reference into the schema document node it was raised against (Issue #75,
        P79-R1-F1). Round 1 tried to close that by deep-copying every returned error; Round 2
        froze every parsed schema document into a ``dict``/``list`` subclass whose mutating
        methods raised, closing in-place mutation through ``obj[key] = value`` -- but Round 3
        found that a ``dict``/``list`` subclass's own mutating slots stay reachable by
        calling the *base type* directly (``dict.__setitem__(node, ...)``), bypassing every
        subclass override entirely (an independently reproduced counterexample: exactly that
        call against the already-admitted top-level Objective Revision validator's
        ``.schema["unevaluatedProperties"]`` made the identical invalid record pass, and a
        real ``bind_project`` genesis transaction commit it).

        That is closed by not being a ``dict``/``list`` subclass at all: every parsed schema
        document is recursively frozen (:func:`_deep_freeze`) into
        :class:`_FrozenSchemaMapping`/:class:`_FrozenSchemaSequence` nodes, which implement
        only :class:`collections.abc.Mapping`/``Sequence``'s read protocol and declare no
        mutating method anywhere in their MRO -- there is no base type whose mutating slot a
        caller could reach through them, by any name, because none exists. A validator built
        via :func:`jsonschema.validators.extend` with a type checker that also recognizes
        these frozen nodes as JSON ``"object"``/``"array"`` instances (:data:`
        _FrozenAwareValidator`) validates against them exactly as it would a plain document,
        including the ``unevaluatedProperties`` keyword's ``$ref``/``allOf`` subschema walk.

        Raises :class:`SchemaContextError` when *schema_id* is outside the adopted set: a
        context fails closed rather than silently validating against nothing.
        """

        raise SchemaContextError(
            f"canonical schema is unavailable in this validation context: {schema_id}"
        )

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


def _bind_adopted_identity(
    verified_flag: bool, validators: Mapping[str, Draft202012Validator]
) -> type[CanonicalSchemaContext]:
    """Build the one-off, per-construction subclass a :class:`CanonicalSchemaContext`
    retypes itself to at the end of ``__init__`` (Issue #75, P79-R1-F2 Round 2, hardened
    P79-R3-F2 Round 3).

    *verified_flag* and *validators* are read exactly once, from this one construction's own
    locals, and captured only in the closures of the three methods defined below --
    :attr:`~CanonicalSchemaContext.verified`, :meth:`~CanonicalSchemaContext.knows_schema`,
    :meth:`~CanonicalSchemaContext.validation_errors` -- never assigned to any instance
    attribute. The returned class's ``__slots__`` is empty: it adds no instance storage at
    all over the base class, so there is no attribute name anywhere in the resulting
    instance's layout through which ``object.__setattr__`` could reach or replace either
    value, independently or together. This is what makes the three required guarantees hold
    simultaneously:

    - replacing ``context._digest`` cannot change what ``verified`` reports, because
      ``verified`` no longer reads ``self._digest`` at all;
    - replacing (there is nothing named ``context._validators`` to replace any more) or
      otherwise reaching in to substitute validators cannot change what ``verified`` reports
      while leaving :meth:`validation_errors` pointed at different bytes, because both read
      the same closure-captured ``validators`` established here;
    - rebinding the module-level :data:`ADOPTED_SCHEMA_SET_DIGEST` global after construction
      cannot change what an *already-constructed* context reports, because *verified_flag*
      was computed once, before this function was ever called, and is never re-read from
      that global afterward.

    Building a fresh class per construction (rather than one shared class checking a shared
    private attribute) is what keeps these three guarantees from just becoming the same
    single-named-target problem one level down: a shared attribute, however named, would
    once again be a single ``object.__setattr__`` target reachable given only a context
    reference.
    """

    def verified(self: CanonicalSchemaContext) -> bool:
        return verified_flag

    def knows_schema(self: CanonicalSchemaContext, schema_id: str) -> bool:
        return schema_id in validators

    def validation_errors(
        self: CanonicalSchemaContext, instance: Any, schema_id: str
    ) -> list[ValidationError]:
        validator = validators.get(schema_id)
        if validator is None:
            raise SchemaContextError(
                f"canonical schema is unavailable in this validation context: {schema_id}"
            )
        return list(validator.iter_errors(instance))

    return type(
        "_VerifiedCanonicalSchemaContext",
        (CanonicalSchemaContext,),
        {
            "__slots__": (),
            "verified": property(verified),
            "knows_schema": knows_schema,
            "validation_errors": validation_errors,
        },
    )
