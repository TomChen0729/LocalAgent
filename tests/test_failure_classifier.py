from agent.failure_classifier import (
    FailureCategory,
    classify_failure,
)


def test_success_result():

    result = classify_failure("成功：已讀取 README.md")

    assert result.failed is False
    assert result.category == FailureCategory.NONE
    assert result.retryable is False


def test_not_found_result():

    result = classify_failure("錯誤：找不到檔案 README.md")

    assert result.failed is True
    assert result.category == FailureCategory.NOT_FOUND
    assert result.retryable is True


def test_permission_denied_result():

    result = classify_failure("錯誤：沒有權限讀取 README.md")

    assert result.failed is True
    assert result.category == FailureCategory.PERMISSION_DENIED
    assert result.retryable is False


def test_invalid_input_result():

    result = classify_failure("錯誤：path 必須是字串。")

    assert result.failed is True
    assert result.category == FailureCategory.INVALID_INPUT
    assert result.retryable is True


def test_timeout_result():

    result = classify_failure("錯誤：command timed out")

    assert result.failed is True
    assert result.category == FailureCategory.TIMEOUT
    assert result.retryable is True


def test_constraint_violation_result():

    result = classify_failure("錯誤：禁止存取專案目錄以外的路徑。")

    assert result.failed is True
    assert result.category == FailureCategory.CONSTRAINT_VIOLATION
    assert result.retryable is False


def test_execution_error_result():

    result = classify_failure("錯誤：執行失敗")

    assert result.failed is True
    assert result.category == FailureCategory.EXECUTION_ERROR
    assert result.retryable is True


def test_empty_result():

    result = classify_failure("")

    assert result.failed is True
    assert result.category == FailureCategory.UNKNOWN
    assert result.retryable is False


def test_non_string_result():

    result = classify_failure(None)

    assert result.failed is True
    assert result.category == FailureCategory.INVALID_INPUT
    assert result.retryable is False


def test_to_dict():

    result = classify_failure("錯誤：找不到檔案 README.md")

    assert result.to_dict() == {
        "failed": True,
        "category": "not_found",
        "retryable": True,
    }
