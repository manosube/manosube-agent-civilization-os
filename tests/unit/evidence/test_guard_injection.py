"""Every structural guard, shown failing on a real violation written into a real package.

A guard that has never reported anything is indistinguishable from a guard that cannot. The
repository has been wrong about exactly this twice -- ``bdf6588`` shipped an assertion whose
f-string could not fail, and ``6b44098`` described an injection control that existed only as
a shell command someone ran once (ADR-0027 §3.5, §3.6). So the controls here are in the
suite, they copy the package to disk, they write the violation into a module the guard
actually reads, and they call **the same functions** the live guards call.

```text
LIVE_ASSERTION_AND_INJECTION_CONTROL_SHARE_ONE_SWEEP=true
```
"""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import pytest
from tests.evidence_guards import (
    clock_read_sites,
    emitted_strings,
    emitted_strings_in,
    module_paths,
)
from tests.evidence_helpers import (
    before_observation_request,
    change_result_evidence_request,
    observation_evidence_request,
    sufficiency_request,
)

from manosube_agent_civilization.evidence import (
    EvidenceError,
    UngroundedChangeResultEvidenceError,
    UnsupportedEvidenceLevelError,
    derive_evidence,
    evaluate_sufficiency,
)

LIVE_PACKAGE = (
    Path(__file__).resolve().parents[3] / "src" / "manosube_agent_civilization" / ("evidence")
)


@pytest.fixture
def package_copy(tmp_path: Path) -> Path:
    """A real copy of the real package, on disk, that a violation can be written into."""

    destination = tmp_path / "evidence"
    shutil.copytree(LIVE_PACKAGE, destination, ignore=shutil.ignore_patterns("__pycache__"))
    return destination


def _inject(package: Path, module: str, source: str) -> None:
    path = package / module
    assert path.is_file(), f"the injection target no longer exists: {module}"
    path.write_text(path.read_text(encoding="utf-8") + source, encoding="utf-8")


# --------------------------------------------------------------------------- #
# the positive control on the controls
# --------------------------------------------------------------------------- #


def test_an_untouched_copy_sweeps_as_clean_as_the_live_package(package_copy: Path) -> None:
    """Without this, an injection failing for any unrelated reason would read as success.

    The module count is compared too: a copy that silently lost files would sweep clean for
    the wrong reason, and every control below would then be measuring an empty directory.
    """

    assert [path.name for path in module_paths(package_copy)] == [
        path.name for path in module_paths(LIVE_PACKAGE)
    ]
    assert clock_read_sites(package_copy) == {}
    assert emitted_strings_in(package_copy) == emitted_strings_in(LIVE_PACKAGE)


# --------------------------------------------------------------------------- #
# the source-level guards
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("engine.py", "\n\ndef _read() -> object:\n    return datetime.now()\n"),
        ("sufficiency.py", "\n\ndef _read() -> object:\n    return datetime.utcnow()\n"),
        ("levels.py", "\n\nimport time\n"),
        ("identity.py", "\n\ndef _read() -> object:\n    return time.monotonic()\n"),
    ],
)
def test_the_clock_guard_reports_an_injected_clock_read(
    package_copy: Path, module: str, source: str
) -> None:
    _inject(package_copy, module, source)
    assert module in clock_read_sites(package_copy)


def test_the_terminal_status_guard_reports_an_injected_closure(package_copy: Path) -> None:
    _inject(package_copy, "engine.py", '\n\nTERMINAL_STATUS = "CLOSED"\n')
    assert "CLOSED" in emitted_strings(package_copy / "engine.py")


def test_the_terminal_status_guard_does_not_report_documentation(package_copy: Path) -> None:
    """The other direction, which is what keeps the guard usable.

    A guard that reported the word wherever it appeared would forbid explaining the
    boundary, and a guard nobody can satisfy gets deleted rather than fixed.
    """

    _inject(
        package_copy,
        "engine.py",
        '\n\ndef _documented() -> None:\n    """Evidence never emits CLOSED."""\n',
    )
    assert "CLOSED" not in emitted_strings(package_copy / "engine.py")


def test_the_independence_guard_reports_an_injected_independence_record(
    package_copy: Path,
) -> None:
    _inject(
        package_copy,
        "sufficiency.py",
        '\n\nINDEPENDENCE_FIELD = "verification_independence_ref"\n',
    )
    emitted: set[str] = set()
    for path in module_paths(package_copy):
        emitted |= emitted_strings(path)
    assert "verification_independence_ref" in emitted


# --------------------------------------------------------------------------- #
# the behavioural guards, each shown refusing a violation it is the only thing refusing
# --------------------------------------------------------------------------- #


def _refuses(request: dict[str, Any], expected: type[Exception]) -> str:
    with pytest.raises(expected) as raised:
        derive_evidence(request)
    return str(raised.value)


def test_the_ungrounded_change_result_guard_is_the_only_thing_refusing_it() -> None:
    """Positive control first: the same request *with* its re-observation succeeds, so the
    refusal below is the guard and not some unrelated defect in the fixture."""

    grounded = change_result_evidence_request()
    assert derive_evidence(grounded)["evidence_position"] == "CHANGE_RESULT_EVIDENCE"

    ungrounded = change_result_evidence_request()
    ungrounded["post_change_observation_request"] = None
    _refuses(ungrounded, UngroundedChangeResultEvidenceError)


def test_the_level_guard_is_the_only_thing_refusing_a_runtime_claim() -> None:
    assert derive_evidence(observation_evidence_request(method_class="INTEGRATION_TEST"))
    _refuses(
        observation_evidence_request(method_class="NATURAL_PATH_EXECUTION"),
        UnsupportedEvidenceLevelError,
    )


def test_the_ceiling_guard_lowers_a_level_that_nothing_backs() -> None:
    """The control is the pair: same method class, different contents, different level."""

    backed = derive_evidence(observation_evidence_request(method_class="UNIT_TEST"))
    assert backed["evidence_level"] == "E2"

    unbacked_request = before_observation_request()
    unbacked_request["attempts"] = []
    unbacked_request["source_occurrences"] = []
    unbacked = derive_evidence(
        observation_evidence_request(
            method_class="UNIT_TEST", observation=unbacked_request, artifact_references=[]
        )
    )
    assert unbacked["evidence_level"] == "E0"


def test_the_re_observation_guard_refuses_the_before_picture_twice_over() -> None:
    assert derive_evidence(change_result_evidence_request())
    _refuses(
        change_result_evidence_request(post_change_observation=before_observation_request()),
        EvidenceError,
    )


def test_the_admitted_instant_guard_refuses_a_record_written_before_its_observation() -> None:
    assert derive_evidence(observation_evidence_request(recorded_at="2026-08-30T09:01:00Z"))
    _refuses(observation_evidence_request(recorded_at="2026-08-30T09:00:59Z"), EvidenceError)


def test_the_artifact_integrity_guard_refuses_a_mutable_locator() -> None:
    clean = observation_evidence_request()
    assert derive_evidence(clean)

    with_locator = observation_evidence_request(
        artifact_references=[
            {
                "kind": "artifact",
                "id": "ARTIFACT-0009",
                "content_sha256": "9" * 64,
                "byte_length": 3,
                "media_type": "text/plain",
                "url": "https://example.test/a",
            }
        ]
    )
    _refuses(with_locator, EvidenceError)


def test_the_policy_address_guard_refuses_a_rewritten_floor() -> None:
    honest = sufficiency_request(minimum_evidence_level="E1")
    assert evaluate_sufficiency(honest)["evidence_sufficiency_result"]["result"] == "SUFFICIENT"

    rewritten = sufficiency_request(minimum_evidence_level="E3")
    rewritten["closure_policy"]["minimum_evidence_level"] = "E0"
    with pytest.raises(EvidenceError):
        evaluate_sufficiency(rewritten)


def test_the_scale_address_guard_refuses_a_reference_to_another_scale() -> None:
    honest = sufficiency_request()
    assert evaluate_sufficiency(honest)

    swapped = sufficiency_request()
    swapped["completion_semantics_ref"]["evidence_level_scale_sha256"] = "0" * 64
    with pytest.raises(EvidenceError):
        evaluate_sufficiency(swapped)
