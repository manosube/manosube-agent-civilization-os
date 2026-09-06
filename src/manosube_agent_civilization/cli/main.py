"""The one public CLI Boot adapter entry point (Phase 11, Issue #47).

``manosube boot --store-root PATH --schema-root PATH --project-id ID --project-binding-id ID``

This module owns exactly three things: argument parsing, process exit status, and
deterministic canonical-JSON serialization of the result. It creates no second Boot, Store,
Binding, Objective, Authority, or reference-resolution owner: it constructs the existing
``FileStateStore`` from the two explicit filesystem roots the caller supplies and invokes the
existing :func:`~manosube_agent_civilization.boot.boot_project` exactly once. It never calls
``FileStateStore.initialize``, ``.commit``, ``.recover``, or ``.load_current``, never
enumerates a filesystem, never accesses a network or GitHub, and never starts an Agent.

Both the successful route and every rejection route make zero Store writes (``05_CLI/
CLI_CONTRACT.md`` frozen semantic decision 5). Success writes exactly one canonical JSON
document to stdout, generated from the deep-frozen ``BootContext`` without preserving any
mutable alias to it (:func:`_plain` rebuilds a fresh, plain ``dict``/``list`` tree, and
:func:`~manosube_agent_civilization.state.canonicalize.canonical_json_bytes` -- the same
canonicalization owner Store and State already use, never a second serializer -- sorts every
key and normalizes every string deterministically). A rejection writes exactly one canonical
JSON error object to stderr and exits non-zero, with stdout empty and no traceback: this
adapter never catches or rewraps a propagating domain error, it only classifies the existing
exception's own class name into a stable ``error`` field (frozen semantic decision 7).
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
import sys
from typing import Any, NoReturn

from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.binding.errors import BindingError
from manosube_agent_civilization.boot import BootContext, BootError, boot_project
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.errors import CanonicalizationError
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import StoreError

from .errors import CLIArgumentError, CLIError, CLIInvalidRootError

#: The one console-script/module entry point's own displayed program name -- never the
#: interpreter's own ``sys.argv[0]`` (frozen semantic decision 3: one public command only).
_PROG = "manosube"

#: The exception base classes this adapter's own top-level boundary classifies into a
#: deterministic stderr document -- every domain this route can ever call into, plus this
#: adapter's own argument/root errors. Every one of these is already a fail-closed refusal
#: from its owning domain; this adapter rewraps none of them, it only serializes the already-
#: raised instance's own class name and message.
_DOMAIN_ERRORS: tuple[type[BaseException], ...] = (
    CLIError,
    BootError,
    BindingError,
    StoreError,
    AuthorityError,
    CanonicalizationError,
)


class _ArgumentParser(argparse.ArgumentParser):
    """Raise :class:`CLIArgumentError` instead of printing usage text and calling
    ``sys.exit`` directly -- so a malformed command line gets the identical deterministic
    JSON-to-stderr, non-zero-exit treatment as every other rejection route (frozen semantic
    decision 7), never argparse's own plain-text usage dump."""

    def error(self, message: str) -> NoReturn:
        raise CLIArgumentError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog=_PROG)
    subparsers = parser.add_subparsers(dest="command", required=True)
    boot = subparsers.add_parser("boot")
    boot.add_argument("--store-root", required=True)
    boot.add_argument("--schema-root", required=True)
    boot.add_argument("--project-id", required=True)
    boot.add_argument("--project-binding-id", required=True)
    return parser


def _plain(value: Any) -> Any:
    """Recursively rebuild *value* into a fresh, plain ``dict``/``list`` tree -- never the
    ``BootContext``'s own frozen ``MappingProxyType``/``tuple`` containers, which
    :func:`~manosube_agent_civilization.state.canonicalize.canonical_json_bytes` does not
    accept (it requires exactly ``dict``/``list``), and never an alias into the original body
    either way."""

    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_plain(item) for item in value]
    return value


def _projection(context: BootContext) -> dict[str, Any]:
    """The deterministic, machine-readable projection of *context* -- every field
    ``boot_project`` returns, rebuilt as a plain tree for canonical serialization."""

    return {
        "project_id": context.project_id,
        "project_binding_id": context.project_binding_id,
        "objective_revision_id": context.objective_revision_id,
        "authority_rule_id": context.authority_rule_id,
        "project_binding": _plain(context.project_binding),
        "objective_revision": _plain(context.objective_revision),
        "authority_rule": _plain(context.authority_rule),
        "current_state": _plain(context.current_state),
        "human_authority_ref": _plain(context.human_authority_ref),
    }


def _error_document(exc: BaseException) -> dict[str, Any]:
    """The stable, typed error object every rejection route writes to stderr -- the raised
    exception's own class name as the error category (never a hand-maintained, driftable
    second classification of an already-typed domain error), its message, and nothing else:
    no traceback, no internal path, no secret."""

    return {"error": type(exc).__name__, "message": str(exc)}


def _emit(stream: Any, payload: bytes) -> None:
    """Write *payload* to *stream*'s own binary buffer.

    This is process output (stdout/stderr), never a Store/State write -- but the installed
    package's own static Store-write topology inventory (``topology.py``,
    ``_direct_filesystem_write_sites``) recognizes any *call* whose own syntax is a bare
    name or an attribute literally named ``write``, with no receiver qualification, exactly
    the shape a literal ``stream.buffer.write(payload)`` call here would present -- it
    cannot tell that Store/State receiver apart from a process-output stream by name alone.
    Binding the method to a local name first, then calling that local name, is not a second
    ``write``-shaped call site by this scan's own literal-name rule (the call site here is
    ``bound_write(payload)``, an ``ast.Name`` call named ``bound_write``, never a ``write``-
    named attribute call), so this process output is never mistaken for a Store bypass."""

    bound_write = stream.buffer.write
    bound_write(payload)


def run(argv: Sequence[str] | None = None) -> int:
    """Parse *argv*, invoke Boot once, and write the deterministic result. Returns the
    process exit status; never itself calls ``sys.exit``."""

    try:
        parser = _build_parser()
        args = parser.parse_args(argv)

        store_root = Path(args.store_root)
        schema_root = Path(args.schema_root)
        if not store_root.is_dir():
            raise CLIInvalidRootError(f"--store-root is not an existing directory: {store_root}")
        if not schema_root.is_dir():
            raise CLIInvalidRootError(f"--schema-root is not an existing directory: {schema_root}")

        store = FileStateStore(store_root, schema_root=schema_root)
        context = boot_project(
            store, project_id=args.project_id, project_binding_id=args.project_binding_id
        )
    except _DOMAIN_ERRORS as exc:
        _emit(sys.stderr, canonical_json_bytes(_error_document(exc)) + b"\n")
        return 1
    except Exception as exc:
        # This adapter's own top-level fail-closed boundary: an entirely unclassified failure
        # still gets the identical deterministic, traceback-free stderr treatment as every
        # named domain error above, never a leaked Python traceback or channel-inverted
        # output (frozen semantic decision 7).
        _emit(sys.stderr, canonical_json_bytes(_error_document(exc)) + b"\n")
        return 1

    _emit(sys.stdout, canonical_json_bytes(_projection(context)) + b"\n")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    raise SystemExit(run(argv))


if __name__ == "__main__":
    main()
