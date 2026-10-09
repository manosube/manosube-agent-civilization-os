# Protocol for a preregistered real-agent false-completion comparison

Status: protocol draft. No real-agent results have been measured by this improvement branch. The separate 40-case closure-control script repeats eight deterministic fixture categories; it is a regression measurement, not 40 independent projects and not a Claude-versus-MANOSUBE experiment.

## Question and conditions

Does the complete MANOSUBE route reduce false acceptance of completion, and at what cost, relative to direct Claude Code execution? Use the same pinned model, CLI version, task version, initial workspace and tool capabilities in both conditions. The direct condition must receive the same objective and oracle specification and its normal verification tools; do not deliberately deprive it of checks. The MANOSUBE condition must traverse the real Authority/Change/Evidence/Reflow route. A stand-in predicate checker must not be labelled MANOSUBE.

Before any model invocation, freeze 40 distinct task instances, independent task oracles, condition prompts, task hashes, model configuration, allowed permissions, timeout and per-run spending ceiling. Run three paired repetitions per task, randomize condition order with a recorded seed, and retain all failures and timeouts. Operator assistance must be recorded and kept comparable. Use author-created tasks or properly licensed external tasks; verify any copied benchmark's license and version.

Task strata: complete controls; unmodified required files; partial edits; stale test receipts; wrong-repository evidence; reverted changes; violated permitted paths; interrupted work. Include both complete and incomplete outcomes in every feasible stratum. Plant faults before freezing the task; do not choose cases after observing which condition fails.

## Independent oracle and metrics

Ground truth is computed from independently checked after-state artifacts and tests, bound to repository/task/head hashes. The operator's acceptance and the model's final claim are distinct fields. A completed kernel gate is not the oracle for its own correctness.

Report false acceptance / truly incomplete runs; true acceptance / truly complete runs; false rejection / truly complete runs; abstention / all evaluable runs; successful task completion; elapsed wall time; actual model cost; active human minutes; and evidence coverage. Preserve UNKNOWN values as null. Never replace missing cost with zero, or include unknown-oracle runs in a success denominator. Report sample counts and confidence intervals, paired differences, task-level variance, and per-stratum outcomes. Repetitions of one task are correlated; confidence intervals must resample tasks, not individual repeats as independent trials.

Retain transcripts, command receipts, task version, before/after hashes, independent oracle evidence, final claim, acceptance decision, runtime/version, assistance, timeouts and measured cost provenance. Scrub credentials and private data before publication. Failed runs are part of the denominator; incomplete transcripts are explicitly identified.

## Run boundary

Actual model execution awaits the operator's chosen Claude Code environment and spending ceiling. The protocol may be revised before execution, but every revision receives a new digest and date. Execution receipts do not retroactively close FD-0005. Any canonical admission remains a separate reviewed operation.

Background sources checked on 2026-10-09: [OverclaimBench](https://arxiv.org/abs/2609.20812), [False Success](https://arxiv.org/abs/2606.09863), [Unreliable Progress Bar](https://arxiv.org/html/2609.08589). These motivate the question; they do not establish a MANOSUBE effect, interchangeable task metrics, or historical priority.
