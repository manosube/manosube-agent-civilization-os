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
    AUTHORIZED_ARTIFACT_COUNT_ENV,
    AUTHORIZED_ARTIFACT_KINDS_ENV,
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
    AUTHORIZED_ARTIFACT_KINDS_ENV: "issue,pull_request,check_run",
    AUTHORIZED_ARTIFACT_COUNT_ENV: "3",
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
        cleanup_confirmed=True,
        no_merge_confirmed=True,
        authorized_artifact_kinds=frozenset({"issue", "pull_request", "check_run"}),
        authorized_artifact_count=3,
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


# ---------------------------------------------------------------------------
# Structural Review Round 4 (P14-R4-F3): the full frozen boundary -- artifact kinds/count
# bound as real fields, and live-write authority as a wholly separate gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    ["", "   ", "not_a_real_kind", "issue,not_a_real_kind", ",,", "issue,issue,bogus"],
)
def test_malformed_authorized_artifact_kinds_fails_closed(bad_value: str) -> None:
    env = {**_VALID_ENV, AUTHORIZED_ARTIFACT_KINDS_ENV: bad_value}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


def test_authorized_artifact_kinds_accepts_a_single_kind() -> None:
    env = {**_VALID_ENV, AUTHORIZED_ARTIFACT_KINDS_ENV: "check_run"}
    config = load_v3_target_configuration(env=env)
    assert config is not None
    assert config.authorized_artifact_kinds == frozenset({"check_run"})


@pytest.mark.parametrize("bad_value", ["0", "-1", "not_a_number", "", "1.5"])
def test_malformed_authorized_artifact_count_fails_closed(bad_value: str) -> None:
    env = {**_VALID_ENV, AUTHORIZED_ARTIFACT_COUNT_ENV: bad_value}
    with pytest.raises(V3ConfigurationError):
        load_v3_target_configuration(env=env)


def test_authorized_artifact_count_accepts_a_positive_integer() -> None:
    env = {**_VALID_ENV, AUTHORIZED_ARTIFACT_COUNT_ENV: "1"}
    config = load_v3_target_configuration(env=env)
    assert config is not None
    assert config.authorized_artifact_count == 1


def test_cleanup_and_no_merge_confirmed_are_bound_fields_not_discarded() -> None:
    """A fully valid configuration carries its own confirmations as real fields (Structural
    Review Round 4, P14-R4-F3) -- a caller can re-verify them, rather than trusting that the
    one-time check at load time happened and was never silently dropped."""

    config = load_v3_target_configuration(env=_VALID_ENV)
    assert config is not None
    assert config.cleanup_confirmed is True
    assert config.no_merge_confirmed is True


# ---------------------------------------------------------------------------
# Structural Review Round 5 (Issue #62, P14-R5-F2): authority bound to the exact
# configuration identity -- changing any one bound field, under an otherwise genuine
# authorization value, refuses.
# ---------------------------------------------------------------------------


def test_configuration_fingerprint_excludes_the_secret_token() -> None:
    """The secret ``token`` must never enter a value a caller compares, logs, or stores as an
    authorization credential."""

    base = load_v3_target_configuration(env=_VALID_ENV)
    assert base is not None
    other_token = load_v3_target_configuration(
        env={**_VALID_ENV, TOKEN_ENV: "a-completely-different-token"}
    )
    assert other_token is not None
    assert base.configuration_fingerprint == other_token.configuration_fingerprint


@pytest.mark.parametrize(
    ("env_key", "changed_value"),
    [
        (TARGET_REPOSITORY_ENV, "acme/a-different-widget"),
        (CHANGE_HEAD_REF_ENV, "agent/a-different-branch"),
        (CHANGE_BASE_REF_ENV, "develop"),
        (EVIDENCE_HEAD_SHA_ENV, "f" * 40),
        (ARTIFACT_NAMING_PREFIX_ENV, "a completely different prefix"),
        (AUTHORIZED_ARTIFACT_KINDS_ENV, "check_run"),
        (AUTHORIZED_ARTIFACT_COUNT_ENV, "1"),
    ],
)
def test_changing_any_one_bound_field_changes_the_configuration_fingerprint(
    env_key: str, changed_value: str
) -> None:
    base = load_v3_target_configuration(env=_VALID_ENV)
    assert base is not None
    changed = load_v3_target_configuration(env={**_VALID_ENV, env_key: changed_value})
    assert changed is not None
    assert base.configuration_fingerprint != changed.configuration_fingerprint


def test_configuration_fingerprint_is_deterministic_and_key_order_insensitive() -> None:
    """The same logical configuration, loaded twice, must recompute the identical fingerprint
    -- this is the value :mod:`tests.fixtures.v3_live_write_authority`'s own signed authority
    record binds itself to, so its own determinism is required, not merely convenient."""

    first = load_v3_target_configuration(env=_VALID_ENV)
    second = load_v3_target_configuration(env=dict(_VALID_ENV))
    assert first is not None
    assert second is not None
    assert first.configuration_fingerprint == second.configuration_fingerprint
