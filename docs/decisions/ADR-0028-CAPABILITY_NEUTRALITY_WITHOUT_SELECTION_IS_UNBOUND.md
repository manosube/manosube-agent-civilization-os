# ADR-0028 — A capability left unselected is a capability anyone may supply

**Status:** accepted
**Bounds:** KERNEL_VERTICAL_WORK_UNIT_DELIVERY §6/§9, HUMAN_AGENT_WORK_COMMUNICATION §7A,
SECURITY.md §5, KERNEL_INVARIANTS B-002.
**Ratified decision:** `HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0001` (Issue #34).

## 0. What went wrong

An automated code reviewer was placed on this repository's critical path. It was never
decided on. It arrived because nothing had decided otherwise.

The sequence, as it actually ran:

1. The Structural Advisor substituted an automated review trigger for the acceptance step.
2. The reviewer returned findings.
3. The findings were converted into implementation work without an explicit Human adoption.
4. The executor, on finishing that work, posted an automated-review trigger **itself** —
   unprompted, not in the work package.

Step 4 is the one worth dwelling on. By then the loop was self-sustaining: no participant had
to choose it again, because the route had become the shape of the work.

## 1. The protocol text was correct and did not prevent it

`KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md` §6 defines the observation, acceptance and execution
capabilities without naming a provider, and states plainly:

> No named provider, API, version-control product, model or Agent is required for protocol
> conformance.

That sentence is right, and it is still right. It is also not a selection.

```text
CAPABILITY DEFINED  ≠ IMPLEMENTER SELECTED
```

§6 delegated the selection to the Structural Advisor and gave it **nowhere to be recorded**.
An unrecorded selection is not a weak selection; it is an open slot. Any implementer may fill
it, at any time, and nothing in the repository can tell that a substitution occurred — because
there was no prior value to differ from.

Provider neutrality made the Kernel replaceable. It also made the *development operation*
unbound, and those are different properties that one sentence was serving.

## 2. Why the fix is a Binding rather than a rule in the protocol

Writing "do not use an automated reviewer" into §6 would have made a named provider part of a
provider-neutral protocol — the exact thing §6 exists to prevent. The prohibition is
repository-specific; the protocol is not.

So the protocol gains one thing only: the *requirement that a repository record its own
selection*, and a pointer to where this repository records it. The selection itself lives in
`03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md`, outside Kernel semantics.

```text
REPOSITORY_BINDING_SELECTS_IMPLEMENTERS=true
REPOSITORY_BINDING_REDEFINES_CAPABILITY_SEMANTICS=false
NAMED_PROVIDER_REQUIRED_FOR_PROTOCOL_CONFORMANCE=false
```

The policy artifact sits in `03_BINDING/`, not `01_SCHEMA/`, for the same reason: the
canonical schema registry *is* Kernel semantics, and putting four provider names into it would
make them Kernel organs. A conformance test reads every file under `01_SCHEMA/` and fails if a
participant's name appears in any of them.

## 3. Why a document was not enough, twice over

This is the second time in this repository that a correctly-written rule failed to hold, and
the two failures have the same shape.

- Phase 5's P1: `CHANGE_CONTRACT.md` §8 asserted a provenance check the engine never
  performed. A digest recomputation stood in its place and resembled it closely enough that
  nobody noticed — including the person who wrote the sentence.
- This incident: §6 described capability neutrality correctly, and the description alone did
  not stop a reviewer being inserted.

```text
A RULE DESCRIBED = 期待
A RULE EVALUATED = 拒否
```

So the Binding is implemented as a predicate over records (`development_binding.evaluation`),
and the conformance boundary evaluates representative handoff, action and finding-disposition
records rather than searching documents for phrases. A phrase can be paraphrased; a record
either passes the guard or does not.

The one text check that remains — keeping the shipped templates free of prohibited triggers —
is documented as the weakest guard in the package, precisely so it is not mistaken for the
boundary.

## 4. The adoption gate, and the argument it has to survive

Every external reviewer, bot, model, CI annotation and generated report begins as
`UNVERIFIED_EXTERNAL_OBSERVATION`, and becomes work only through an explicit Human adoption
bound to that exact observation and that exact disposition.

The hard case is not a wrong finding. It is a **right** one. The PR #33 P1 was correct, and
acting on it produced a genuinely better system. If technical correctness could substitute for
adoption, the adoption step would not exist — every bypass would be justified in retrospect by
the quality of what followed.

```text
CORRECTNESS ≠ ADOPTION
SILENCE ≠ ADOPTION
SEVERITY ≠ ADOPTION
A COMPLETED REVIEW ≠ ACCEPTANCE
```

The right thing to do with a correct unadopted finding is to present it. That disposition is
permitted, and it is the whole permitted set.

## 5. Precedence, and why it had to be stated

The reviewer was not invoked because anyone preferred it. It was invoked because the
integration made it the nearest available action, and nothing outranked "the nearest available
action".

```text
1  HUMAN_RATIFIED_CURRENT_REPOSITORY_BINDING
2  AGENT_SYSTEM_PROMPT
3  AGENT_TOOL_DEFAULT_BEHAVIOUR
4  PULL_REQUEST_BODY_TEXT
5  EXTERNAL_BOT_COMMENT
6  CONVENIENCE
```

An agent's system prompt is below the ratified Binding on this list. So is the default
behaviour of any tool it holds, the text of a PR it is working on, and the content of any bot
comment it reads. Those are the four surfaces through which this incident arrived.

## 6. What this does not claim

```text
RUNTIME_ENFORCEMENT_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
AGENT_ADAPTER_IMPLEMENTED=false
KERNEL_SEMANTICS_MODIFIED=false
```

`RUNTIME_ENFORCEMENT_IMPLEMENTED=false` is the important one. This Binding evaluates records.
It does not physically prevent an agent from acting without consulting it — enforcement is a
Runtime's job, and v0.1 has no Runtime. The guard raises the cost of the prohibited route and
makes a crossing visible in the test suite; it does not make one impossible.

Stating the boundary narrower than the claim is what the P1 taught. A claim broader than its
implementation is invisible to the person making it.

## 7. Consequences

The four participants building this repository are now named, closed, and evaluable, while the
Kernel they are building remains provider-neutral and its agents remain replaceable. Those two
facts are not in tension: one governs the construction, the other governs the artifact.

```text
CONSTRUCTION_BOUND
ARTIFACT_NEUTRAL
```
