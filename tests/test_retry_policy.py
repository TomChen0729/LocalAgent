from agent.failure_classifier import FailureCategory
from agent.retry_policy import (
    DEFAULT_MAX_RETRIES,
    RETRY_LIMITS,
    get_retry_limit,
    should_retry,
)


def test_default_max_retries():

    assert DEFAULT_MAX_RETRIES == 2


def test_not_found_retry_limit():

    assert get_retry_limit(FailureCategory.NOT_FOUND) == 2


def test_permission_denied_retry_limit():

    assert get_retry_limit(FailureCategory.PERMISSION_DENIED) == 0


def test_not_found_should_retry_first_time():

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=0,
    )

    assert decision.should_retry is True
    assert decision.retry_count == 0
    assert decision.max_retries == 2


def test_not_found_should_retry_second_time():

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=1,
    )

    assert decision.should_retry is True
    assert decision.retry_count == 1
    assert decision.max_retries == 2


def test_not_found_should_stop_after_limit():

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=2,
    )

    assert decision.should_retry is False
    assert decision.retry_count == 2
    assert decision.max_retries == 2


def test_permission_denied_should_not_retry():

    decision = should_retry(
        FailureCategory.PERMISSION_DENIED,
        retry_count=0,
    )

    assert decision.should_retry is False
    assert decision.max_retries == 0


def test_constraint_violation_should_not_retry():

    decision = should_retry(
        FailureCategory.CONSTRAINT_VIOLATION,
        retry_count=0,
    )

    assert decision.should_retry is False
    assert decision.max_retries == 0


def test_unknown_should_not_retry():

    decision = should_retry(
        FailureCategory.UNKNOWN,
        retry_count=0,
    )

    assert decision.should_retry is False
    assert decision.max_retries == 0


def test_negative_retry_count():

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=-1,
    )

    assert decision.should_retry is False
    assert decision.retry_count == -1


def test_invalid_retry_count_type():

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count="0",
    )

    assert decision.should_retry is False
    assert decision.retry_count == 0


def test_none_category():

    decision = should_retry(
        FailureCategory.NONE,
        retry_count=0,
    )

    assert decision.should_retry is False
    assert decision.max_retries == 0


def test_to_dict():

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=0,
    )

    assert decision.to_dict() == {
        "should_retry": True,
        "retry_count": 0,
        "max_retries": 2,
        "reason": ("允許 Retry #1。" "最大 Retry 次數為 2。"),
    }


def test_all_retry_limits_are_non_negative():

    for category, limit in RETRY_LIMITS.items():

        assert isinstance(
            category,
            FailureCategory,
        )

        assert isinstance(
            limit,
            int,
        )

        assert limit >= 0
