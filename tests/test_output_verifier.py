from requirements.output_verifier import verify_output
from requirements.specification import OutputConstraints


def test_output_passes_when_under_max_words():
    constraints = OutputConstraints(
        max_words=10,
    )

    result = verify_output(
        "這是一個簡短回答。",
        constraints,
    )

    assert result["status"] == "passed"
    assert result["all_passed"] is True
    assert result["failed"] == 0


def test_output_fails_when_over_max_words():
    constraints = OutputConstraints(
        max_words=3,
    )

    result = verify_output(
        "這是一個超過字數限制的回答。",
        constraints,
    )

    assert result["status"] == "failed"
    assert result["all_passed"] is False
    assert result["failed"] == 1


def test_output_passes_when_no_suggestions_are_detected():
    constraints = OutputConstraints(
        no_suggestions=True,
    )

    result = verify_output(
        "main.py 包含三個參數。",
        constraints,
    )

    assert result["status"] == "passed"
    assert result["failed"] == 0


def test_output_fails_when_suggestion_is_detected():
    constraints = OutputConstraints(
        no_suggestions=True,
    )

    result = verify_output(
        "main.py 包含三個參數。建議你修改程式碼。",
        constraints,
    )

    assert result["status"] == "failed"
    assert result["failed"] == 1


def test_output_passes_when_no_examples_are_detected():
    constraints = OutputConstraints(
        no_examples=True,
    )

    result = verify_output(
        "這個函式接受兩個參數。",
        constraints,
    )

    assert result["status"] == "passed"
    assert result["failed"] == 0


def test_output_fails_when_example_is_detected():
    constraints = OutputConstraints(
        no_examples=True,
    )

    result = verify_output(
        "這個函式接受兩個參數。例如，可以傳入字串。",
        constraints,
    )

    assert result["status"] == "failed"
    assert result["failed"] == 1


def test_multiple_output_constraints_can_be_verified():
    constraints = OutputConstraints(
        max_words=20,
        no_suggestions=True,
        no_examples=True,
    )

    result = verify_output(
        "main.py 包含兩個參數。",
        constraints,
    )

    assert result["status"] == "passed"
    assert result["all_passed"] is True
    assert result["failed"] == 0


def test_multiple_output_constraints_fail_when_one_constraint_fails():
    constraints = OutputConstraints(
        max_words=20,
        no_suggestions=True,
        no_examples=True,
    )

    result = verify_output(
        "main.py 包含兩個參數。建議你修改程式。",
        constraints,
    )

    assert result["status"] == "failed"
    assert result["all_passed"] is False
    assert result["failed"] == 1


def test_semantic_constraints_are_skipped_for_now():
    constraints = OutputConstraints(
        parameter_names_only=True,
        no_analysis=True,
        language="zh-TW",
    )

    result = verify_output(
        "foo, bar",
        constraints,
    )

    assert result["status"] == "passed"
    assert result["all_passed"] is True

    skipped_constraints = [
        item["constraint"] for item in result["results"] if item["status"] == "skipped"
    ]

    assert "parameter_names_only" in skipped_constraints
    assert "no_analysis" in skipped_constraints
    assert "language" in skipped_constraints


def test_output_verifier_rejects_invalid_answer_type():
    constraints = OutputConstraints(
        max_words=10,
    )

    result = verify_output(
        None,
        constraints,
    )

    assert result["status"] == "failed"
    assert result["all_passed"] is False


def test_output_verifier_rejects_invalid_constraints_type():
    result = verify_output(
        "Hello",
        None,
    )

    assert result["status"] == "failed"
    assert result["all_passed"] is False


def test_output_without_deterministic_constraints_passes():
    constraints = OutputConstraints()

    result = verify_output(
        "任何回答都可以。",
        constraints,
    )

    assert result["status"] == "passed"
    assert result["all_passed"] is True
