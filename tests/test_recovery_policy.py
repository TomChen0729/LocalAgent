from agent.failure_classifier import FailureCategory
from agent.recovery_policy import (
    RecoveryPolicy,
)


def test_get_alternative_tools():

    policy = RecoveryPolicy()

    alternatives = policy.get_alternative_tools(
        "read_section",
    )

    assert alternatives == [
        "read_file",
    ]


def test_unknown_tool_has_no_alternative():

    policy = RecoveryPolicy()

    alternatives = policy.get_alternative_tools(
        "unknown_tool",
    )

    assert alternatives == []


def test_decide_recovery():

    policy = RecoveryPolicy()

    decision = policy.decide(
        "read_section",
        FailureCategory.NOT_FOUND,
    )

    assert decision.should_recover is True

    assert decision.original_tool == "read_section"

    assert decision.failure_category == (FailureCategory.NOT_FOUND)

    assert decision.alternatives == [
        "read_file",
    ]


def test_permission_denied_does_not_recover():

    policy = RecoveryPolicy()

    decision = policy.decide(
        "read_section",
        FailureCategory.PERMISSION_DENIED,
    )

    assert decision.should_recover is False

    assert decision.alternatives == []


def test_constraint_violation_does_not_recover():

    policy = RecoveryPolicy()

    decision = policy.decide(
        "read_section",
        FailureCategory.CONSTRAINT_VIOLATION,
    )

    assert decision.should_recover is False

    assert decision.alternatives == []


def test_unknown_failure_does_not_recover():

    policy = RecoveryPolicy()

    decision = policy.decide(
        "read_section",
        FailureCategory.UNKNOWN,
    )

    assert decision.should_recover is False

    assert decision.alternatives == []


def test_tool_without_alternative_does_not_recover():

    policy = RecoveryPolicy()

    decision = policy.decide(
        "read_file",
        FailureCategory.NOT_FOUND,
    )

    assert decision.should_recover is False

    assert decision.alternatives == []


def test_recovery_decision_to_dict():

    policy = RecoveryPolicy()

    decision = policy.decide(
        "read_section",
        FailureCategory.NOT_FOUND,
    )

    result = decision.to_dict()

    assert result["should_recover"] is True

    assert result["original_tool"] == "read_section"

    assert result["failure_category"] == "not_found"

    assert result["alternatives"] == [
        "read_file",
    ]
