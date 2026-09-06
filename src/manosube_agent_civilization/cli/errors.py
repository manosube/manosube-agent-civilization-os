"""Fail-closed CLI Boot adapter errors (Phase 11, Issue #47).

These exist only for the checks this adapter itself owns -- argument parsing and the
existence of the two explicit filesystem roots the caller supplies. Every other failure mode
(Binding identity/shape, Store corruption/uninitialized-project/boundary, Boot's own
cross-record consistency, canonical-JSON/schema/fingerprint failures) propagates the existing
owning domain's own typed error unchanged; this adapter never catches and rewraps those, it
only classifies them for its own deterministic stderr projection (:mod:`.main`).
"""

from __future__ import annotations


class CLIError(RuntimeError):
    """Base error: the CLI Boot adapter itself could not proceed, before Boot was ever
    invoked."""


class CLIArgumentError(CLIError):
    """The command line is missing a required argument, supplies an unknown argument, names
    an unknown subcommand, or otherwise fails argument parsing."""


class CLIInvalidRootError(CLIError):
    """``--store-root`` or ``--schema-root`` does not name an existing directory."""
