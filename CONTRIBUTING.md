# Contributing and independent reproduction

Start with [the offline quickstart](examples/01_minimal_kernel_cycle/README.md). Linux/Python 3.12 is the currently tested execution target; native Windows persistence is unsupported. The repository's v1 acceptance is scoped and does not establish universal autonomy or a real-world performance advantage.

To report a result, open an issue using the reproduction template or reply to [Issue #100](https://github.com/manosube/manosube-agent-civilization-os/issues/100). Record your version/commit, environment, objective, before/after state, exact commands, expected result, observed result and shareable artifact references. Failure and blocked reproduction reports are welcome. Never post credentials, private keys or unauthorized project data.

For changes, use a branch and pull request. In your virtual environment, install the
verification tools with `python -m pip install -c requirements-ci.txt -e . pytest
pytest-cov hypothesis ruff mypy types-jsonschema build hatchling` (one command).
Run `ruff check src`, `mypy src --platform linux`, `python scripts/validate_schemas.py`,
and the affected tests. Full-suite partitions run in Quality CI; collect all tests before
sharding. Source-impact checks still require the matching architecture/current-state
update for implementation changes. Do not reinterpret historical Human acceptance,
rewrite evidence, or mark unmeasured dimensions complete.

The project has repository-specific development-role policies. An external contribution is a proposed change; maintainers evaluate its scope and provenance before acceptance. CI success supports review and does not grant merge authority. Public example identities and keys are test-only.

Report security problems through [SECURITY.md](SECURITY.md). Discussion participation does not require a maintainer role, model subscription, or sponsorship. Sponsorship supports verification, documentation and external reproduction; it does not purchase acceptance of findings or authority over the kernel.
