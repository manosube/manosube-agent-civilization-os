# Runtime observation transports (Issue #105)

This is an operator-facing guide, not a canonical design document. The load-bearing design
lives in `10_RUNTIME/RUNTIME_CONTRACT.md` §17 (read that first if you are changing behavior,
not just operating it); this file only explains how to actually use what that section
describes.

Issue #64 shipped one way to observe a running deployment: `HTTP_GET_BOUNDED`, a bounded HTTP
GET. Issue #105 adds a second, `SSH_EXEC_BOUNDED`, for a target reachable only over SSH, plus
two ways to run it:

- **Capability A -- manual.** A Human operator is shown an exact, copy/paste-able `ssh`
  command, runs it themselves, and feeds the result back in. No grant is strictly required for
  a Human to simply run a command this package rendered; a grant is required before this
  package's own CLI will *render* one, because rendering is itself part of what Issue #105's
  adoption gates.
- **Capability B -- grant-gated unattended.** This package runs the identical `ssh` command
  itself, with no Human present at the moment of execution, but only when a Human-ratified
  grant explicitly says so, for that exact target, right now.

Neither capability connects to anything by merely existing. Nothing in this delivery holds a
credential, provisions a key, or is wired into a real target -- every example below runs
against a local fixture or is marked as not yet executed against anything real.

## 1. Prerequisites

- This package installed (editable is fine): `pip install -e .`
- An `ssh` client available wherever Capability A's command is actually run (a Human's own
  machine, or a GitHub Actions runner -- `ubuntu-latest` ships one).
- For Capability B only: a **bounded-SSH-observation grant**, ratified by SHUKOU (see §2).
- `scripts/runtime_observation_probe.py` deployed, read-only, to the target -- the one script
  the rendered/executed command actually runs there. Deploying it is an operational step this
  delivery does not perform; see §5.

Nothing here requires or assumes a VPS or cloud provider exists yet. Every command in this
guide can be exercised against `127.0.0.1` with the probe script copied onto the same machine.

## 2. The grant

A grant is a plain JSON object -- not a canonical Store record, not a new Kernel element, and
not resolved through Boot. It is checked entirely offline, by
`manosube_agent_civilization.runtime.transport_control.require_valid_grant` and its siblings,
exactly the way `development_binding`'s own executor-eligibility grants are checked in a
different part of this Kernel. Its *fields* name a target, a probe artifact, and a window; what
makes it a grant at all is its own `signature` -- a genuine Ed25519 signature by the exact
Project Binding's own Human Authority, verified against a fresh Boot restoration for the exact
`project_id`/`project_binding_id` the attempt is actually using (PR #108 Structural Review
Round 1, F1) -- never a self-asserted `decision_status` string alone.

```jsonc
{
  "schema_version": "0.1",
  "grant_id": "GRANT-2026-EXAMPLE-1",
  "project_id": "PRJ-EXAMPLE",
  "project_binding_id": "PROJBIND-EXAMPLE",
  "provider": "local",
  "deployment_id": "widget-service",
  "instance_identity": "widget-service-1",
  "deployment_fingerprint": "sha256:<64 hex chars -- the target's own current claimed identity>",
  "host": "127.0.0.1",
  "port": 22,
  "user": "probe",
  "probe_identity": "OS_HEALTH_SNAPSHOT_BOUNDED",
  "probe_script_sha256": "<the real, current SHA-256 of scripts/runtime_observation_probe.py>",
  "deployment_config_fingerprint": "<SHA-256 of this exact target's own sibling runtime_observation_probe.config.json paths -- see §5>",
  "permitted_fields": ["hostname"],
  "redaction_fields": [],
  "max_output_bytes": 1048576,
  "max_lines": 200,
  "max_timeout_seconds": 30,
  "permitted_transports": ["MANUAL_SSH"],
  "issued_at": "2026-01-01T00:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z",
  "decision_status": "RATIFIED",
  "signature": {
    "algorithm": "ed25519",
    "key_id": "<the Project Binding's own human_authority_signing_key.key_id>",
    "value": "<128 hex chars -- signed over every field above except signature itself>"
  }
}
```

Every field is required; no field is optional and no unknown field is accepted. `probe_identity`
must be one of exactly `OS_HEALTH_SNAPSHOT_BOUNDED` / `SOURCE_LOG_EXCERPT_BOUNDED` -- the same
closed vocabulary a Boundary's own `endpoint.probe_identity` uses. `permitted_transports` lists
which of `GITHUB_ACTIONS` / `MANUAL_SSH` / `PREAUTHORIZED_UNATTENDED_SSH` this one grant
authorizes; a grant that should permit Capability A, a real Actions-executed observation, and
the unattended half of Capability B lists all three. `decision_status` must be exactly
`"RATIFIED"` and `signature` must genuinely verify against the real Project Binding -- there is
no default-admit path, and an unratified or unsigned grant is refused with the identical error
every other malformed field is.

**`deployment_fingerprint` and `probe_script_sha256` (PR #108 Structural Review Round 2,
SR2-F2/SR2-F4).** `deployment_fingerprint` binds the grant to the target's own *current* claimed
identity, not merely its stable provider/deployment/instance coordinates -- a grant issued
against one declared identity is refused once the real attempt's own target has rotated to a
new one, even though every other coordinate still matches. `probe_script_sha256` must equal the
real, current SHA-256 digest of `scripts/runtime_observation_probe.py` as this repository ships
it (`manosube_agent_civilization.runtime.types.SSH_PROBE_SCRIPT_SHA256`); because this field is
itself one of the fields the Human Authority's own signature covers, a live probe report's own
self-reported digest is compared against *this exact grant's* signed value, never against the
bare public constant directly.

**Corrected claim (PR #108 Structural Review Round 4, SR4-F4).** Earlier text here said a
"forged or substituted digest can never be made to agree with a genuine signature" -- that
overstates what this comparison proves. `probe_script_sha256` and `SSH_PROBE_SCRIPT_SHA256`
are both *public* values; a substitute script can trivially print back the expected public
digest without forging anything, since copying a known value defeats no signature at all. What
this comparison actually proves is only that the probe's own self-report *agrees with* the
grant's signed expectation -- a consistency check, never an independent cryptographic
attestation that the artifact which produced the report is genuinely the one reviewed and
pinned. This is a disclosed, honestly bounded guarantee: no stronger remote attestation
primitive exists over plain SSH, and a fully compromised target can report whatever digest it
likes.

**`deployment_config_fingerprint` (PR #108 Structural Review Round 3, SR3-F4).**
`probe_script_sha256` alone left a gap: two deployments can run the byte-identical probe script
(so both share one `probe_script_sha256`) while each resolves its own, different sibling
`runtime_observation_probe.config.json` (§5) -- so a grant issued for one target's own
source/log paths could be replayed, unmodified, against a different target whose sibling config
points somewhere else entirely, and `probe_script_sha256` alone would never catch it.
`deployment_config_fingerprint` closes that gap: it is a SHA-256 over the exact sibling-config
values the probe script actually resolved and used for this run (never the config *file's own*
bytes, which may be absent -- the fingerprint covers the already-defaulted/resolved path
values), self-reported by the probe in every report it emits and compared against this exact
grant's own signed value the same way `probe_script_sha256` already is. Like that field, it is
one of the fields the Human Authority's signature itself covers -- and, like that field (see
the corrected claim just above), this is a consistency check between the probe's own
self-report and the grant's own signed expectation, never an independent cryptographic
attestation of what configuration genuinely produced the report.

**Authorization is checked before any read, not only reported as a mismatch afterward (PR #108
Structural Review Round 4, SR4-F4; corrected by Round 5, SR5-F2).** The paragraph above
describes what the *grant/adapter* side compares a report against, after the fact. The probe
script itself also checks, for `SOURCE_LOG_EXCERPT_BOUNDED`, whether its own currently-effective
configuration is authorized *before* it ever opens `SOURCE_EXCERPT_PATH`/`LOG_EXCERPT_PATH` at
all. Round 4's own version of this check compared against a local sibling file
(`runtime_observation_probe.approved_config.json`) -- but that file was only ever compared
against the script's *own* locally-resolved configuration, with no connection to what a real
caller's live, currently-verified grant actually authorizes; a party with only filesystem access
to the target could keep a swapped sibling config and its own "approval" mutually consistent,
with no grant involved at all. Round 5 removes that local file entirely: the probe script's
second positional CLI argument, `expected_deployment_config_fingerprint`, is now the live
binding -- a value that can only ever reach the script by riding along on the one, specific,
already-grant-verified SSH command `network.render_ssh_command_argv` renders for this exact
attempt (see §3). A missing or malformed argument is refused as `MALFORMED`; a well-shaped one
that does not equal the script's own computed `deployment_config_fingerprint` is refused as
`CONFIG_NOT_AUTHORIZED` -- both before any read. This is still a defense independent of, and
complementary to, the grant/adapter comparison above: this one refuses an unauthorized read on
the target itself, using a value that arrived fresh on this exact invocation, never a static
file sitting there in advance.

**A grant's own window must contain a Boundary's, never merely resemble it (PR #108 Structural
Review Round 3, SR3-F2).** `SshRuntimeAdapter` additionally re-verifies the grant, live, at the
moment of its own observation attempt (not only once, at construction) -- and that live
re-verification now also checks that the Boundary's own declared `time_window` (`issued_at`/
`expires_at`) sits entirely inside the grant's own signed `issued_at`/`expires_at`, not merely
that both independently pass their own `now`-vs-`expires_at` check. Without this, a Boundary
could declare its own, arbitrarily backdated or widened window with no connection to what the
grant's signature actually authorized. The live `now` this re-verification reads comes from
exactly one, narrowly injectable source
(`manosube_agent_civilization.runtime.engine.current_utc_instant`, overridable only through
`SshRuntimeAdapter`'s own constructor, the one deliberate exception to this package's otherwise
universal "no function reads a clock of its own" rule) -- never from a caller-suppliable `now`
string that could itself be backdated.

**The live instant is also checked against the Boundary's own window directly (PR #108
Structural Review Round 4, SR4-F2).** The paragraph above closed the gap between the grant's
own window and the Boundary's *declared* one, but left one further gap open: a grant valid for
a wide window (a full year) that structurally contains a much narrower Boundary window (one
day) still passed both checks at a live instant that fell inside the grant's own window but far
outside the Boundary's. `transport_control.require_boundary_within_live_window` is the missing
third check, requiring the live instant to fall inside the Boundary's own window directly, not
merely inside whatever broader window the grant happens to authorize.

**Where a grant lives.** This delivery introduces no grant store, no schema file under
`01_SCHEMA/`, and no Store record kind. A grant is an ordinary JSON file an operator keeps
(or a GitHub Actions `workflow_dispatch` input, as `grant_json` on the shipped
`.github/workflows/runtime_observation.yml` workflow) -- independent of the canonical Store on
purpose, exactly as `transport_control.py`'s own module docstring states ("this module creates
no second Runtime, Authority, Evidence, State, or Reflow owner"). Where it is kept, how many
copies exist, and who may edit the file are operational decisions for whoever deploys this,
not something this package tracks.

**Expiry and revocation.** A grant's own `expires_at` is the only revocation mechanism this
delivery ships: once `now` passes `expires_at`, every function in `transport_control.py`
refuses it, with zero exceptions and zero grace period. There is no separate revoke call,
because there is nothing stateful to revoke -- the grant is re-validated, fully, on every use.
To revoke a grant *before* its own `expires_at`, stop distributing/using that file; a grant
whose JSON no caller still holds authorizes nothing, because nothing ever looks it up by
`grant_id` alone. If a grant was already shared more broadly than intended, the only clean fix
is to treat it as compromised and have SHUKOU ratify a replacement with a different
`grant_id` and a window that starts now -- the old one still technically validates until its
own `expires_at`, so narrow that window deliberately when ratifying, not as an afterthought.

## 3. Capability A -- manual, step by step

1. Get a ratified grant naming `"MANUAL_SSH"` in `permitted_transports` (§2).
2. Render the command:

   ```bash
   python scripts/runtime_observation_transport.py render-command \
     --grant-file grant.json \
     --now "2026-06-01T00:00:00Z"
   ```

   Output: `{"ok": true, "command": "ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o
   ConnectTimeout=10 -p 22 probe@127.0.0.1 'python3 runtime_observation_probe.py
   OS_HEALTH_SNAPSHOT_BOUNDED <64-hex-char deployment_config_fingerprint>'"}`. The trailing
   hex value is the grant's own signed `deployment_config_fingerprint` (PR #108 Structural
   Review Round 5, SR5-F2) -- the probe script requires it as a second positional argument
   and refuses to read anything if it does not match. The exact same string, field for field,
   is what Capability B would run unattended for the identical grant -- `render_manual_ssh_
   command` and `SshRuntimeAdapter.observe` both build it through the one shared
   `network.render_ssh_command_argv`.
3. A Human operator copies that command, runs it themselves (from their own terminal, or
   pasted into a GitHub Actions step -- the shipped `runtime_observation.yml` workflow does
   exactly step 2 and stops there; it never runs the command itself).
4. The probe script prints one JSON line. Feed it through the real canonical route directly
   (PR #108 Structural Review Round 3, SR3-F3(A) -- this subcommand no longer stops at a
   bare digest check; it now produces a genuine envelope/receipt/Evidence hand-off, the
   identical outcome any other transport reaches):

   ```bash
   python scripts/runtime_observation_transport.py import-output \
     --report-file report.json \
     --grant-file grant.json \
     --target-identity-file target_identity.json \
     --store-root ./store \
     --schema-root 01_SCHEMA \
     --project-id PRJ-EXAMPLE \
     --project-binding-id PROJBIND-EXAMPLE \
     --permitted-fields hostname \
     --now "2026-06-01T00:05:00Z" \
     --captured-at "2026-06-01T00:00:00Z" \
     --captured-exit-code 0
   ```

   `ok: false` here means only that the route itself could not be reached (an invalid grant,
   or a malformed target/Boundary shape) -- a captured report naming the wrong target, an
   unpermitted field, or self-reported counters that lie about what it actually shipped
   instead surfaces as a real, bounded `observation_outcome` (typically `MALFORMED`/
   `IDENTITY_MISMATCH`) on a genuine envelope and receipt, never a forged `ok: true`.

   **Real capture provenance, never a silent default (PR #108 Structural Review Round 4,
   SR4-F3).** `--captured-exit-code` is required -- there is no default standing in for a
   capture the operator never actually attested, so a report left behind by a command that
   genuinely failed can never be classified as though it had succeeded. Pass
   `--captured-stderr-file <path>` if the Human operator also captured the command's own
   stderr. `--captured-at` is the trusted instant the operator attests the capture actually
   happened -- deliberately distinct from `--now` (the instant this import command itself is
   running) -- and becomes the resulting Envelope's own `observed_at`; reusing `--now` for both
   would invent a capture instant from import time, which this round refuses to do.
   `--evidence-request-file <path>` is optional on this subcommand too; see §4 for what it
   does and when to supply it.

Rendering a command never opens a connection. Running it is the Human's own act, over a
connection this package never opens.

## 4. Capability B -- grant-gated unattended, step by step

1. Get a ratified grant naming `"PREAUTHORIZED_UNATTENDED_SSH"` in `permitted_transports`.
2. Decide the transport for this attempt:

   ```bash
   python scripts/runtime_observation_transport.py classify-dispatch \
     --dispatched --runner-allocated
   # {"dispatch_status": "AVAILABLE"}
   ```

   `select_transport` prefers GitHub Actions whenever it reports `AVAILABLE` and no transport
   was explicitly requested -- Actions being unavailable never by itself selects
   `PREAUTHORIZED_UNATTENDED_SSH` through this function; an explicit request is always required
   for that mode here.
3. Run the observation, with an explicit request:

   ```bash
   python scripts/runtime_observation_transport.py observe \
     --grant-file grant.json \
     --target-identity-file target_identity.json \
     --store-root ./store \
     --schema-root 01_SCHEMA \
     --project-id PRJ-EXAMPLE \
     --project-binding-id PROJBIND-EXAMPLE \
     --permitted-fields hostname,uptime_seconds \
     --now "2026-06-01T00:00:00Z" \
     --actions-status UNAVAILABLE \
     --requested-transport PREAUTHORIZED_UNATTENDED_SSH
   ```

   This refuses, with zero SSH process ever spawned, unless the grant is valid, current, and
   actually names `PREAUTHORIZED_UNATTENDED_SSH` -- there is no path through this command that
   skips `transport_control.select_transport`. `GITHUB_ACTIONS` executes through this identical
   command too (PR #108 Structural Review Round 2, SR2-F1) -- the CLI no longer refuses every
   transport except the unattended one; only `MANUAL_SSH` is still never executed by this
   subcommand, since that mode's whole authorization act is a Human running the rendered
   command themselves.

**Automatic unattended fallback (SR2-F1), an explicit opt-in.** A caller that does not want to
make a per-attempt Human selection may instead pass `--allow-automatic-fallback`, with no
`--requested-transport` at all:

```bash
python scripts/runtime_observation_transport.py observe \
  --grant-file grant.json \
  --target-identity-file target_identity.json \
  --store-root ./store \
  --schema-root 01_SCHEMA \
  --project-id PRJ-EXAMPLE \
  --project-binding-id PROJBIND-EXAMPLE \
  --permitted-fields hostname,uptime_seconds \
  --now "2026-06-01T00:00:00Z" \
  --actions-status UNAVAILABLE \
  --allow-automatic-fallback
```

This resolves to `PREAUTHORIZED_UNATTENDED_SSH` automatically only once `--actions-status` is
exactly `UNAVAILABLE` (never the ambiguous `UNKNOWN`) and the grant already, explicitly permits
that transport -- the authority already fully pre-exists in the signed grant; this flag only
automates the mechanical trigger, never the authorization itself
(`select_transport`'s own existing, unchanged behavior is untouched; this is a separate,
narrowly scoped function, `select_transport_with_automatic_fallback`). Pass
`--attempt-already-satisfied` on a retry of an attempt a caller's own bounded, local
record already knows reached a transport, to refuse a second, duplicate unattended execution;
this package keeps no attempt ledger of its own, so that correlation is the caller's own
responsibility (`compute_runtime_observation_attempt_id`, surfaced in every `observe` output as
`attempt_id`, is the pure, deterministic identity a caller correlates against).

`observe` also takes an optional `--evidence-request-file <path>`; see the `run-controller`
section below for what it does.

**A genuinely independent fallback controller, not just a caller-driven selector (PR #108
Structural Review Round 3, SR3-F1; the deadline itself corrected by Round 4, SR4-F1).**
`observe --allow-automatic-fallback` above still only ever accepts a single, already-decided
`--actions-status` string -- it never itself waits or polls. `run-controller` is the
qualitatively different primitive the reviewer asked for: it owns its own bounded polling loop
over a sequence of observed dispatch facts, deciding for itself when a **real elapsed-time**
deadline has been reached, never merely when an iteration count runs out:

```bash
python scripts/runtime_observation_transport.py run-controller \
  --grant-file grant.json \
  --target-identity-file target_identity.json \
  --store-root ./store \
  --schema-root 01_SCHEMA \
  --project-id PRJ-EXAMPLE \
  --project-binding-id PROJBIND-EXAMPLE \
  --permitted-fields hostname,uptime_seconds \
  --now "2026-06-01T00:00:00Z" \
  --fixture-dispatch-status-sequence UNKNOWN,UNKNOWN,UNAVAILABLE \
  --start-deadline-seconds 30 \
  --max-polls 5 \
  --request-id REQ-2026-06-01-0001 \
  --claim-state-file ./claim-state.json
```

`--fixture-dispatch-status-sequence` (renamed from `--dispatch-status-sequence` by PR #108
Structural Review Round 5, SR5-F1, to make its synthetic nature explicit) is a comma-separated,
pre-known sequence of observed dispatch facts polled in order (the controller's own loop
repeats the final entry once the sequence is exhausted, rather than requiring a caller to pad
it out to `--max-polls` entries) -- an explicit FIXTURE input, never a live GitHub Actions poll.
It is mutually exclusive with, and exactly one is required against, `--dispatch-status-file
<path>`: the declared NORMAL (non-fixture) entry point this subcommand actually runs under in
practice, where an external, already-authorized process writes
`{"dispatch_status": "...", "observed_at": "..."}` to a local JSON file, which this subcommand
reads fresh on every poll, refusing a stale read (`--dispatch-status-max-staleness-seconds`,
default `30.0`, compared against `--now`) as the honest `UNKNOWN` this controller already knows
how to handle. Either source is wrapped in a genuinely bounded acquisition primitive (see
below) before being handed to the controller.

**`--start-deadline-seconds` is a real wall-clock budget (PR #108 Structural Review Round 4,
SR4-F1; corrected by Round 5, SR5-F1).** Checked via `time.monotonic` before every poll, this
is what actually bounds how long the controller waits -- `--max-polls` alone never did: an
instantly-answering provider (the fixture sequence above included) could otherwise exhaust
every poll, and therefore decide "deadline exceeded", in microseconds. Once elapsed time
already meets or exceeds this bound, no further poll is made. Round 4's own version of this
check ran only *before* each poll, never *after* the loop stopped the other way it can stop --
`--max-polls` simply being exhausted while the dispatch status was still ambiguously `UNKNOWN`
-- so an instantly-answering provider could still reach `FALLBACK_AUTHORIZED` after only
microseconds of real elapsed time against a far larger declared deadline. Round 5 corrects
this: an `UNKNOWN` reached purely because the poll budget ran out, with real time still
remaining, now returns a new, distinct decision, `DEADLINE_NOT_YET_REACHED` -- zero grant
checks, zero SSH, on that decision alone. Separately, a provider call that itself ignores the
`remaining_seconds` budget it is handed (sleeping longer, blocking on slow I/O) can no longer
hold the whole controller hostage either: `adapter.bounded_dispatch_status_acquisition` runs
the raw call in a background daemon thread and returns `"UNKNOWN"` the instant its own join
times out, rather than waiting for a stalled call to finish.

The decision is one of `ACTIONS_AVAILABLE_DEFER` / `FALLBACK_AUTHORIZED` /
`FALLBACK_REFUSED_NO_GRANT` / `ALREADY_SATISFIED` / `DEADLINE_NOT_YET_REACHED`; the SSH adapter
is only ever constructed, and only ever executes, on `FALLBACK_AUTHORIZED` -- every other
decision returns with zero target calls. The output also reports `final_dispatch_status`/
`poll_count`/`elapsed_seconds`, so a caller can honestly tell a confirmed `UNAVAILABLE`
fallback apart from a deadline-exceeded-while-still-`UNKNOWN` one, even though both reach the
identical decision.

**`--request-id` and `--claim-state-file` (PR #108 Structural Review Round 4, SR4-F1).** A
stable `operation_id` -- derived from the grant, the target's own stable provider/deployment/
instance coordinates, *and* `--request-id` -- is computed once and reused whether this call
defers to Actions or falls back to SSH, so an Actions attempt and any later SSH fallback for
the identical *request* can be correlated even though they are two separate invocations.
`--request-id` is what makes that identity specific to *this one logical observation request*:
reusing one grant/target combination for two genuinely separate requests without varying
`--request-id` would collide them onto one operation id, exactly the gap this round closes.
`--claim-state-file` points at a local JSON file this subcommand genuinely loads, consults, and
-- only after a real `FALLBACK_AUTHORIZED` execution -- updates and saves back, persisting
`RuntimeObservationClaimState` across separate invocations and refusing a second, duplicate
execution of the identical operation. Omit it (or pass none) and every invocation starts from
an empty claim state, exactly as before this round.

**`--evidence-request-file` and the real Evidence hand-off (PR #108 Structural Review Round 4,
SR4-F3).** Every subcommand that reaches a real receipt (`observe`, `run-controller`,
`import-output`) accepts this optional flag and includes an `evidence_handoff` field in its
own JSON output either way. Omit it, and `evidence_handoff` honestly reports
`{"status": "NOT_REQUESTED"}` -- this package never fabricates an Evidence hand-off that did
not happen. Pass it, and the real
`manosube_agent_civilization.runtime.evidence_handoff.route_runtime_observation_to_evidence` is
invoked against the file's own content (a complete, Change-Free Verification Evidence request
grounded in a real `observation_request`/`difference_request`/`verification_observation_
request` your own project already has a route to produce -- this delivery invents no such
route, since doing so would mean minting a new Observation/Difference authority chain from
nothing). A successful hand-off reports `{"status": "HANDED_OFF", "evidence_id": ...,
"evidence_position": ...}`; a request this route itself refuses (a project mismatch, a missing
prerequisite, a malformed shape) reports `{"status": "REFUSED", "reason": "..."}` -- the
precise bounded status, never a crash and never a silently assumed success.

This delivery does not wire capability B into any scheduler, cron, or always-on controller; it
ships the gate and the CLI that exercises it, so a downstream project can invoke it from
whatever unattended controller it already has, under its own separate decision to actually run
one continuously.

## 5. Deploying the probe script to a real target

`scripts/runtime_observation_probe.py` is the one file that needs to exist on a target at all --
copy it there, read-only, and run it once by hand to confirm `python3
runtime_observation_probe.py OS_HEALTH_SNAPSHOT_BOUNDED 0000000000000000000000000000000000000000000000000000000000000000`
(any 64-hex-character value; `OS_HEALTH_SNAPSHOT_BOUNDED` never compares it to anything) prints
a JSON line. It takes no installation step (stdlib only, Python 3.8+), reads no argument beyond
the one closed `probe_identity` positional and (PR #108 Structural Review Round 5, SR5-F2) the
required second `expected_deployment_config_fingerprint` positional, and never writes anything.

**Per-target path configuration is a sibling file, never an edit to this reviewed script
(PR #108 Structural Review Round 2, SR2-F4).** For `SOURCE_LOG_EXCERPT_BOUNDED`, place a
`runtime_observation_probe.config.json` file next to the deployed script (same directory,
resolved only relative to the script's own real location -- never a caller-supplied path):

```json
{
  "source_excerpt_path": "/opt/widget-service/source_excerpt.txt",
  "log_excerpt_path": "/var/log/widget-service/observed.log"
}
```

Either key, or the whole file, may be omitted -- an omitted key or an absent/unreadable/
malformed file falls back to this script's own shipped default for that path.

**The probe now self-reports a `deployment_config_fingerprint` over these resolved paths
(PR #108 Structural Review Round 3, SR3-F4).** Every report the probe emits includes a
SHA-256 fingerprint computed over the exact, already-resolved `source_excerpt_path`/
`log_excerpt_path` values this run actually used (defaults included, whether or not a sibling
config file was present) -- a byte-identical probe script deployed against two different
targets with two different sibling configs reports two different fingerprints, even though
`probe_script_sha256` is identical for both. `import-output`/`observe`/`run-controller` all
compare this self-reported value against the exact grant's own signed
`deployment_config_fingerprint` field (§2) -- a grant issued for one target's own paths is
refused outright against a different target's sibling config, never silently accepted because
the script digest alone still matched.

**The caller's own live grant commitment authorizes the configuration before any excerpt path
is ever read (PR #108 Structural Review Round 4, SR4-F4; corrected by Round 5, SR5-F2).** The
paragraph above describes what happens *after* a report already exists -- the grant/adapter
side compares the self-reported fingerprint against its own signed expectation. That is not
the only gate: for `SOURCE_LOG_EXCERPT_BOUNDED`, the probe script requires a **second,
required positional CLI argument**, `expected_deployment_config_fingerprint`, and refuses to
open `SOURCE_EXCERPT_PATH`/`LOG_EXCERPT_PATH` at all unless it equals the probe's own computed
`deployment_config_fingerprint`:

```bash
python3 runtime_observation_probe.py SOURCE_LOG_EXCERPT_BOUNDED <64-hex-char fingerprint>
```

Round 4's own version of this check (`runtime_observation_probe.approved_config.json`, a third
sibling file) is **removed** -- it only ever compared against the script's own locally-resolved
configuration, with no connection to a real caller's live, currently-verified grant. A party
with mere filesystem access to the target could keep that file and the path configuration
mutually consistent, with no grant involved at all. Round 5 replaces it with a value that can
only ever reach the script by riding along on the one, specific, already-grant-verified SSH
command `network.render_ssh_command_argv` renders for this exact attempt (§2/§3) -- a caller
never deploys this value to the target in advance; it arrives fresh on every single invocation.
A missing second argument, or one of the wrong shape (not exactly 64 lowercase hex characters),
is refused as `{"ok": false, "reason": "MALFORMED", ...}` before any configuration check is
even reached; a correctly-shaped value that simply does not match this deployment's own
computed fingerprint is refused as `{"ok": false, "reason": "CONFIG_NOT_AUTHORIZED", ...}` --
both before any read of either excerpt path. No sibling *approval* file of any kind is deployed
or read for this purpose any longer; `runtime_observation_probe.config.json` (the unrelated
*path*-configuration file) is unaffected.

**Do not edit
`SOURCE_EXCERPT_PATH`/`LOG_EXCERPT_PATH` directly in the script file itself** -- editing the
reviewed script changes its own SHA-256 content digest, which breaks the exact digest pin a
grant's own signed `probe_script_sha256` field is supposed to bind to a specific, reviewed
artifact (the earlier version of this guide instructed exactly that edit; it is withdrawn,
because it directly contradicted the very digest pin this delivery relies on). If this
repository's own probe script is ever genuinely revised, its new digest must be recomputed
(`manosube_agent_civilization.runtime.types.SSH_PROBE_SCRIPT_SHA256`) and a new grant issued
naming it -- never silently carried forward from an old approval.

## 6. What this delivery has, and has not, proven against a real target

- Every HTTP-transport claim in this repository's own tests runs against a real, disposable,
  local HTTP server (unchanged from Issue #64).
- Every SSH-transport test in this delivery's own suite runs the real
  `observe_runtime_target`/`SshRuntimeAdapter` pipeline with `subprocess.run` mocked to return
  exactly the JSON line the real probe script emits -- proving this package's own handling of
  that exact contract, never a real network/SSH round trip.
- No `ssh`/`sshd`/`ssh-keygen` binary exists in this delivery's own build/test environment, and
  installing one was out of scope for this delivery (a machine/service modification the
  adoption and handoff both explicitly prohibit). **The real local-SSH-fixture vertical proof,
  and the real unattended-dispatch-against-a-real-target proof, are both pending** -- not
  claimed by this delivery, and tracked for a future, separately authorized step once a real
  disposable SSH target (or a sandbox that can install `openssh-server`) is available.
- No production SSH connection, no credential, and no key of any kind was created, requested,
  or used anywhere in this delivery.

**PR #108 Structural Review Round 2 adds one further disclosed gap.** Neither
`scripts/runtime_observation_transport.py` (the CLI) nor `scripts/runtime_observation_probe.py`
(the probe) is part of the installed `manosube_agent_civilization` package, and this round's own
permitted-file inventory authorizes no new test file for either (`ADDITIONAL_PATH_AUTHORIZATION_
BY_THIS_RECORD=false`). This round's CLI-level corrections (real `GITHUB_ACTIONS`/automatic-
fallback execution, `import-output`'s own bound and grant-bound digest check) and the probe
script's own corrections (ancestor-symlink-safe paths, sibling configuration loading) were
verified by direct manual invocation against a real, Boot-bound fixture world during this
round's own correction work -- not by a permanent automated test, which a future round with
authorization to add one should supply. The security-critical logic both scripts call
(`transport_control.py`, `adapter.py`) is fully covered by this delivery's own automated suite
either way -- the scripts themselves are documented as "thin CLI wrappers" around exactly that
logic, and remain so.

**PR #108 Structural Review Round 3 narrows that gap for three of its four findings, and
leaves it exactly where Round 2 left it for the fourth.** SR3-F1 (the independent fallback
controller), SR3-F2 (the trusted-clock live reverification and Boundary⊆Grant window binding),
and SR3-F3(A) (`import-output` routed through the real canonical route) all live entirely in
the installed package (`transport_control.py`, `adapter.py`, `engine.py`) and are each covered
by new, permanent automated tests in this round's own authorized test files -- not by manual
invocation alone. SR3-F3(B) (the probe script's descriptor-relative, no-follow path walk) and
SR3-F4 (the probe script's `deployment_config_fingerprint` self-report) are both still
corrections to `scripts/runtime_observation_probe.py` itself, outside the installed package,
and this round's own permitted-file inventory again authorizes no new path for a script-level
test file -- so, exactly as Round 2 disclosed for that same script, both were verified by
direct manual invocation against a real, Boot-bound fixture world during this round's own
correction work, never by a permanent automated test. The one narrowing this round does add:
the handoff clarifies that an *existing*, already-authorized runtime test file may import or
subprocess-execute the scripts themselves against neutral fixtures without that counting as a
new test file path -- a future round that chooses to exercise that allowance would close this
disclosed gap for good; this round's own corrections did not need it and did not add it.

**PR #108 Structural Review Round 4 closes that remaining disclosed gap.** Both scripts are
now genuinely exercised by permanent, automated tests in this delivery's own existing
authorized test files (`tests/integration/runtime/test_runtime_unattended_ssh.py`) -- never a
new test file path, exactly as the Round 3 handoff's own clarification permits.
`scripts/runtime_observation_probe.py` is copied into an isolated directory and run as a real
subprocess, covering: a genuinely authorized configuration reading real files; refusal before
any read when the approval file is absent, malformed, or names the wrong fingerprint (the
absent/malformed/mismatched cases are all distinguished from "tried and failed" by asserting
the refusal reason is `CONFIG_NOT_AUTHORIZED`, never `NOT_FOUND`); a decisive proof that the
refusal genuinely precedes any read attempt, using a named pipe nothing ever writes to as the
configured source path -- a script that attempted the read first would hang forever on it, and
the test's own bounded timeout would catch that; and the SR3-F3(B) ancestor-symlink refusal,
preserved as a permanent regression now that this file genuinely exercises the real script.
`scripts/runtime_observation_transport.py` is likewise exercised as a real CLI subprocess
(`import-output`, `run-controller`) against a real, Boot-bound on-disk Store, proving the
captured-provenance/redaction/claim-persistence wiring this section documents is genuinely
reachable through the shipped command line, not only through the library functions it calls.
