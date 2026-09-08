"""Phase 14 (Issue #62), Structural Review Round 3 (P14-R3-F3): the real V3 GitHub target
configuration contract -- entirely offline, zero network access, zero Store/adapter
dependency.

Every case here proves :func:`load_v3_target_configuration` fails closed (raises
``V3ConfigurationError``) before any network access could ever occur, or returns ``None`` for
the one genuinely safe default (nothing configured at all). No test in this file constructs a
``RealGitHubAdapter`` or touches ``urllib`` -- this module validates a configuration *shape*
only.
"""

from __future__ import annotations

import pytest
from tests.fixtures.v3_target_configuration import (
    ARTIFACT_NAMING_PREFIX_ENV,
    CHANGE_BASE_REF_ENV,
    CHANGE_HEAD_REF_ENV,
    CLEANUP_CONFIRMED_ENV,
    EVIDENCE_HEAD_SHA_ENV,
    NO_MERGE_CONFIRMED_ENV,
    TARGET_REPOSITORY_ENV,
    TOKEN_ENV,
    V3ConfigurationError,
    V3TargetConfiguration,
    load_v3_target_configuration,
)

_VALID_ENV = {
    TARGET_REPOSITORY_ENV: "acme/widget",
    TOKEN_ENV: "test-token-not-a-real-secret",
    CHANGE_HEAD_REF_ENV: "agent/frozen-v3-branch",
    CHANGE_BASE_REF_ENV: "main",
    EVIDENCE_HEAD_SHA_ENV: "0123456789abcdef0123456789abcdef01234567",
    ARTIFACT_NAMING_PREFIX_ENV: "MANOSUBE V3 proof (do not merge)",
    CLEANUP_CONFIRMED_ENV: "true",
    NO_MERGE_CONFIRMED_ENV: "true",
}


def test_fully_unconfigured_environment_returns_none() -> None:
    assert load_v3_target_configuration(env={}) is None


def test_fully_valid_environment_returns_complete_configuration() -> None:
    config = load_v3_target_configuration(env=_VALID_ENV)
    assert config == V3TargetConfiguration(
        owner="acme",
        repo="widget",
        token="test-token-not-a-real-secret",  # noqa: S106
        change_head_ref="agent/frozen-v3-branch",
        change_base_ref="main",
        evidence_head_sha="0123456789abcdef0123456789abcdef01234567",
        artifact_naming_prefix="MANOSUBE V3 proof (do not merge)",
    )
    assert config is not None
    assert config.target_repository == {"host": "github", "owner": "acme", "repo": "widget"}


def test_partially_configured_environment_fails_closed_not_none() -> None:
    """A partial configuration is never silently treated as 'unconfigured' -- exactly one
    variable set must still fail closed with a real error, before any network access."""

    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env={TARGET_REPOSITORY_ENV: "acme/widget"})


@pytest.mark.parametrize("missing_key", list(_VALID_ENV))
def test_any_single_missing_variable_fails_closed(missing_key: str) -> None:
    env = dict(_VALID_ENV)
    del env[missing_key]
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


@pytest.mark.parametrize(
    "bad_value",
    ["widget", "acme/widget/extra", "", "acme/", "/widget", "acme /widget"],
)
def test_malformed_target_repository_fails_closed(bad_value: str) -> None:
    env = {**_VALID_ENV, TARGET_REPOSITORY_ENV: bad_value}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


def test_identical_head_and_base_ref_fails_closed() -> None:
    env = {**_VALID_ENV, CHANGE_BASE_REF_ENV: _VALID_ENV[CHANGE_HEAD_REF_ENV]}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


def test_ref_containing_a_control_character_fails_closed() -> None:
    env = {**_VALID_ENV, CHANGE_HEAD_REF_ENV: "agent/frozen\nbranch"}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


@pytest.mark.parametrize(
    "bad_sha",
    [
        "0" * 39,  # too short
        "0" * 41,  # too long
        "G" * 40,  # not hex
        "0123456789ABCDEF0123456789ABCDEF01234567",  # uppercase hex, never accepted
        "",
    ],
)
def test_malformed_evidence_head_sha_fails_closed(bad_sha: str) -> None:
    env = {**_VALID_ENV, EVIDENCE_HEAD_SHA_ENV: bad_sha}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


def test_grammatically_valid_but_unverifiable_sha_is_accepted_by_this_offline_validator() -> None:
    """A disclosed limitation, not a gap: ``"a" * 40`` is syntactically a real-looking SHA
    (all lowercase hex, exactly 40 characters) -- indistinguishable from a genuine commit SHA
    without a live network call this offline validator deliberately never makes. Confirming
    the commit actually exists on the frozen target is the real ``RealGitHubAdapter`` call's
    own job at execution time, not this configuration contract's."""

    env = {**_VALID_ENV, EVIDENCE_HEAD_SHA_ENV: "a" * 40}
    config = load_v3_target_configuration(env=env)
    assert config is not None
    assert config.evidence_head_sha == "a" * 40


@pytest.mark.parametrize("bad_value", ["True", "TRUE", "yes", "1", "", "false"])
def test_cleanup_confirmed_requires_the_exact_literal(bad_value: str) -> None:
    env = {**_VALID_ENV, CLEANUP_CONFIRMED_ENV: bad_value}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


@pytest.mark.parametrize("bad_value", ["True", "TRUE", "yes", "1", "", "false"])
def test_no_merge_confirmed_requires_the_exact_literal(bad_value: str) -> None:
    env = {**_VALID_ENV, NO_MERGE_CONFIRMED_ENV: bad_value}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


def test_empty_token_fails_closed() -> None:
    env = {**_VALID_ENV, TOKEN_ENV: "   "}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


def test_default_env_source_is_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    """Omitting *env* reads real ``os.environ`` -- proving the production call path (no
    explicit ``env=`` argument) genuinely reaches the same validation, not a separate,
    untested code path."""

    for key, value in _VALID_ENV.items():
        monkeypatch.setenv(key, value)
    config = load_v3_target_configuration()
    assert config is not None
    assert config.owner == "acme"
