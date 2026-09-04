"""The v0.1 mandatory Invariant union G19 must add, whether or not a Policy declares any.

``CLOSURE_POLICY.md`` section on G19 names one authority source for
``APPLICABLE_V0_1_MANDATORY_INVARIANTS``: the fenced ``ID PASS`` block under
``00_KERNEL/KERNEL_INVARIANTS.md``'s ``# 16. v0.1 Mandatory Gate`` heading, with
``P-003`` excluded because it is a post-Reflow, version-level invariant G19 (a pre-Reflow
Difference Closure gate) does not own. A Closure Policy's own ``required_invariants`` are
additive on top of this union and can never erase it -- an empty Policy set must not make
G19 vacuously pass.

Full Git blob/commit/tree provenance (binding the registry to the exact
``kernel_source_ref_evaluated.commit_sha``/``tree_sha`` a candidate was evaluated against,
and recomputing each individual invariant's own ``invariant_definition_sha256`` from its
own definition block in sections 1-15) is **not implemented here** -- it is the same kind
of large, precisely specified sub-system this module's sibling, ``evidence/levels.py``,
already resolves by pinning rather than by runtime Git resolution: the engine reads no
filesystem, so what is pinned here is the parsed *identity set* (every ``ID`` the section
declares, minus ``P-003``), not a live re-derivation. ``tests/contract/reflow/
test_invariant_registry_source.py`` re-parses the live document with the same grammar this
module exposes and proves the pin has not drifted from it.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

#: The canonical source, and the blob it must be -- the same pin-and-prove pattern
#: ``evidence/levels.py`` uses for ``COMPLETION_SEMANTICS_PATH``/``_BLOB_SHA``.
KERNEL_INVARIANTS_PATH = "00_KERNEL/KERNEL_INVARIANTS.md"
KERNEL_INVARIANTS_BLOB_SHA = "f4fa6336dc3b655297292b707493f3ab92423d53"

#: The exact heading text bounding the section this module's ids are parsed from.
MANDATORY_GATE_HEADING = "# 16. v0.1 Mandatory Gate"
NEXT_HEADING = "# 17. Invariant Evaluation Record"

#: The normalized ``# 16.`` section's own digest, pinned the same way the blob is --
#: NFC-normalized, LF-only, single trailing newline, UTF-8 encoded, SHA-256'd.
MANDATORY_GATE_SOURCE_SECTION_SHA256 = (
    "b54ebb989de78996da9b04af9495e7cec679b0d3b936a5a592bfeacc29e7b5f9"
)

_ENTRY_PATTERN = re.compile(r"^([KASODCERBXP]-[0-9]{3}) PASS$")

#: Every id the live ``# 16.`` fenced block declares, in source order -- computed once by
#: :func:`parse_mandatory_gate_ids` against the real document and pinned here so the engine
#: itself performs no filesystem read. The contract test proves this tuple still equals a
#: fresh parse of the live document.
V0_1_MANDATORY_GATE_IDS: tuple[str, ...] = (
    "K-001", "K-002", "K-003", "K-004",
    "A-001", "A-002", "A-003", "A-004", "A-005",
    "S-001", "S-002", "S-003", "S-004", "S-005",
    "O-001", "O-002", "O-003", "O-004",
    "D-001", "D-002", "D-003", "D-004",
    "C-001", "C-002", "C-003", "C-004", "C-005",
    "E-001", "E-002", "E-003", "E-004", "E-005",
    "R-001", "R-002", "R-003", "R-004", "R-005",
    "B-001", "B-002", "B-003", "B-004",
    "X-001", "X-002", "X-004",
    "P-001", "P-002", "P-003", "P-004",
)

#: G19 is a pre-Reflow Difference Closure gate; ``P-003`` is the post-Reflow, version-level
#: ``VERSION_COMPLETION`` invariant the Policy text names as the one exact exclusion. Fixed
#: by this profile, not by a producer input -- no additional exclusion is admitted.
EXCLUDED_POST_REFLOW_IDS: frozenset[str] = frozenset({"P-003"})


def normalize_section_text(text: str) -> str:
    """Return *text* NFC-normalized, LF-only, with exactly one trailing newline."""

    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n") + "\n"


def section_sha256(text: str) -> str:
    """Return the pinned digest profile's hash of a (not yet normalized) section text."""

    return hashlib.sha256(normalize_section_text(text).encode("utf-8")).hexdigest()


def _fenced_text_blocks(text: str) -> list[str]:
    """Return every ` ```text ` ... ` ``` ` block's inner content, in order."""

    blocks: list[str] = []
    rest = text
    while "```text" in rest:
        start = rest.index("```text") + len("```text")
        remainder = rest[start:]
        try:
            end = remainder.index("```")
        except ValueError as error:
            raise ValueError("a fenced 'text' block is never closed") from error
        blocks.append(remainder[:end])
        rest = remainder[end + len("```") :]
    return blocks


def _is_candidate_block(block: str) -> bool:
    """Return whether *block* contains at least one ``ID PASS``-shaped line.

    The section legitimately carries a *second* fenced ``text`` block after the id
    registry -- the X-003 limited-Claim declaration (``AGENT_REQUIRED_FOR_KERNEL=false`` /
    ``SESSION_INDEPENDENT=true``), which the Policy text names explicitly as *not* part of
    the Invariant registry. That block is not id-shaped at all, so it is not mistaken for a
    second, conflicting candidate block; a genuine second ``ID PASS`` block would be.
    """

    return any(
        _ENTRY_PATTERN.match(line.strip()) for line in block.splitlines() if line.strip()
    )


def parse_mandatory_gate_ids(section_text: str) -> tuple[str, ...]:
    """Return every ``ID`` the section's one ``ID PASS``-shaped fenced block declares, in
    order.

    The grammar is exact: exactly one candidate-shaped ` ```text ` block may exist in
    *section_text*, every non-blank line inside it must match
    ``^[KASODCERBXP]-[0-9]{3} PASS$``, and no id may repeat. A second candidate-shaped
    block, an unrecognized line inside the one real block, or a repeated id is refused
    rather than silently skipped -- this is the parser
    ``tests/contract/reflow/test_invariant_registry_source.py`` runs against the live
    document, and the same parser a totality/injected-violation test runs against a
    corrupted copy of it.
    """

    blocks = _fenced_text_blocks(section_text)
    candidates = [block for block in blocks if _is_candidate_block(block)]
    if not candidates:
        raise ValueError("no id-shaped fenced 'text' candidate block found in the section")
    if len(candidates) > 1:
        raise ValueError("more than one fenced 'text' candidate block found in the section")

    ids: list[str] = []
    seen: set[str] = set()
    for line in candidates[0].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _ENTRY_PATTERN.match(stripped)
        if match is None:
            raise ValueError(f"unrecognized line in the v0.1 Mandatory Gate block: {stripped!r}")
        identity = match.group(1)
        if identity in seen:
            raise ValueError(f"duplicate invariant id in the v0.1 Mandatory Gate block: {identity}")
        seen.add(identity)
        ids.append(identity)
    return tuple(ids)


def expected_g19_invariant_ids() -> frozenset[str]:
    """Return the pinned v0.1 mandatory Invariant id union, minus the one excluded id."""

    return frozenset(V0_1_MANDATORY_GATE_IDS) - EXCLUDED_POST_REFLOW_IDS
