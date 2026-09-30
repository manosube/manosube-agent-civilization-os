# Copilot participation in repository development

```text
DOCUMENT_ID=COPILOT-PARTICIPATION-0001
DOC_TYPE=DEVELOPMENT_BINDING_CHANGE_PROPOSAL
KERNEL_ELEMENT=none
STATUS=DESIGN_PREPARED_AWAITING_INDEPENDENT_REVIEW_AND_HUMAN_ACCEPTANCE
GOVERNING_ISSUE=#102
DIFFERENCE_ID=D-COPILOT-EXCHANGEABLE-DEVELOPMENT-EXECUTOR
REQUEST_RECORD=https://github.com/manosube/manosube-agent-civilization-os/issues/102
ADOPTION_ID=ADOPT_COPILOT_DEVELOPMENT_BINDING_DESIGN_20261001
OBSERVED_BASE_MAIN=391378d8aeb784a62cd2bc93d96538443c754a2d
ACTIVE_BINDING=DEV-BINDING-0001
ACTIVE_POLICY_VERSION=0.2
COPILOT_MACHINE_ADMISSION_IMPLEMENTED=false
COPILOT_NATURAL_WORK_UNIT_OBSERVED=false
MERGE_ALLOWED=false
ISSUE_CLOSE_ALLOWED=false
```

## Purpose and current truth

SHUKOU requested Kernel-compatible Copilot participation on 2026-10-01 JST.
The Structural Advisor recorded the direct session request in Issue #102. The
record is provenance of the design request, not a claim that SHUKOU has accepted
this eventual PR's exact delivery SHA.

This is a change to this repository's **Development Binding** participant
selection. It is not a new Product Binding genesis. Do not call
`binding.route.bind_project` merely to enroll an assistant, duplicate a Store,
add a ninth Kernel element or register a provider policy under `01_SCHEMA/`.
`BINDING_INDEX.md` distinguishes these two binding domains.

The existing Development Binding selects Claude Code for implementation. Its
JSON policy is pinned in `development_binding.policy`; the evaluator and adoption
record machinery are the existing admission owners. `request_copilot_review`
is prohibited by the current policy. Instructions alone cannot change these facts.
The active binding's participant assignment and Human authority remain in effect
until an explicit superseding decision is independently reviewed and accepted.

The file `.github/copilot-instructions.md` supplies repository guidance, including
this current restriction. It is guidance to an AI, not a deterministic enforcement
boundary. Adding it neither activates Copilot nor proves policy conformance.

## Proposed participant selection

| Responsibility | Owner / capability |
| --- | --- |
| Objective, boundary, finding disposition, final acceptance, manual merge | SHUKOU |
| Canonical State, Difference, Authority, Evidence and Reflow semantics | Existing canonical Kernel owners |
| Structural observation, handoff and independent structural review | ChatGPT Structural Advisor |
| Implementation for one authorized work unit | One selected executor: Claude Code or GitHub Copilot |
| Copilot research / review findings | Observation candidates, never authority |
| Commits, Issues, PRs and receipts | GitHub audit surface |

One work unit must select one actual provider. Preserve the provider identity in
records; do not normalize Copilot to CLAUDE_CODE. Selection must bind to the
governing Issue, Difference, adoption URL, authorized repository, branch/PR,
base/head, allowed actions and path scope. An eligible-provider list never grants
execution by itself. Provider replacement requires an explicit replacement record
and preserved before-State, unresolved Differences and prior evidence lineage.

Copilot may implement, test, self-review and prepare a PR only after executable
admission and that work-unit selection exist. Claude Code remains available.
Copilot cannot structurally accept its own changes. Its findings start
`UNVERIFIED_EXTERNAL_OBSERVATION` and become implementation input only after
SHUKOU explicitly adopts the exact finding and disposition.

Neither this proposal nor a trial silently enables automated reviews. Keep the
current default prohibition. Any later review trial needs a separate explicit
Human grant consistent with the ratified policy; no new mandatory acceptance gate.

## Implementation handoff

Next implementation owner is Claude Code, using the existing Development Binding
route after Human acceptance of this exact design and a verified implementation
handoff. The Structural Advisor prepares this document but does not author code
or independently approve its own design.

1. Inventory all provider-pinned consumers before choosing the smallest compatible
   revision: policy constants/loader, evaluator, adoption-record validation,
   transition state names, handoff/completion templates, installed-wheel resource
   handling, active binding and current-source projections.
2. Evolve the existing policy/evaluator, not a parallel Copilot evaluator. Pin the
   new ratified content consistently in code and JSON. Preserve legacy Claude Code
   records and historical Human decisions without rewriting their meaning.
3. Separate implementation capability from actual provider selection. Admit the
   selected provider for precisely one work unit; reject unknown providers,
   missing grants, scope mismatches, changed SHA, replay across work units and
   duplicate active selections. Do not create a permissive alias or unchecked
   provider string.
4. Preserve the existing review/acceptance/merge ownership and fail-closed
   behavior. Keep automated external review prohibited by default. Update the
   relevant active documents and specific source projections in the same diff.
5. Prove valid Claude Code and Copilot delivery, prohibited Copilot actions,
   self-acceptance and merge refusal, unadopted-finding refusal, policy tampering
   rejection, selection integrity and installed-wheel conformance.
6. Run the agreed focused binding/adoption/wheel tests, source-impact and
   freshness checks and required final suite. Record actual terminal results,
   baseline failures and remaining Differences. Stop at
   `READY_FOR_STRUCTURAL_REVIEW`.

Issue #102 carries the authorized design scope and remaining implementation
obligation. This document does not itself grant that next code work unit.

## Trial handoff fields

After the revised binding is accepted, SHUKOU selects one small reversible work
unit. These placeholders must be filled and read back; blanks are not authority.

```text
WORK_UNIT_ID=<exact identity>
DIFFERENCE_ID=<exact identity>
GOVERNING_ISSUE=<URL>
VERIFIED_ADOPTION_URL=<read-back record>
ADOPTION_ID=<exact identity>
AUTHORIZED_REPOSITORY=manosube/manosube-agent-civilization-os
AUTHORIZED_BRANCH_OR_PR=<exact branch or PR>
AUTHORIZED_BASE_SHA=<exact commit>
EXPECTED_HEAD_SHA=<exact commit when updating>
SELECTED_EXECUTOR_PROVIDER=GITHUB_COPILOT
REQUIRED_CAPABILITY=IMPLEMENTATION_EXECUTOR
PERMITTED_PATHS=<closed work-unit scope>
PERMITTED_ACTIONS=<closed work-unit scope>
CLOSURE_CONDITION=<observable result>
REQUIRED_EVIDENCE=<commands and artifact references>
PROHIBITED_ACTIONS=merge,issue_close,production_deployment,billing,credentials,destructive_operation
AUTOMATED_EXTERNAL_REVIEW_REQUEST_ALLOWED=false
EXECUTOR_TERMINAL_STATE=READY_FOR_STRUCTURAL_REVIEW
STRUCTURAL_REVIEW_OWNER=CHATGPT
FINAL_ACCEPTANCE_OWNER=SHUKOU
MERGE_OPERATION_OWNER=SHUKOU
```

Use this as selection input to the accepted existing owner, not a new schema or
alternate authorization channel. GitHub assignee status and Copilot entitlement
are not grants. If service access or assignment is unavailable, record BLOCKED
without manufacturing runtime evidence.

## Evidence and closure

| Stage | Evidence needed | Current observation |
| --- | --- | --- |
| Design | Exact draft files and source comparison | Prepared in design PR |
| Integration | Independent review, SHUKOU acceptance, exact merge and read-back | Pending |
| Executable admission | Positive/negative records through existing evaluator, checkout and wheel | Not implemented |
| Copilot operation | One actual authorized Copilot work unit returns SHA-bound PR and evidence | Unobserved |
| Reflow | Independent structural review, Human decision and accepted after-State | Unobserved |

Do not close Issue #102 from the instructions PR alone. Full closure requires the
accepted instructions, executable selection enforcement, a real bounded Copilot
trial and evidence reflow. Failure or unavailable service is an explicit remaining
Difference. Do not claim RUNTIME_PROVEN from fixtures, instructions, a Copilot
comment or a merged design document.

## GitHub guidance consulted

Official documentation retrieved when preparing this design:
- [Repository custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
- [Customizing code review](https://docs.github.com/en/copilot/tutorials/customize-code-review)

GitHub supports repository-wide `.github/copilot-instructions.md`. AI adherence
is non-deterministic. No plan purchase, paid execution, account configuration,
repository setting or automated review trigger is part of this design PR.
