# Agent Runtime Contract (Phase 12, Issue #49)

```text
DOC_TYPE=AGENT_RUNTIME_CONTRACT
DOCUMENT_ID=AGENT-RUNTIME-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=EPHEMERAL_EXECUTION_ADAPTER
PREDECESSOR_ISSUE=#47
PREDECESSOR_PR=#48
PREDECESSOR_MERGE_COMMIT=b1b98b9feb79058c407a7733586542b031c50ce2
```

See `AGENT_RUNTIME_INDEX.md` for this contract set's own position and reading order.

## 1. Position

This layer adds exactly one provider-neutral, in-process lifecycle adapter over the existing,
already-verified Phase 10 Boot route (`manosube_agent_civilization.boot.boot_project`), so a
caller can hold a temporary, non-authoritative Agent lifetime over a verified Boot Context and
explicitly release it. It is produced by exactly one owner
(`manosube_agent_civilization.agent_runtime`) and its one public start route invokes Boot
exactly once.

```text
AGENT_RUNTIME_OWNER_COUNT=1
PUBLIC_AGENT_START_ENTRY_POINT_COUNT=1
```

## 2. Public signature

```python
start_temporary_agent(
    store,
    *,
    project_id: str,
    project_binding_id: str,
) -> TemporaryAgent
```

```python
agent.boot_context  # read-only while active
agent.release()  # idempotent, local, zero-write
```

Start requires exactly the same explicit inputs Boot itself requires: a caller-supplied
`store`, `project_id`, and `project_binding_id`. No current-working-directory, environment,
filesystem scan, cache, "only Project" inference, or recovery is permitted (frozen semantic
decision 2). No CLI command, console-script extension, process daemon, provider adapter, or
second public lifecycle entry point is introduced in this Phase.

## 3. Frozen semantic decisions

1. **One lifecycle adapter, existing owners only.** This layer owns only ephemeral lifetime
   state: active versus released. Boot restores; the Store persists; Binding and Authority
   retain their existing owners. This layer creates none of these a second time.
2. **Explicit canonical start.** Start requires caller-supplied `store`, `project_id`, and
   `project_binding_id`. No cwd, environment, filesystem scan, cache, "only Project"
   inference, or recovery is permitted.
3. **Boot exactly once.** The public start route calls `boot_project` exactly once, never
   `load_current`, bare `reconstruct`, `initialize`, `bind_project`, `commit`, or `recover`.
4. **Ephemeral only.** A `TemporaryAgent` exists only in process memory. It creates no
   canonical record, schema, directory, journal, manifest, cache, resume token, durable agent
   id, or long-term memory.
5. **Non-authoritative.** A live Agent exposes only the already deep-frozen `BootContext`; it
   grants no Authority and cannot evaluate Authority, create/execute Change, observe an
   external system, or close a Difference.
6. **Release is terminal.** `release()` is local, idempotent, and zero-write. After release,
   access through the Agent handle to its context/lifecycle service fails with one typed
   `AgentReleasedError`; it cannot be restarted or resumed.
7. **Domain errors propagate unchanged.** Boot/Binding/Store/Authority failures propagate
   their owning typed exceptions. This layer defines a typed error only for its own lifecycle
   boundary (`AgentReleasedError`), never reclassifying an owning-domain refusal.
8. **Deterministic verified context.** Repeated fresh-process starts over an unchanged bound
   Store yield byte-equivalent projections of the Agent's Boot Context. The Agent object's
   Python identity is not a persisted or canonical identity.
9. **No hidden execution.** There is no model call, prompt, tool invocation, subprocess,
   shell, network/GitHub call, URL read, filesystem enumeration, command execution,
   scheduler, background loop, or Agent-to-Agent messaging.
10. **Strict phase boundary.** Independent Verification (13), GitHub (14), Runtime (15),
    model replaceability (16), URL read-only (17), autonomous Change (18), and multi-Agent
    (19) remain out of scope.
11. **Canonical construction only (Structural Review Round 2, P12-R2-F1; supersedes Round 1's
    `AgentConstructionError`/construction-token design).** Round 1's private construction
    token was only an importable module attribute -- it proved no real provenance, since any
    caller could `import` it directly and hand it, plus a directly-constructed `BootContext`,
    to `TemporaryAgent(...)` without `boot_project` ever running. `TemporaryAgent` is instead
    the public lifecycle *interface*: an `abc.ABC` declaring only `boot_context`/`release` as
    abstract members, with no `__init__` of its own. `TemporaryAgent(...)` therefore always
    raises Python's own `TypeError` for an uninstantiable abstract class, regardless of what
    is supplied. The concrete implementation, `_ActiveTemporaryAgent`, is never exported from
    this package; only `start_temporary_agent`, immediately after its own single
    `boot_project` call, ever instantiates it, returning it typed as the public
    `TemporaryAgent` interface. This is a public-API and ownership boundary, not a claim that
    hostile code running in the same Python process -- deliberately importing this private
    module and subclassing or monkeypatching around it -- is somehow cryptographically
    sandboxed; no mechanism in Python achieves that, and this layer does not claim otherwise.
    What it actually guarantees: every ordinary caller going through this package's public,
    documented surface (`TemporaryAgent` the type, `start_temporary_agent` the function)
    cannot obtain an active Agent except by way of a real `boot_project` call.

## 4. Canonical owner

```text
src/manosube_agent_civilization/agent_runtime/
├── __init__.py     public exports
├── errors.py        AgentRuntimeError / AgentReleasedError
├── agent.py         TemporaryAgent (public ABC interface) / _ActiveTemporaryAgent (private)
└── route.py         start_temporary_agent -- the one public start route
```

`AgentReleasedError` exists only for the one lifecycle check this layer itself owns (access to
a released Agent's context). Every other failure mode propagates the existing owning domain's
own typed error unchanged -- `manosube_agent_civilization.boot.
{BootNotFoundError,BootConsistencyError}`, `manosube_agent_civilization.binding.errors.
{BindingIdentityError,BindingValidationError}`, `manosube_agent_civilization.store.errors.
{CorruptStoreError,StateNotFoundError,BoundaryError,...}`, and
`manosube_agent_civilization.authority.errors.*` -- this layer never catches or rewraps any
of them.

`agent.py` owns one further, unexported implementation detail: `_ActiveTemporaryAgent`, the
one private concrete subclass of the public `TemporaryAgent` interface. `route.py` is the only
module that ever imports or instantiates it (Structural Review Round 2, P12-R2-F1); it is not
part of this package's public exports, and `TemporaryAgent` itself, being an `abc.ABC` with no
concrete implementation, cannot be instantiated directly by anyone.

## 5. Canonical successful route

```text
1. Invoke boot_project(store, project_id=..., project_binding_id=...) exactly once -- the
   identical restoration route Phase 11's CLI already invokes, reused rather than restated.
2. Wrap the returned, already deep-frozen BootContext in one new TemporaryAgent, active.
3. Return that TemporaryAgent to the caller. Zero Store writes occurred.
4. The caller reads agent.boot_context (read-only, byte-identical to what boot_project
   itself returned) as many times as it likes while the Agent remains active.
5. The caller calls agent.release() exactly when it is done. Zero Store writes occur; the
   call is idempotent; a second call has the identical effect.
6. After release, agent.boot_context raises AgentReleasedError. The Agent cannot be
   restarted, resumed, used to restore, or used to recover a Store.
7. Prove the identical route from a fresh Python process, repeated, with byte-equal
   BootContext projections each time and zero Store mutation.
```

## 6. Required rejection proofs

At minimum, this layer fails closed, with zero Store mutation
(`STATE_TRANSITION_COUNT_DELTA=0`, `LINEAGE_APPEND_COUNT_DELTA=0`, `RECORD_COUNT_DELTA=0`,
`TRANSACTION_MANIFEST_COUNT_DELTA=0`, `EXTERNAL_OPERATION_COUNT_DELTA=0`), and no
`TemporaryAgent` produced, for every failure mode Boot itself already proves fail-closed
(propagated through this layer unchanged, never reclassified):

```text
- missing Project or Product Binding (BootNotFoundError)
- a tampered persisted Project Binding, Objective Revision, or Authority Rule
  (CorruptStoreError, via the Store's own generic manifest-claimant tamper detection)
- an interrupted transaction at a representative crash stage, a later transaction's deleted
  recovery journal, and a later transaction's recovery journal replaced by a non-directory
  entry -- all collapse to the Store's own CorruptStoreError, propagated unchanged
- a malformed or lineage-divergent present current.json view (CorruptStoreError)
```

And, for this layer's own lifecycle boundary:

```text
- access to agent.boot_context after agent.release() raises AgentReleasedError, with zero
  Store mutation and no residue of any kind
- calling agent.release() a second time (or more) is a zero-write no-op -- idempotent, never
  an error
- a released Agent cannot be restarted, resumed, or reused to start a new Agent, restore a
  Project, or recover a Store: there is no method on a released (or active) TemporaryAgent
  that does any of those things
- static conformance proves exactly one public start route (start_temporary_agent) and
  exactly one lifecycle type (TemporaryAgent); that boot_project is called exactly once, in
  exactly one place; that route.py/agent.py/__init__.py never call
  initialize/commit/recover/load_current/bind_project/reconstruct; and that no module in this
  package imports a model, subprocess, shell, network, GitHub, Observer, Change-execution,
  scheduler, or multi-Agent surface
- a direct TemporaryAgent(...) call -- with no arguments, or with a real BootContext obtained
  through a direct boot_project call rather than through start_temporary_agent -- always
  raises Python's own TypeError for an uninstantiable abstract class (P12-R2-F1, superseding
  Round 1's AgentConstructionError/token proof)
- static conformance proves inspect.isabstract(TemporaryAgent) and that its
  __abstractmethods__ are exactly {"boot_context", "release"}; that _ActiveTemporaryAgent is
  imported and instantiated nowhere but route.py, and exported nowhere in __all__; and that no
  construction-token/capability scheme (_ROUTE_CONSTRUCTION_TOKEN, _ConstructionToken,
  AgentConstructionError) remains anywhere in this package
- a rejected direct construction attempt calls boot_project zero times and mutates the Store
  zero times; the canonical start_temporary_agent route itself remains completely unaffected
  and still calls boot_project exactly once
```

## 7. Explicit non-claims

```text
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
```
