from dataclasses import dataclass
from enum import Enum
from typing import Any


class FailureCategory(str, Enum):
    NONE = "none"

    INVALID_INPUT = "invalid_input"

    NOT_FOUND = "not_found"

    PERMISSION_DENIED = "permission_denied"

    EXECUTION_ERROR = "execution_error"

    TIMEOUT = "timeout"

    CONSTRAINT_VIOLATION = "constraint_violation"

    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FailureClassification:

    failed: bool

    category: FailureCategory

    retryable: bool

    def to_dict(self):

        return {
            "failed": self.failed,
            "category": self.category.value,
            "retryable": self.retryable,
        }


# ============================================================
# Failure Classification Patterns
# ============================================================

NOT_FOUND_PATTERNS = (
    "找不到",
    "不存在",
    "not found",
    "no such file",
    "does not exist",
)


PERMISSION_PATTERNS = (
    "沒有權限",
    "權限不足",
    "permission denied",
    "access denied",
)


INVALID_INPUT_PATTERNS = (
    "必須是",
    "不可以是",
    "無效",
    "invalid",
)


TIMEOUT_PATTERNS = (
    "timeout",
    "timed out",
    "逾時",
)


CONSTRAINT_PATTERNS = (
    "禁止",
    "不允許",
    "constraint",
    "not allowed",
)


EXECUTION_PATTERNS = (
    "執行時發生問題",
    "執行失敗",
    "execution error",
    "execution failed",
)


# ============================================================
# Retryability
# ============================================================

RETRYABLE_CATEGORIES = {
    FailureCategory.NOT_FOUND,
    FailureCategory.INVALID_INPUT,
    FailureCategory.EXECUTION_ERROR,
    FailureCategory.TIMEOUT,
}


# ============================================================
# Internal Helpers
# ============================================================


def _classify_text(text: str) -> FailureClassification:
    """
    根據文字內容判斷 Failure Category。

    這裡只負責文字分類，
    不處理 dict。
    """

    if not isinstance(text, str):

        return FailureClassification(
            failed=True,
            category=FailureCategory.INVALID_INPUT,
            retryable=False,
        )

    text = text.strip()

    if not text:

        return FailureClassification(
            failed=True,
            category=FailureCategory.UNKNOWN,
            retryable=False,
        )

    lowered = text.lower()

    # --------------------------------------------------------
    # NOT_FOUND
    # --------------------------------------------------------

    if any(pattern.lower() in lowered for pattern in NOT_FOUND_PATTERNS):

        return FailureClassification(
            failed=True,
            category=FailureCategory.NOT_FOUND,
            retryable=True,
        )

    # --------------------------------------------------------
    # PERMISSION_DENIED
    # --------------------------------------------------------

    if any(pattern.lower() in lowered for pattern in PERMISSION_PATTERNS):

        return FailureClassification(
            failed=True,
            category=FailureCategory.PERMISSION_DENIED,
            retryable=False,
        )

    # --------------------------------------------------------
    # INVALID_INPUT
    # --------------------------------------------------------

    if any(pattern.lower() in lowered for pattern in INVALID_INPUT_PATTERNS):

        return FailureClassification(
            failed=True,
            category=FailureCategory.INVALID_INPUT,
            retryable=True,
        )

    # --------------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------------

    if any(pattern.lower() in lowered for pattern in TIMEOUT_PATTERNS):

        return FailureClassification(
            failed=True,
            category=FailureCategory.TIMEOUT,
            retryable=True,
        )

    # --------------------------------------------------------
    # CONSTRAINT_VIOLATION
    # --------------------------------------------------------

    if any(pattern.lower() in lowered for pattern in CONSTRAINT_PATTERNS):

        return FailureClassification(
            failed=True,
            category=FailureCategory.CONSTRAINT_VIOLATION,
            retryable=False,
        )

    # --------------------------------------------------------
    # EXECUTION_ERROR
    # --------------------------------------------------------

    if any(pattern.lower() in lowered for pattern in EXECUTION_PATTERNS):

        return FailureClassification(
            failed=True,
            category=FailureCategory.EXECUTION_ERROR,
            retryable=True,
        )

    # --------------------------------------------------------
    # No known failure pattern
    # --------------------------------------------------------

    return FailureClassification(
        failed=False,
        category=FailureCategory.NONE,
        retryable=False,
    )


def _extract_dict_message(result: dict) -> str:
    """
    從 Tool Result Dict 中取得可供 FailureClassifier
    判斷的文字。

    優先順序：

        error
        message
        result
        content
    """

    for key in (
        "error",
        "message",
        "result",
        "content",
    ):

        value = result.get(key)

        if isinstance(value, str):

            return value

    return ""


def _classify_dict(result: dict) -> FailureClassification:
    """
    分析 Dict 型 Tool Result。

    Tool Result Contract：

        success=True
            → Tool 成功

        success=False
            → Tool 失敗，
              再分析 error/message/result/content

    """

    if "success" not in result:

        return FailureClassification(
            failed=True,
            category=FailureCategory.INVALID_INPUT,
            retryable=False,
        )

    success = result["success"]

    # --------------------------------------------------------
    # Invalid success field
    # --------------------------------------------------------

    if not isinstance(success, bool):

        return FailureClassification(
            failed=True,
            category=FailureCategory.INVALID_INPUT,
            retryable=False,
        )

    # --------------------------------------------------------
    # Explicit success
    # --------------------------------------------------------

    if success:

        return FailureClassification(
            failed=False,
            category=FailureCategory.NONE,
            retryable=False,
        )

    # --------------------------------------------------------
    # Explicit failure
    # --------------------------------------------------------

    message = _extract_dict_message(
        result,
    )

    if not message:

        return FailureClassification(
            failed=True,
            category=FailureCategory.UNKNOWN,
            retryable=False,
        )

    return _classify_text(
        message,
    )


# ============================================================
# Public API
# ============================================================


def classify_failure(
    result: Any,
) -> FailureClassification:
    """
    將 Tool Result 標準化成 FailureClassification。

    支援：

        str
        dict

    其他型別會視為 INVALID_INPUT。
    """

    # --------------------------------------------------------
    # String Result
    # --------------------------------------------------------

    if isinstance(result, str):

        return _classify_text(
            result,
        )

    # --------------------------------------------------------
    # Dict Result
    # --------------------------------------------------------

    if isinstance(result, dict):

        return _classify_dict(
            result,
        )

    # --------------------------------------------------------
    # Unsupported Type
    # --------------------------------------------------------

    return FailureClassification(
        failed=True,
        category=FailureCategory.INVALID_INPUT,
        retryable=False,
    )


__all__ = [
    "FailureCategory",
    "FailureClassification",
    "classify_failure",
]
