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
governing_issue             the Issue this adoption governs, e.g. "#53"
comment_url                 an immutable GitHub comment URL --
                             https://github.com/<owner>/<repo>/(issues|pull)/<n>#issuecomment-<id>
decision_authority           must be "SHUKOU"
decision_status               must be "RATIFIED"
api_read_back_confirmed     a boolean: was comment_url actually read back
                             through the GitHub API before this record was built?
reviewed_sha                 the exact commit SHA the adoption reviewed
authorized_target_sha        the exact commit SHA the work this record authorizes
                             is based on or targets
```

The record admits (`ADOPTION_RECORD_ADMITTED`) only when every one of the following holds:

```text
comment_url matches the immutable-comment URL pattern
api_read_back_confirmed is exactly true
decision_authority == "SHUKOU"
decision_status == "RATIFIED"
reviewed_sha and authorized_target_sha are both real-shaped commit SHAs
reviewed_sha == authorized_target_sha
```

Any other well-formed record is `ADOPTION_RECORD_REFUSED`, with the specific reason codes
named in `adoption_record.py`. A record that is not even the right Python shape -- an
unknown key, a missing key, a field of the wrong type -- raises `AdoptionRecordError`
instead: there is no admission question to answer for something unreadable, the same
distinction `authority.errors` and `authority.verifier_selection` already draw between an
unreadable input and a readable-but-wrong one.

## 3. What this enforcement is not

```text
NETWORK_CALL_MADE_BY_THIS_MODULE=false
GITHUB_TOKEN_HELD_BY_THIS_MODULE=false
SECRET_HELD_BY_THIS_MODULE=false
GITHUB_API_RUNTIME_VALIDATION_PERFORMED=false
AUTOMATIC_IMPLEMENTATION_AUTHORIZATION=false
NEW_CANONICAL_AUTHORITY_OWNER=false
```

`api_read_back_confirmed` is the caller's own structured claim that the read-back already
happened, out of band, before the record was constructed -- exactly the same independent
API confirmation this repository's own commit and Pull Request history already performs
before acting on every adoption it cites. This module can prove that the claim is
*present*, *well-typed*, and *bound to a real-looking, individually addressable GitHub
comment URL*. It cannot prove, and never claims to prove, that the remote comment
currently exists or currently reads as claimed -- that would require the network call this
module deliberately does not make.

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
UNVERIFIED_URL_REJECTED=true
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
