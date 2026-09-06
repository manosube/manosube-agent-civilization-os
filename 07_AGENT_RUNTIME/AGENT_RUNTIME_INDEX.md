# Agent Runtime Index (Phase 12, Issue #49)

```text
DOC_TYPE=AGENT_RUNTIME_INDEX
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=AGENT-RUNTIME-INDEX-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=EPHEMERAL_EXECUTION_ADAPTER
CANONICAL_KERNEL_COUNT=1
AGENT_RUNTIME_OWNER_COUNT=1
PUBLIC_AGENT_START_ENTRY_POINT_COUNT=1
```

---

## 0. What this document is

This is the one entry point for the **Temporary Agent lifecycle** contract set -- the two
documents under `07_AGENT_RUNTIME/` that define how a temporary, non-authoritative Agent
lifetime is started over an already-verified Boot Context, and explicitly released.

```text
1. AGENT_RUNTIME_INDEX.md      (this document)
2. AGENT_RUNTIME_CONTRACT.md   the one public start route, its frozen semantics, and its
                                negative controls
```

Read `AGENT_RUNTIME_CONTRACT.md` for the load-bearing design; this document only fixes this
layer's own position relative to the rest of the Kernel and to Boot.

## 1. This is not a ninth Kernel element

`00_KERNEL/KERNEL_INDEX.md` §4 fixes exactly eight Kernel elements (Objective through
Reflow). The Temporary Agent lifecycle is not a ninth -- the same `KERNEL_ELEMENT=none`-style
convention Development Binding, Product Binding, Boot, and the CLI already use (here spelled
`EPHEMERAL_EXECUTION_ADAPTER`, since it is specifically a process-memory-only lifetime, never
a persisted or authoritative owner). It does not appear in `00_KERNEL/`'s own numbered reading
order, and it redefines no Kernel Contract's own semantics.

```text
KERNEL_ELEMENT=EPHEMERAL_EXECUTION_ADAPTER
CANONICAL_KERNEL_COUNT=1
```

## 2. This is not a second Boot owner, and not authoritative

The Temporary Agent lifecycle never validates, restores, or reverifies a Project itself --
that remains Boot's own, one-owner concern (`manosube_agent_civilization.boot.boot_project`).
It only *starts* one ephemeral, in-process handle over the already-verified `BootContext`
Boot returns, and *releases* it. A live Agent exposes only that already deep-frozen
`BootContext`; it grants no Authority, evaluates no Authority Decision, creates or executes
no Change, observes no external system, and closes no Difference.

```text
AGENT_IS_A_SECOND_BOOT_OWNER=false
AGENT_CALLS_BOOT_PROJECT_MORE_THAN_ONCE_PER_START=false
AGENT_GRANTS_AUTHORITY=false
AGENT_EVALUATES_AUTHORITY_DECISION=false
AGENT_EXECUTES_CHANGE=false
AGENT_OBSERVES_EXTERNAL_SYSTEM=false
```

## 3. This is not persistence, execution, or a second lifecycle owner

A `TemporaryAgent` exists only in process memory. It creates no canonical record, schema,
directory, journal, manifest, cache, resume token, durable agent id, or long-term memory, and
makes zero Store writes on start, use, release, and every rejection. It never calls a model
provider, executes a prompt or tool, runs a subprocess or shell command, makes a network or
GitHub call, reads a URL, enumerates a filesystem, runs a scheduler or background loop, or
messages another Agent.

```text
AGENT_IS_PERSISTED=false
AGENT_MAY_MUTATE_STORE=false
MODEL_PROVIDER_IMPLEMENTED=false
PROMPT_EXECUTION_IMPLEMENTED=false
TOOL_EXECUTION_IMPLEMENTED=false
COMMAND_EXECUTION_IMPLEMENTED=false
SCHEDULER_IMPLEMENTED=false
BACKGROUND_AGENT_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
```

## 4. Canonical owner

```text
src/manosube_agent_civilization/agent_runtime/
├── __init__.py     public exports
├── errors.py        AgentRuntimeError / AgentReleasedError
├── agent.py         TemporaryAgent (public ABC interface) / _ActiveTemporaryAgent (private)
└── route.py         start_temporary_agent -- the one public start route
```

No second Boot, Store, Lineage, Recovery, Objective, Boundary, Authority, or Binding owner is
created anywhere in this package. `start_temporary_agent` invokes the existing
`manosube_agent_civilization.boot.boot_project` exactly once and wraps its returned
`BootContext` in one `TemporaryAgent`; no new schema and no new persisted record kind is
introduced.

**Structural Review Round 1 correction (SHUKOU adoption
`ADOPT_P12_R1_CANONICAL_TEMPORARY_AGENT_CONSTRUCTION`) -- superseded by Round 2, below.** The
initial delivery left `TemporaryAgent.__init__` publicly callable with any caller-supplied
`BootContext` -- `BootContext` is itself publicly constructible, so a caller could fabricate an
active Agent without ever calling `start_temporary_agent` or `boot_project`. Round 1 added a
private construction token (`agent._ROUTE_CONSTRUCTION_TOKEN`) that only `route.py` ever
imported, required as `TemporaryAgent.__init__`'s `_construction_token` argument.

**Structural Review Round 2 correction (SHUKOU adoption of P12-R2-F1).** Round 1's token was
only an importable module attribute -- it proved no real construction provenance, since any
caller could `import` it directly, construct a `BootContext` directly, and hand both to
`TemporaryAgent(...)` without `boot_project` ever running. The token/capability scheme
(`_ROUTE_CONSTRUCTION_TOKEN`, `_ConstructionToken`, `AgentConstructionError`) is removed
entirely, with no replacement secret, closure, stack-inspection, environment value, cache,
registry, or persisted receipt. `TemporaryAgent` is now the public lifecycle *interface*: a
real `abc.ABC` declaring only `boot_context`/`release` as abstract members and no `__init__` of
its own, so `TemporaryAgent(...)` always raises Python's own `TypeError` regardless of what is
supplied. The concrete implementation, `_ActiveTemporaryAgent`, is never exported from this
package; only `start_temporary_agent`, immediately after its own single `boot_project` call,
ever instantiates it. This is a public-API and ownership boundary, not a claim that hostile
code running in the same Python process -- deliberately importing this private module and
subclassing or monkeypatching around it -- is cryptographically isolated; no mechanism in
Python achieves that, and this layer never claims otherwise. What it actually guarantees: every
ordinary caller going through this package's public, documented surface cannot obtain an active
Agent except by way of a real `boot_project` call. This is again a construction-boundary
correction, not a semantic redesign: the public start route, release terminality, deep
immutability, typed owner-error propagation, and zero-Store-mutation guarantees are all
unchanged and independently retested.

## 5. Explicit non-claims

```text
TEMPORARY_AGENT_IMPLEMENTED=true
MODEL_PROVIDER_IMPLEMENTED=false
PROMPT_EXECUTION_IMPLEMENTED=false
TOOL_EXECUTION_IMPLEMENTED=false
COMMAND_EXECUTION_IMPLEMENTED=false
OBSERVER_IMPLEMENTED=false
SCHEDULER_IMPLEMENTED=false
BACKGROUND_AGENT_IMPLEMENTED=false
PERSISTENT_AGENT_MEMORY_IMPLEMENTED=false
AGENT_RESUME_IMPLEMENTED=false
GITHUB_ADAPTER_IMPLEMENTED=false
NETWORK_ACCESS_IMPLEMENTED=false
RUNTIME_OBSERVATION_IMPLEMENTED=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
AUTONOMOUS_CHANGE_IMPLEMENTED=false
MULTI_AGENT_IMPLEMENTED=false
NEW_STATE_OWNER=false
NEW_AUTHORITY_OWNER=false
NEW_PERSISTED_ARTIFACT=false
PHASE_12_COMPLETE=false
PHASE_13_ALLOWED=false
```
