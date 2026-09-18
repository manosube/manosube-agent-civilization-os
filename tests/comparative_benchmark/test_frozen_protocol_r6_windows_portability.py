"""P90-R6-WINDOWS-F1 (PR #90, `ADOPT_P90_R6_WINDOWS_PORTABILITY_FIX`, comment 5723625948):
decisive proof that the Windows-facing reproduction/signing entrypoint
(`scripts.generate_and_sign_frozen_protocol_r6_independent_reproduction_submission`) never
imports `fcntl` or the unrelated `store`/`boot`/`binding`/`work_time_transparency` surfaces this
package's own file-backed Store/Boot/Binding/Work-Time-Transparency machinery pulls in -- the
exact defect SHUKOU's real Windows PowerShell run discovered: `fcntl` is POSIX-only, and
`work_time_transparency/__init__.py`'s own eager imports (`.adapters` -> ... ->
`store.file_store` -> `import fcntl`) broke this script before the passphrase prompt was ever
reached, before the PEM was opened, before signing, and before any submission JSON was emitted.

Runs the complete reproduce -> sign -> locally-verify -> emit path in a genuinely fresh child
Python process (never merely asserting an import succeeded in-process, where a module already
imported by an earlier test would mask the defect) with a `sys.meta_path` finder installed
*before* any repository import that refuses `fcntl` and every `manosube_agent_civilization.
{store,boot,binding,work_time_transparency}` import with the identical `ModuleNotFoundError`
SHUKOU's own Windows run raised -- the closest a POSIX CI process can come to proving the same
fact SHUKOU's real Windows machine already proved false before this fix, and true after it."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Installed as the very first statement of the child process -- before any repository or
#: third-party import -- so it is in force for the complete import graph this test exercises.
_BLOCKER_PREAMBLE = textwrap.dedent(
    """
    import sys
    import importlib.abc

    _BLOCKED_EXACT = {"fcntl"}
    _BLOCKED_PREFIXES = (
        "manosube_agent_civilization.store",
        "manosube_agent_civilization.boot",
        "manosube_agent_civilization.binding",
        "manosube_agent_civilization.work_time_transparency",
    )

    class _Blocker(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if name in _BLOCKED_EXACT or name.startswith(_BLOCKED_PREFIXES):
                raise ModuleNotFoundError(f"No module named {name!r}")
            return None

    sys.meta_path.insert(0, _Blocker())
    """
)


def test_the_generator_module_imports_cleanly_with_fcntl_and_wtt_route_surfaces_blocked() -> None:
    child_script = _BLOCKER_PREAMBLE + textwrap.dedent(
        f"""
        sys.path.insert(0, {str(REPO_ROOT)!r})
        import scripts.generate_and_sign_frozen_protocol_r6_independent_reproduction_submission as gen
        import tests.comparative_benchmark.frozen_protocol_reproduction as repro

        events = repro.reproduce_raw_events()
        assert len(events) == 4
        print("IMPORT_AND_REPRODUCE_OK")
        """
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", child_script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "IMPORT_AND_REPRODUCE_OK" in result.stdout
    assert "fcntl" not in result.stderr


def test_the_full_reproduce_sign_locally_verify_emit_path_completes_with_those_imports_blocked(
    tmp_path: Path,
) -> None:
    """The complete round trip -- against a disposable test key, never SHUKOU's own -- proves
    this script can do everything a real Windows run needs (reach the passphrase prompt, open
    the PEM, sign, locally verify, emit) while every import SHUKOU's real Windows machine could
    not provide is fail-closed for the whole duration of the child process."""

    pem_dir = tmp_path / "pem"
    pem_dir.mkdir()
    out_path = tmp_path / "submission.json"

    child_script = _BLOCKER_PREAMBLE + textwrap.dedent(
        f"""
        sys.path.insert(0, {str(REPO_ROOT)!r})
        import getpass
        import json
        from pathlib import Path

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            BestAvailableEncryption, Encoding, PrivateFormat, PublicFormat,
        )

        import scripts.generate_and_sign_frozen_protocol_r6_independent_reproduction_submission as gen

        private_key = Ed25519PrivateKey.generate()
        public_key_hex = private_key.public_key().public_bytes(
            encoding=Encoding.Raw, format=PublicFormat.Raw
        ).hex()
        passphrase = "disposable-clean-process-test-passphrase"  # noqa: S105

        pem_path = Path({str(pem_dir)!r}) / "disposable_test_key.pem"
        pem_path.write_bytes(
            private_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.PKCS8,
                encryption_algorithm=BestAvailableEncryption(passphrase.encode("utf-8")),
            )
        )

        gen.REGISTERED_ED25519_PUBLIC_KEY_HEX = public_key_hex
        getpass.getpass = lambda *a, **k: passphrase

        exit_code = gen.main(["--pem-path", str(pem_path), "--output", {str(out_path)!r}])
        assert exit_code == 0

        submission = json.loads(Path({str(out_path)!r}).read_text())
        assert submission["signature"]["public_key"] == public_key_hex
        assert submission["agreement"] in {{"MATCH", "DIVERGENT", "INCOMPARABLE"}}
        assert passphrase not in json.dumps(submission)
        print("FULL_ROUND_TRIP_OK")
        """
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", child_script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "FULL_ROUND_TRIP_OK" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
    assert out_path.exists()
    assert "disposable-clean-process-test-passphrase" not in out_path.read_text()


def test_the_generator_and_reproduction_modules_never_import_the_blocked_surfaces() -> None:
    """A cheap, complementary static proof (never a substitute for the two dynamic tests
    above): neither module's own source text *imports* `fcntl` or `work_time_transparency`
    at all -- the fix removed the dependency, it did not merely defer or hide the import.
    Docstring/comment prose that documents why the dependency was removed (e.g. explaining
    `work_time_transparency.clock.default_clock`'s replacement) is expected and is not an
    import, so this checks each source line's own `import`/`from ... import` statements
    rather than banning the bare word from the whole file."""

    generator_source = (
        REPO_ROOT
        / "scripts"
        / "generate_and_sign_frozen_protocol_r6_independent_reproduction_submission.py"
    ).read_text(encoding="utf-8")
    reproduction_source = (
        REPO_ROOT / "tests" / "comparative_benchmark" / "frozen_protocol_reproduction.py"
    ).read_text(encoding="utf-8")

    for source in (generator_source, reproduction_source):
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert "fcntl" not in stripped
                assert "work_time_transparency" not in stripped
