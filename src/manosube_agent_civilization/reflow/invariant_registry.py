"""The v0.1 mandatory Invariant registry G19 must add, whether or not a Policy declares any.

``CLOSURE_POLICY.md`` section on G19 names one authority source for
``APPLICABLE_V0_1_MANDATORY_INVARIANTS``: the fenced ``ID PASS`` block under
``00_KERNEL/KERNEL_INVARIANTS.md``'s ``# 16. v0.1 Mandatory Gate`` heading, with
``P-003`` excluded because it is a post-Reflow, version-level invariant G19 (a pre-Reflow
Difference Closure gate) does not own. A Closure Policy's own ``required_invariants`` are
additive on top of this union and can never erase it -- an empty Policy set must not make
G19 vacuously pass.

R2-G19 (Phase 7 structural-review round 2) escalated G19 from an id-only union to the
Policy's full registry contract: each mandatory id's own ``invariant_definition_sha256`` is
now derived too, from its ``## <ID> — <NAME>`` definition block under
``00_KERNEL/KERNEL_INVARIANTS.md`` sections 4-15 (the same heading-to-next-heading,
NFC/LF/trailing-newline normalize-then-SHA-256 profile section 16's own digest already
uses -- CLOSURE_POLICY.md names this "第1章のInvariant block抽出規則" without spelling
out a second grammar because section 1 only fixes the canonical *field* list every block
already follows; the block boundary itself is the next ``#``/``##`` heading, which is what
:func:`parse_invariant_definition_digests` and this module's own pinned
:data:`V0_1_INVARIANT_DEFINITION_DIGESTS` both use). The registry's own
``registry_semantic_fingerprint``/``registry_id`` are derived exactly as
``CLOSURE_POLICY.md`` specifies (:func:`registry_digest`). A binding's own ``binding_id`` is
also derived and checked (:func:`candidate_invariant_evaluation_binding_id`), and a same-ID
definition conflict between a Policy's own ``required_invariants`` and the mandatory
registry now fails G19 closed rather than silently unifying by first-wins/last-wins/ID-only
dedup (``reflow/closure.py``'s ``_evaluate_g19``). The Atomic-Reflow pre-commit
re-resolution CLOSURE_POLICY.md requires is real too, wired into
:func:`~manosube_agent_civilization.reflow.commit.commit_reflow` via
:func:`mandatory_bindings_still_match`.

Two things this module still does **not** claim, named rather than silently narrowed:

* Live Git commit/tree resolution -- binding the registry to the exact
  ``kernel_source_ref_evaluated.commit_sha``/``tree_sha`` a *candidate* was evaluated
  against, by resolving an arbitrary commit's tree at runtime. Doing that would mean this
  engine reading either the filesystem or a live Git object database at evaluation time,
  which is the same "the engine reads no filesystem" line ``evidence/levels.py`` already
  draws for the Evidence Level scale, and which this whole vertical draws everywhere else
  (pin, and prove the pin against the live document in a contract test, never resolve a
  caller-supplied source live). What is real here instead: the pinned blob/digests are
  drift-tested against the live document (``tests/contract/reflow/
  test_invariant_registry_source.py``), and G19 additionally requires a same-ID
  definition-conflict check (below) that a live Git resolution would not add anything to
  that a caller-controlled ``kernel_source_ref_evaluated`` could not equally forge.
* Any producer for ``invariant_evaluation`` records (``01_SCHEMA/difference/
  invariant_evaluation.schema.json`` has none anywhere in this tree, confirmed by grep --
  the same gap ``reflow/route.py`` names for ``candidate_completion_record``). G19 verifies
  every *binding*'s own closed fields exactly; it cannot resolve the ``invariant_evaluation``
  record a binding's ``invariant_evaluation_ref`` names, because nothing in v0.1 produces
  one to resolve.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
import unicodedata

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

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


#: Every mandatory id's own definition-block digest -- ``## <ID> — <NAME>`` heading through
#: the next ``#``/``##`` heading, NFC/LF/trailing-newline normalized, SHA-256'd. Computed
#: once by :func:`parse_invariant_definition_digests` against the live document and pinned
#: here for the same "engine reads no filesystem" reason :data:`V0_1_MANDATORY_GATE_IDS`
#: is. ``X-003`` is deliberately absent: its own ``##`` block exists (section 12), but
#: ``CLOSURE_POLICY.md`` names it explicitly as *not* part of this registry -- it has no
#: ``ID PASS`` line in section 16, and is evaluated as G21's mandatory Claim instead.
V0_1_INVARIANT_DEFINITION_DIGESTS: dict[str, str] = {
    "K-001": "0e8747f833b56ac5f1b756f280ad7d6f276597249831648a2418043022818c59"[:64],
    "K-002": "6aa9a3e018dbafd62d1e30cd02d62b01d7b9eac4e7c02503704f156cfc253067"[:64],
    "K-003": "46e88f95aa0bee9d336b5fb72cf09b38e5eebcfeca27a203d9660562835353c9"[:64],
    "K-004": "7b2aea6e574cae56c266a6b4616b6fe6a2be3f19d227cc660abdd599e0b4f8e3"[:64],
    "A-001": "43926a695901431f5c287c2056a863cf280819c784c425ce727d0f5d232061e6"[:64],
    "A-002": "a51fd412dce483ff8b7f9a82a31a4c3a407d8822c609bea419f7a9b90c52c754"[:64],
    "A-003": "e635955491006bb0cb5e572598d54da7e4ba2dff46110e796f4a99c4b837ae08"[:64],
    "A-004": "9a991489f2aaad79165dbc9764a1006686a465ce1191fa62e76a0a7d75b30cb0"[:64],
    "A-005": "e72cc3776d2f9cad64ebb7af8cdb7ab8de0604328d4a337c98f36117739833ba"[:64],
    "S-001": "6931833977612105db24dc7f599121488b46637b555a3eb4fd83899263bb0402"[:64],
    "S-002": "238a2691b4afd1409c5adeb1bd0f0a8810adb17b622bcc04f31a34e9f9da0a56"[:64],
    "S-003": "77cdd71e73bfdfb716143551961674a34bdb0f53196a3f66e7a1b0d7418f0794"[:64],
    "S-004": "13c64bfd41644d2e66161721e3fd2465953c1deeb4d6bf3797f59fd0a425e727"[:64],
    "S-005": "9d41ea33357d1b90398fc6a99cee00376744e82b902a61cafd82cb5f5ac9bbc6"[:64],
    "O-001": "096611804717312280729c0228fb9d57d3a92e6e56b89c2b6b32b7b50962aca4"[:64],
    "O-002": "107a9ecf660648f71c4ca644eb7ccba4d965681be67b51257cc80066a524833b"[:64],
    "O-003": "7ea52536d4bbfa9ec3301144c4f959d8dc732a222bc6eebece598cff5e87e422"[:64],
    "O-004": "ab4471cd74cc2fed4c510f60c081674e45829b4d8353720fbaeabf05239f5b03"[:64],
    "D-001": "a06680f3239ce663e2e38ee44869dbd1cd6b0c9559d385acfb6d15b6c38520cd"[:64],
    "D-002": "282d39925938423be8a54b8405dfd79770da3f08ef00bba38b1fce80e91405c4"[:64],
    "D-003": "542d162b527417b78703dc3f9d5e61612be910410f1540a4de76d23795f42d4b"[:64],
    "D-004": "288856b31f51be18baa1dd956799f8daf1db6d640556c24c35cbe33ad8028f2c"[:64],
    "C-001": "ecc2f51d9997d2d70b142f6f0d9025f02fa952d3aef21492a73fa18fdffa11fe"[:64],
    "C-002": "871dc489bb81e0481778fb825c9d6e464c58b5009dda254d07d0bbe80a06564a"[:64],
    "C-003": "80825e80c5fd5a704d7d1aa804e8f255749bbeabdb10358b38a6b9ffae5cc156"[:64],
    "C-004": "72d5fca9ef5106bdd3b92ecee60442e42a955c1a9a1f078c5b4d65d1fe18f1dd"[:64],
    "C-005": "2bd29749069f97468282295959ffad1b18df7256cf148de561e39949dea040e4"[:64],
    "E-001": "e8e89561604902c6b470d85fd8b9624fb36404041a38abb2bd07dba1acf5acdb"[:64],
    "E-002": "c8c3232b895729d9dddc2a23ff29cfe54c85551e5aabf4d874fdb08264fc2a40"[:64],
    "E-003": "d12105d9ee60d5a168d88ac47d426315f5d74aad1cb5f8afb8fdc6a9f1370998"[:64],
    "E-004": "3e9f77b43efdf0fbbd3b1dc06dcf472595df5951ee12f9721773b367ed489d58"[:64],
    "E-005": "adfe9f4d38fa3c95707668c57fa0fd8182193027e32dc6d3d5f144b6ee67df5f"[:64],
    "R-001": "b8b34a0a81c3b38a033753498713de323d187512265e3474baad7f2f1dfdd4df"[:64],
    "R-002": "a12a5bb1b7fd98ed1e81b52cd9eac6ad9569b61d1a4885aa91c4a4dc2d45784b"[:64],
    "R-003": "fce31a6e7662601d27b2f8f3c18419fa3a49c1ccfc2641a78b83867f8a902b80"[:64],
    "R-004": "4be547ac580171def53836caa57d2da2e3d372c0c4916b1410d5128c2fb016cf"[:64],
    "R-005": "3c425b749db6c4afbcefdffad7793586a29bc37cd3a73cd67da1095cdf78b559"[:64],
    "B-001": "787318873c5e3753f7ea32ddaec847023f19bd72342c515c9b3b4f95bceb8966"[:64],
    "B-002": "4b02d7f908c9ae41b67af9be29943af4da0f800f111313094d31076202a7e1cf"[:64],
    "B-003": "9cfc888711261d0321abc7f281fae5b1c0ec987d96cdaf33101986e493946f4d"[:64],
    "B-004": "e5316e0d2518921db178887f031129e83ba892bd2162c20e54922a5821d95e18"[:64],
    "X-001": "6eb2f4cdf243518382b2dbbdfd7de47bff2314c9f87a3cef7e57c40894d57369"[:64],
    "X-002": "0eef84a3bd3060158e7ea8fc46924dcc4b3a5ba5f6ce1470dbe15307de10cfd8"[:64],
    "X-004": "17a0139dff4194c5cc3772dd5e6c9352e1ee75cd8e9deceb76d8e3d54b2c0026"[:64],
    "P-001": "428a3572e180b9b1eb97368f00301d2b56fa64362518b87f8e194da2b140309b"[:64],
    "P-002": "a194b2ebac692ad3ee03b19f213294e9a756c125e25e2fd814e18ccf1af21fc8"[:64],
    "P-003": "f507084d44f680da2609c1ca86726430210e5ef1f948c59ddd116b0687e613bf"[:64],
    "P-004": "921164b064496590afb09adde9b21916a0420e027aaaeb5abdd58b615f2f1781"[:64],
}

_INVARIANT_HEADING = re.compile(r"^## ([KASODCERBXP]-[0-9]{3}) — .*$", re.MULTILINE)
_ANY_HEADING = re.compile(r"^#{1,2} .*$", re.MULTILINE)


def parse_invariant_definition_digests(document_text: str) -> dict[str, str]:
    """Return every mandatory id's own ``## <ID> — <NAME>`` block digest, from the whole
    live ``KERNEL_INVARIANTS.md`` text -- the parser
    ``tests/contract/reflow/test_invariant_registry_source.py`` runs to prove
    :data:`V0_1_INVARIANT_DEFINITION_DIGESTS` has not drifted from the document.
    """

    heading_starts = [(match.group(1), match.start()) for match in _INVARIANT_HEADING.finditer(document_text)]
    any_heading_starts = sorted(match.start() for match in _ANY_HEADING.finditer(document_text))
    mandatory = set(V0_1_MANDATORY_GATE_IDS)
    digests: dict[str, str] = {}
    for invariant_id, start in heading_starts:
        if invariant_id not in mandatory:
            continue
        if invariant_id in digests:
            raise ValueError(f"duplicate '## {invariant_id} —' heading in the document")
        end = next((pos for pos in any_heading_starts if pos > start), len(document_text))
        digests[invariant_id] = section_sha256(document_text[start:end])
    missing = mandatory - set(digests)
    if missing:
        raise ValueError(f"no '## <ID> —' heading found for: {sorted(missing)}")
    return digests


#: The registry's own fixed identity fields, per ``CLOSURE_POLICY.md``'s
#: ``MANOSUBE-V0_1-MANDATORY-INVARIANT-REGISTRY-0.1`` profile.
REGISTRY_PROFILE = "MANOSUBE-V0_1-MANDATORY-INVARIANT-REGISTRY-0.1"
REGISTRY_SCHEMA_VERSION = "0.1"
REGISTRY_REPOSITORY = "manosube/manosube-agent-civilization-os"
_REGISTRY_DOMAIN_SEPARATOR = b"MANOSUBE:V0_1_MANDATORY_INVARIANT_REGISTRY:0.1:"


def registry_entries() -> tuple[dict[str, str], ...]:
    """Return the registry's ordered entry list -- every id in :data:`V0_1_MANDATORY_GATE_IDS`
    (the full source set, ``P-003`` included: "Registryはsource set全体を保持する"), each
    qualified by its own pinned definition digest.
    """

    return tuple(
        {
            "invariant_id": invariant_id,
            "invariant_definition_sha256": "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS[invariant_id],
        }
        for invariant_id in V0_1_MANDATORY_GATE_IDS
    )


def registry_digest() -> str:
    """Return the raw hex digest ``CLOSURE_POLICY.md`` defines: domain-separated SHA-256 of
    the closed ``profile + schema_version + repository + path + source_section_sha256 +
    entries`` projection -- ``registry_id``/commit SHA/whole-file blob SHA excluded.
    """

    payload: dict[str, Any] = {
        "profile": REGISTRY_PROFILE,
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "repository": REGISTRY_REPOSITORY,
        "path": KERNEL_INVARIANTS_PATH,
        "source_section_sha256": "sha256:" + MANDATORY_GATE_SOURCE_SECTION_SHA256,
        "entries": [dict(entry) for entry in registry_entries()],
    }
    return hashlib.sha256(_REGISTRY_DOMAIN_SEPARATOR + canonical_json_bytes(payload)).hexdigest()


def registry_semantic_fingerprint() -> str:
    """Return ``"sha256:" + lowercase_hex(registry_digest())``."""

    return "sha256:" + registry_digest()


def registry_id() -> str:
    """Return ``"V01-MANDATORY-INV-REG-" + uppercase_hex(registry_digest())``."""

    return "V01-MANDATORY-INV-REG-" + registry_digest().upper()


#: ``CLOSURE_POLICY.md``'s ``candidate_invariant_evaluation_binding`` identity profile.
#: Unlike ``candidate_claim_evaluation_event_id``/``_series_id`` (which explicitly state a
#: "domain X を前置して" prefix) or ``registry_digest`` (which shows the same literal
#: ``SHA-256(UTF8(domain) || CANONICAL_JSON_UTF8(...))`` form), the binding_id sentence uses
#: this document's *other* formula style -- the same bare ``PROFILE=...`` style
#: ``policy_semantic_fingerprint`` and the Target Predicate fingerprint already use, with no
#: domain-separator field in their own ``PROFILE=`` blocks either. Read literally and
#: consistently with both of this document's own formula styles, ``binding_id`` is
#: unseparated: ``"CAND-INV-EVAL-" + uppercase_hex(SHA-256(canonical_json(closed_fields)))``
#: over every field except ``binding_id`` itself -- no domain-separator prefix.
BINDING_PROFILE = "MANOSUBE-CANDIDATE-EVALUATION-BINDING-SHA256-0.1"


def candidate_invariant_evaluation_binding_id(binding: dict[str, Any]) -> str:
    """Return the content-addressed ``binding_id`` CLOSURE_POLICY.md's G19 section derives
    for a ``candidate_invariant_evaluation_binding`` -- every field except ``binding_id``
    itself, canonical JSON UTF-8, SHA-256, uppercase hex, prefixed ``"CAND-INV-EVAL-"``.
    """

    closed = {key: value for key, value in binding.items() if key != "binding_id"}
    digest = hashlib.sha256(canonical_json_bytes(closed)).hexdigest()
    return "CAND-INV-EVAL-" + digest.upper()


def expected_g19_invariant_entries() -> frozenset[tuple[str, str, str]]:
    """Return G19's mandatory expected set as ``(kind, id, invariant_definition_sha256)``
    triples -- the exact shape a ``candidate_invariant_evaluation_binding``'s own
    ``invariant_ref``/``invariant_definition_ref`` must match.
    """

    return frozenset(
        ("kernel_invariant", invariant_id, "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS[invariant_id])
        for invariant_id in expected_g19_invariant_ids()
    )


def mandatory_bindings_still_match(bindings: list[dict[str, Any]]) -> bool:
    """R2-G19's Atomic-Reflow pre-commit re-resolution: re-derive the mandatory (non-Policy)
    portion of G19's expected set from the *currently* pinned registry and confirm every
    mandatory-id binding in *bindings* still carries the matching digest.

    Named honestly: within one running process the pinned registry cannot itself drift
    between an Evaluation's own computation and its commit, so this mirrors
    ``evaluation_expires_at``'s G18 recheck in form -- a real, unconditional re-derivation
    and re-comparison immediately before commit -- without being able to observe registry
    drift except across a code deployment that lands mid-transaction. What it protects
    against is exactly that: a binding computed against one deployed registry being
    silently promoted after a newer one has since been deployed.
    """

    expected_ids = expected_g19_invariant_ids()
    for binding in bindings:
        ref = binding.get("invariant_ref") or {}
        if ref.get("kind") != "kernel_invariant" or ref.get("id") not in expected_ids:
            continue
        expected_digest = "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS[ref["id"]]
        actual_digest = (binding.get("invariant_definition_ref") or {}).get(
            "invariant_definition_sha256"
        )
        if actual_digest != expected_digest:
            return False
    return True
