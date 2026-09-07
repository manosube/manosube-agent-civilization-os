# MANOSUBE Agent Civilization OS

## Governance Adoption Record Enforcement (Issue #53)

```text
DOC_TYPE=GOVERNANCE_OPERATING_GUIDE
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=GOVERNANCE-ADOPTION-RECORD-ENFORCEMENT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=none
DECISION_AUTHORITY=SHUKOU
ADOPTION_ID=ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT
GOVERNING_ISSUE=#53
RUNTIME_ENFORCEMENT_IMPLEMENTED=false
```

---

## 0. What this document is

`CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` §3 and §3.1 already state the rule: an external
finding -- and, by the identical reasoning, an implementation instruction -- becomes
authority only through an explicit SHUKOU adoption, bound to its own exact observation. What
that document did not yet have was a mechanically checkable *shape* for such an adoption, or
a module that answers, for one exact record, whether it has that shape.

This document is that shape's operating guide. `src/manosube_agent_civilization/
development_binding/adoption_record.py` is its enforcement (`evaluate_adoption_record`);
`tests/contract/binding/test_adoption_record_enforcement.py` is its proof.

```text
GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT_IS_A_NEW_KERNEL_ELEMENT=false
GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT_IS_A_NEW_AUTHORITY_OWNER=false
GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT_IS_A_GITHUB_ADAPTER=false
```

This is not a ninth Kernel element (`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight),
and it is not a second Authority owner (`00_KERNEL/05_AUTHORITY/AUTHORITY_CONTRACT.md`
remains the one Change-permission evaluator). It is an extension of the existing
`development_binding` owner -- the same package that already evaluates this repository's
own handoff-state policy -- answering one further, narrowly-scoped question about the
*instruction* that starts a work unit, rather than about the states that work unit moves
through once started.

## 1. The canonical sequence

```text
SHUKOU decision
  ↓
ChatGPT Structural Advisor records the complete adoption on GitHub
  (an Issue or Pull Request comment, in the repository's own adoption format)
  ↓
ChatGPT Structural Advisor reads the comment back through the GitHub API
  and cites its immutable comment URL
  ↓
Claude Code independently re-reads that exact URL through the GitHub API,
  confirms the body, decision authority, and reviewed HEAD/base SHA match
  what was cited, and only then begins implementation
  ↓
Claude Code implementation, ending at READY_FOR_STRUCTURAL_REVIEW
  ↓
ChatGPT Structural Advisor's structural review
  ↓
SHUKOU final acceptance and manual merge
```

No step in this sequence may be skipped, reordered, or inferred from a step's own
plausibility. In particular:

```text
A_CHAT_DRAFT_IS_NOT_A_DECISION_RECORD=true
UNPOSTED_TEXT_IS_NOT_A_DECISION_RECORD=true
A_URL_NOT_YET_READ_BACK_IS_NOT_VERIFIED=true
TECHNICAL_CORRECTNESS_IS_NOT_ADOPTION=true
SILENCE_IS_NOT_ADOPTION=true
HISTORICAL_COMMENT_DOES_NOT_RETROACTIVELY_AUTHORIZE_NEW_WORK=true
```

The last four restate `CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` §3/§3.1/§3.2 verbatim in
meaning; this document adds nothing new to *what* counts as adoption, only a way to *check*
that a specific record actually carries one.

## 2. What a verified Governance Adoption Record contains

`evaluate_adoption_record` reads exactly nine keys and no others:

```text
schema_version              "0.1"
adoption_id                 the adoption's own stable identifier, e.g.
                             ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT
governing_issue             the Issue or Pull Request this adoption semantically governs,
                             e.g. "#53" -- distinct from wherever it happens to be recorded
comment_url                 an immutable GitHub comment URL, scoped to this repository --
                             https://github.com/manosube/manosube-agent-civilization-os
                             /(issues|pull)/<n>#issuecomment-<id>
decision_authority           must be "SHUKOU"
decision_status               must be "RATIFIED"
api_read_back_receipt       a structured receipt: the caller's own claim of what the
                             independent API read-back actually showed for adoption_id,
                             governing_issue, reviewed_sha, comment_url, decision_authority,
                             and decision_status
reviewed_sha                 the exact commit SHA the adoption reviewed
authorized_target_sha        the exact commit SHA the work this record authorizes
                             is based on or targets
```

`api_read_back_receipt` is itself a closed object with exactly six keys -- `adoption_id`,
`governing_issue`, `reviewed_sha`, `comment_url`, `decision_authority`, `decision_status` --
the same six names as the record's own top-level declarations, checked field-by-field for
exact agreement.

The record admits (`ADOPTION_RECORD_ADMITTED`) only when every one of the following holds:

```text
comment_url matches the immutable-comment URL pattern, scoped to this repository
adoption_id is non-empty and ADOPT_-shaped
governing_issue is a well-formed #<number> reference
api_read_back_receipt agrees, field by field, with adoption_id / governing_issue /
    reviewed_sha / comment_url / decision_authority / decision_status as the record
    itself declares them
decision_authority == "SHUKOU"
decision_status == "RATIFIED"
reviewed_sha and authorized_target_sha are both real-shaped commit SHAs
reviewed_sha == authorized_target_sha
```

Any other well-formed record is `ADOPTION_RECORD_REFUSED`, with the specific reason codes
named in `adoption_record.py` (and declared, explicitly, in its `EMITTED_REASON_CODES`
constant). A record that is not even the right Python shape -- an unknown key, a missing
key, a field of the wrong type, at either the record's own top level or within the receipt
-- raises `AdoptionRecordError` instead: there is no admission question to answer for
something unreadable, the same distinction `authority.errors` and
`authority.verifier_selection` already draw between an unreadable input and a
readable-but-wrong one.

### 2.1 Governing context and recording location are separate (GAR-R2-F1)

Structural Review Round 1 (GAR-R1-F1) required `governing_issue` to name the same Issue or
Pull Request number that hosts `comment_url`'s own comment. Round 2 (GAR-R2-F1, Issue #53
comment 5565703135) superseded that rule as itself incorrect: a governing Issue may
legitimately be recorded through a comment on a *different* Issue or Pull Request -- an
adoption governing Issue #53 may be recorded as a comment on Pull Request #56, exactly as
this correction itself was. `governing_issue` (which unit this adoption semantically
governs) and `comment_url` (where it happens to have been recorded) are separate contexts,
and the module no longer conflates them.

What binds the record instead is the read-back receipt: the caller's own structured claim,
independently obtained through the GitHub API read-back, of what `adoption_id`,
`governing_issue`, `reviewed_sha`, and `comment_url` the read comment actually showed. A
receipt disagreeing with even one of the record's own declared fields of the same name is
refused for exactly that field -- `API_READ_BACK_RECEIPT_ADOPTION_ID_MISMATCH`,
`API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH`, `API_READ_BACK_RECEIPT_REVIEWED_SHA_
MISMATCH`, or `API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH`. An absent or empty receipt
disagrees with every non-empty declared field, so "the read-back was never actually
confirmed" needs no separate boolean flag or reason code of its own -- it surfaces as these
same mismatches.

### 2.2 Repository scope and decision-field binding (GAR-R3)

Round 3 (Issue #53 comment 5566075546) closed two further gaps.

**GAR-R3-F1**: `comment_url` -- previously any `https://github.com/<owner>/<repo>/...`
address -- is now scoped to exactly `manosube/manosube-agent-civilization-os`. A comment
hosted in a different repository is refused as `COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT`,
the same code a chat draft receives, *even when the record's own receipt names that same
foreign repository and would otherwise "agree"* -- a matching receipt for the wrong
repository is not a verified adoption for this one. Within this repository, §2.1's
decoupling is unchanged: `governing_issue` and `comment_url`'s own Issue/PR number may still
differ.

**GAR-R3-F2**: the read-back receipt grew from four fields to six. `decision_authority` and
`decision_status` are now bound the identical way `adoption_id`, `governing_issue`,
`reviewed_sha`, and `comment_url` already were -- a caller cannot declare
`decision_authority="SHUKOU"` at the record's own top level while the receipt's own claim of
what the read-back showed names a different authority or status. Disagreement on either
field is refused as `API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH` or
`API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH`.

## 3. What this enforcement is not

```text
NETWORK_CALL_MADE_BY_THIS_MODULE=false
GITHUB_TOKEN_HELD_BY_THIS_MODULE=false
SECRET_HELD_BY_THIS_MODULE=false
GITHUB_API_RUNTIME_VALIDATION_PERFORMED=false
AUTOMATIC_IMPLEMENTATION_AUTHORIZATION=false
NEW_CANONICAL_AUTHORITY_OWNER=false
```

`api_read_back_receipt` is the caller's own structured claim of what the read-back already
showed, out of band, before the record was constructed -- exactly the same independent API
confirmation this repository's own commit and Pull Request history already performs before
acting on every adoption it cites. This module can prove that the claim is *present*,
*well-typed*, and *internally consistent with the record it accompanies* (§2.1). It cannot
prove, and never claims to prove, that the remote comment currently exists or currently
reads as claimed -- that would require the network call this module deliberately does not
make.

```text
LOCAL_TEST_PROVES_RECORD_ADMISSION=true
LOCAL_TEST_PROVES_CURRENT_REMOTE_GITHUB_STATE=false
```

This mirrors `CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` §9's own explicit
`RUNTIME_ENFORCEMENT_IMPLEMENTED=false`: that document evaluates a *policy record*, never
watches the repository to guarantee no Agent ever acts without evaluating it first;
this document's own enforcement evaluates an *adoption record* the identical way, for the
identical reason. The owner of physical enforcement is a future Runtime, which v0.1 of this
system does not have.

## 4. How an executor uses this

Before beginning implementation from an instruction that claims a SHUKOU adoption, an
executor should be able to construct the instruction's own Governance Adoption Record (the
nine fields above, from the comment it independently re-read) and confirm
`evaluate_adoption_record` returns `ADOPTION_RECORD_ADMITTED`. A record that comes back
`ADOPTION_RECORD_REFUSED`, or that cannot even be constructed because a required field is
missing, names exactly which part of the canonical sequence in §1 has not actually
happened -- and implementation does not begin until it has.

## 5. Acceptance

```text
CONTRACT_STATIC_PROOF_IMPLEMENTED=true
OPERATING_GUIDE_WRITTEN=true
NEGATIVE_TESTS_PRESENT=true
POSITIVE_TEST_PRESENT=true
CHAT_DRAFT_REJECTED=true
UNPOSTED_TEXT_REJECTED=true
REVIEWED_SHA_MISMATCH_REJECTED=true
UNVERIFIED_READ_BACK_RECEIPT_REJECTED=true
COMPLETE_VERIFIED_ADOPTION_ADMITTED=true
SEMANTIC_AUTHORITY_TRANSFERRED=false
PR_52_MODIFIED=false
PHASE_13_SEMANTICS_MODIFIED=false
PHASE_14_STARTED=false
NEW_KERNEL_ELEMENT=false
NEW_AUTHORITY_OWNER=false
GITHUB_ADAPTER_IMPLEMENTED=false
RUNTIME_ENFORCEMENT_IMPLEMENTED=false
```

### 5.1 Structural Review Round 1 (GAR-R1) -- superseded by Round 2

Issue #53 comment 5565302174 (`ADOPT_GAR_R1_BOUND_RECORD_IDENTITY_AND_PRECISE_REASON_CODE_
SWEEP`) required `adoption_id` and `governing_issue` to be well-formed, and required
`governing_issue` to name the same Issue/PR number as `comment_url`'s own hosting path. The
route-drift guard's allowlist was replaced with an AST-based sweep limited to `_verdict(...)`
arguments and `.append()` calls.

```text
GAR_R1_F1_ADOPTION_ID_GOVERNING_REFERENCE_SHAPE_CHECKS=true
GAR_R1_F1_GOVERNING_ISSUE_BOUND_TO_COMMENT_URL_HOSTING_NUMBER=SUPERSEDED_BY_GAR_R2
GAR_R1_F2_AST_BASED_REASON_CODE_SWEEP=SUPERSEDED_BY_GAR_R2
```

### 5.2 Structural Review Round 2 (GAR-R2)

Issue #53 comment 5565703135 (`ADOPT_GAR_R2_SEPARATE_GOVERNING_AND_RECORDING_CONTEXTS`)
found GAR-R1-F1's own binding wrong -- see §2.1 -- and replaced it with the structured
read-back receipt. It also required the route-drift allowlist to derive only from each
evaluator's own explicit `EMITTED_REASON_CODES` declaration, with a bidirectional static
proof (every declared code reachable; every emitted code declared) rather than an inferred
sweep, however precise.

```text
GAR_R2_F1_READ_BACK_RECEIPT_INTRODUCED=true
GAR_R2_F1_GOVERNING_ISSUE_AND_COMMENT_URL_HOSTING_NUMBER_DECOUPLED=true
GAR_R2_F1_CROSS_ISSUE_PR_RECORDING_POSITIVE_CASE_ADMITTED=true
GAR_R2_F2_EMITTED_REASON_CODES_DECLARED_PER_EVALUATOR=true
GAR_R2_F2_ALLOWLIST_DERIVED_FROM_DECLARED_SURFACE_ONLY=true
GAR_R2_F2_BIDIRECTIONAL_REACHABILITY_AND_DECLARATION_PROOF=true
NETWORK_TOKEN_SECRET_ADAPTER_ADDED=false
```

### 5.3 Structural Review Round 3 (GAR-R3)

Issue #53 comment 5566075546 (`ADOPT_GAR_R3_REPOSITORY_SCOPED_AND_DECISION_BOUND_RECEIPT`)
closed two further gaps -- see §2.2: `comment_url` is scoped to this repository, and the
read-back receipt now also binds `decision_authority` and `decision_status`.

```text
GAR_R3_F1_COMMENT_URL_SCOPED_TO_THIS_REPOSITORY=true
GAR_R3_F1_FOREIGN_REPOSITORY_URL_REJECTED_EVEN_WHEN_RECEIPT_AGREES=true
GAR_R3_F1_SAME_REPOSITORY_CROSS_ISSUE_PR_RECORDING_STILL_ADMITTED=true
GAR_R3_F2_RECEIPT_EXTENDED_TO_SIX_FIELDS=true
GAR_R3_F2_DECISION_AUTHORITY_AND_STATUS_BOUND_BY_RECEIPT=true
GAR_R3_F2_EMITTED_REASON_CODES_AND_BIDIRECTIONAL_PROOF_UPDATED=true
NETWORK_TOKEN_SECRET_ADAPTER_ADDED=false
```
