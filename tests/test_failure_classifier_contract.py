from agent.failure_classifier import (
    FailureCategory,
    classify_failure,
)


def test_string_failure_is_classified():
    result = classify_failure("找不到指定的檔案。")

    assert result.failed is True
    assert result.category == FailureCategory.NOT_FOUND


def test_string_success_is_not_failure():
    result = classify_failure("成功讀取 README.md。")

    assert result.failed is False
    assert result.category == FailureCategory.NONE


def test_empty_string_is_failure():
    result = classify_failure("")

    assert result.failed is True


def test_dict_success_result():
    result = classify_failure(
        {
            "success": True,
            "result": "README content",
        }
    )

    assert result.failed is False


def test_dict_failure_result():
    result = classify_failure(
        {
            "success": False,
            "error": "找不到指定的檔案。",
        }
    )

    assert result.failed is True
    assert result.category == FailureCategory.NOT_FOUND


def test_dict_failure_with_message():
    result = classify_failure(
        {
            "success": False,
            "message": "Permission denied。",
        }
    )

    assert result.failed is True
    assert result.category == FailureCategory.PERMISSION_DENIED
