# Round 6 real-Agent task corpus

Defined under PR #90 Round 6 (`ADOPT_P90_R6_REAL_AGENT_ORIGINAL_RUN_AND_FINAL_PROTOCOL`,
comment `5714630885`). Two small, deterministic-content, independently-checkable tasks, each
run once under `MANOSUBE_ABSENT` and once under `MANOSUBE_PRESENT`, by the identical real
agent (this session's own native tool-using agent identity, Claude Sonnet 5 running inside
Claude Code) with an identical tool surface (Bash, Write, Read) and an identical resource
budget (single turn, no retries beyond ordinary tool-call error recovery).

## Task A -- hash computation

Compute the SHA-256 hex digest (lowercase, no trailing newline in the digest value itself) of
the literal ASCII string `MANOSUBE_PHASE21_ROUND6_TASK_A` (no trailing newline in the input),
and write only that digest to the task's output file.

- Independent check: `printf '%s' MANOSUBE_PHASE21_ROUND6_TASK_A | sha256sum`

## Task B -- prime enumeration

List every prime number `p` with `2 <= p <= 50`, ascending, comma-separated, no spaces, and
write only that line to the task's output file.

- Independent check: the unique ascending list is
  `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47`.

## Conditions

- `MANOSUBE_ABSENT`: output written directly to
  `examples/comparative_benchmark/real_agent_corpus/absent/task_{a,b}_output.txt`. No
  Difference is raised, no Authority Decision is obtained, no Observation/Evidence/Reflow
  wraps the write -- the agent acts directly on the task.
- `MANOSUBE_PRESENT`: output written to
  `examples/comparative_benchmark/real_agent_corpus/present/task_{a,b}_output.txt`, wrapped by
  a real Difference -> Authority Decision -> (identical) task execution -> Observation ->
  Evidence -> Reflow lifecycle, as recorded in
  `examples/comparative_benchmark/real_agent_corpus/present/lifecycle_events.md`.

Raw events (what was run, in what order, with what result, including any failures) for both
conditions are recorded in `examples/comparative_benchmark/real_agent_corpus/RAW_EVENTS.md`,
published in full -- not a success-only subset.
