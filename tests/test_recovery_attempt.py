import pytest

from agent.recovery_attempt import (
    DEFAULT_MAX_RECOVERY_ATTEMPTS,
    RecoveryAttemptPolicy,
)


def test_default_max_attempts():

    assert DEFAULT_MAX_RECOVERY_ATTEMPTS == 1


def test_first_recovery_is_allowed():

    policy = RecoveryAttemptPolicy()

    result = policy.can_recover(
        0,
    )

    assert result.should_recover is True

    assert result.attempt_count == 0

    assert result.max_attempts == 1


def test_recovery_limit_reached():

    policy = RecoveryAttemptPolicy()

    result = policy.can_recover(
        1,
    )

    assert result.should_recover is False

    assert result.attempt_count == 1

    assert result.max_attempts == 1


def test_custom_recovery_limit():

    policy = RecoveryAttemptPolicy(
        max_attempts=3,
    )

    assert (
        policy.can_recover(
            0,
        ).should_recover
        is True
    )

    assert (
        policy.can_recover(
            1,
        ).should_recover
        is True
    )

    assert (
        policy.can_recover(
            2,
        ).should_recover
        is True
    )

    assert (
        policy.can_recover(
            3,
        ).should_recover
        is False
    )


def test_negative_attempt_count():

    policy = RecoveryAttemptPolicy()

    result = policy.can_recover(
        -1,
    )

    assert result.should_recover is False


def test_invalid_attempt_count():

    policy = RecoveryAttemptPolicy()

    result = policy.can_recover(
        "0",
    )

    assert result.should_recover is False


def test_invalid_max_attempts():

    with pytest.raises(ValueError):

        RecoveryAttemptPolicy(
            max_attempts=-1,
        )


def test_boolean_max_attempts_is_invalid():

    with pytest.raises(ValueError):

        RecoveryAttemptPolicy(
            max_attempts=True,
        )


def test_decision_to_dict():

    policy = RecoveryAttemptPolicy()

    result = policy.can_recover(
        0,
    )

    data = result.to_dict()

    assert data["should_recover"] is True

    assert data["attempt_count"] == 0

    assert data["max_attempts"] == 1

    assert "reason" in data
