from dataclasses import dataclass

from agent.failure_classifier import FailureCategory

# ============================================================
# Retry Configuration
# ============================================================

DEFAULT_MAX_RETRIES = 2


RETRY_LIMITS = {
    FailureCategory.NOT_FOUND: 2,
    FailureCategory.INVALID_INPUT: 2,
    FailureCategory.EXECUTION_ERROR: 2,
    FailureCategory.TIMEOUT: 2,
    FailureCategory.PERMISSION_DENIED: 0,
    FailureCategory.CONSTRAINT_VIOLATION: 0,
    FailureCategory.UNKNOWN: 0,
    FailureCategory.NONE: 0,
}


# ============================================================
# Retry Decision
# ============================================================


@dataclass(frozen=True)
class RetryDecision:
    """
    Retry Policy 的決策結果。

    Attributes:
        should_retry:
            是否應該重新執行 Tool。

        retry_count:
            目前已經進行的 Retry 次數。

        max_retries:
            此 Failure Category 最大允許 Retry 次數。

        reason:
            決策原因。
    """

    should_retry: bool
    retry_count: int
    max_retries: int
    reason: str

    def to_dict(self) -> dict:
        """
        轉換成 Runtime 可以使用的 dictionary。
        """

        return {
            "should_retry": self.should_retry,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "reason": self.reason,
        }


# ============================================================
# Retry Policy
# ============================================================


def get_retry_limit(
    category: FailureCategory,
) -> int:
    """
    取得指定 Failure Category 的最大 Retry 次數。
    """

    if not isinstance(category, FailureCategory):
        return 0

    return RETRY_LIMITS.get(
        category,
        0,
    )


def should_retry(
    category: FailureCategory,
    retry_count: int,
) -> RetryDecision:
    """
    根據 Failure Category 與目前 Retry 次數，
    決定是否應該重新執行 Tool。

    注意：

        這個函式是 deterministic。

        不呼叫 LLM。
        不執行 Tool。
        不修改 Project State。

    retry_count 定義：

        0 = 尚未 Retry
        1 = 已經 Retry 1 次
        2 = 已經 Retry 2 次
    """

    # --------------------------------------------------------
    # Validate retry_count
    # --------------------------------------------------------

    if not isinstance(retry_count, int):
        return RetryDecision(
            should_retry=False,
            retry_count=0,
            max_retries=0,
            reason="retry_count 必須是整數。",
        )

    if retry_count < 0:
        return RetryDecision(
            should_retry=False,
            retry_count=retry_count,
            max_retries=0,
            reason="retry_count 不可以小於 0。",
        )

    # --------------------------------------------------------
    # Get Retry Limit
    # --------------------------------------------------------

    max_retries = get_retry_limit(category)

    # --------------------------------------------------------
    # Non-retryable Failure
    # --------------------------------------------------------

    if max_retries == 0:

        return RetryDecision(
            should_retry=False,
            retry_count=retry_count,
            max_retries=0,
            reason=(f"Failure Category " f"'{category.value}' 不允許 Retry。"),
        )

    # --------------------------------------------------------
    # Retry Available
    # --------------------------------------------------------

    if retry_count < max_retries:

        next_retry = retry_count + 1

        return RetryDecision(
            should_retry=True,
            retry_count=retry_count,
            max_retries=max_retries,
            reason=(
                f"允許 Retry #{next_retry}。" f"最大 Retry 次數為 " f"{max_retries}。"
            ),
        )

    # --------------------------------------------------------
    # Retry Limit Reached
    # --------------------------------------------------------

    return RetryDecision(
        should_retry=False,
        retry_count=retry_count,
        max_retries=max_retries,
        reason=(f"已達 Retry 上限 " f"{max_retries} 次，停止重試。"),
    )


__all__ = [
    "DEFAULT_MAX_RETRIES",
    "RETRY_LIMITS",
    "RetryDecision",
    "get_retry_limit",
    "should_retry",
]
