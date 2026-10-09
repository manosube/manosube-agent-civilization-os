# MANOSUBE Agent Civilization OS

MANOSUBE is a state-centered kernel for software development with replaceable AI
executors. It connects objectives, state, observations, unresolved differences,
authorization, changes, evidence, and reflow into one recorded cycle.

The practical question is whether another executor can continue work while preserving
what may be changed, which version was evaluated, why completion was accepted, and
which differences remain unresolved. This repository implements contracts and Python
routes for that question. It is a research implementation whose comparative benefit
still needs independent measurement.

## Try it

Use Linux/POSIX and Python 3.12 or later. Clone this repository, create a virtual
environment, and install it with `python -m pip install -e .`. Follow the
[minimal cycle guide](examples/01_minimal_kernel_cycle/README.md) to initialize a
disposable Store, restore it with `manosube boot`, and commit a controlled cycle.
The fixture key and explicit evidence inputs are public demonstration data; provide
your own authorization and evidence for actual projects.

There are two commands: `manosube init` delegates genesis to the Binding owner;
`manosube boot` restores an already bound project without writing its Store.
FileStateStore uses POSIX locks and directory synchronization and explicitly refuses
unsupported platforms. The controlled filesystem adapter also requires POSIX
descriptor-relative operations. Windows users need a functioning Linux environment.

## Evaluate the claims

The [Japanese design report](docs/research/MANOSUBE_governance_continuity_ja.md) and
[English companion](docs/research/EXTERNAL_EVALUATION_EN.md) describe implementation
boundaries and existing public evidence. Current comparison evidence contains two
deterministic tasks with success in both conditions. It does not establish a causal
advantage over another agent framework or direct model use.

An [English manuscript translation draft](docs/research/MANOSUBE_governance_continuity_en.md)
also covers the Japanese edition's sections and appendices and awaits author review.

The [real-agent protocol](examples/false_completion/PROTOCOL.md) proposes matched
conditions, independent completion oracles, false-accept and false-reject measures,
task-level analysis, and actual cost reporting. The separate closure-control script
tests planted input defects; it is not an agent benchmark. The
[readiness record](docs/EXTERNAL_READINESS.md) lists remaining work explicitly.

## Contribute or support evaluation

[CONTRIBUTING.md](CONTRIBUTING.md) explains setup, validation, issue reporting and the
project's authority boundaries. Reproduction reports should record the exact commit,
environment, commands and outputs. Read [SECURITY.md](SECURITY.md) for vulnerability
reporting. [Sponsorship information](docs/SPONSORSHIP.md) describes concrete deliverables
for independent reproduction, comparative evidence, and evaluator onboarding.

The project is Apache-2.0 licensed; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
Use [CITATION.cff](CITATION.cff) for citation metadata. No compliance certification,
production security guarantee, sponsor outcome or general reliability improvement is
claimed by these documents.
