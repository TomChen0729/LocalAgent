from dataclasses import dataclass

# ============================================================
# Default Recovery Limit
# ============================================================

DEFAULT_MAX_RECOVERY_ATTEMPTS = 1


# ============================================================
# Recovery Attempt Decision
# ============================================================


@dataclass(frozen=True)
class RecoveryAttemptDecision:
    """
    描述目前是否允許進行 Recovery。
    """

    should_recover: bool
    attempt_count: int
    max_attempts: int
    reason: str

    def to_dict(self):
        return {
            "should_recover": self.should_recover,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "reason": self.reason,
        }


# ============================================================
# Recovery Attempt Policy
# ============================================================


class RecoveryAttemptPolicy:
    """
    Deterministic Recovery Attempt Policy。

    負責：

    - 控制 Recovery 次數
    - 防止 Recovery Loop

    不負責：

    - Failure Classification
    - Alternative Tool Selection
    - Tool Execution
    - Verification
    - Task State
    """

    def __init__(
        self,
        max_attempts=DEFAULT_MAX_RECOVERY_ATTEMPTS,
    ):

        if not isinstance(
            max_attempts,
            int,
        ) or isinstance(
            max_attempts,
            bool,
        ):

            raise ValueError("max_attempts 必須是正整數。")

        if max_attempts < 0:

            raise ValueError("max_attempts 不可以小於 0。")

        self.max_attempts = max_attempts

    # ========================================================
    # Check Recovery Limit
    # ========================================================

    def can_recover(
        self,
        attempt_count: int,
    ) -> RecoveryAttemptDecision:

        if not isinstance(
            attempt_count,
            int,
        ) or isinstance(
            attempt_count,
            bool,
        ):

            return RecoveryAttemptDecision(
                should_recover=False,
                attempt_count=attempt_count,
                max_attempts=self.max_attempts,
                reason="Recovery attempt count 必須是整數。",
            )

        if attempt_count < 0:

            return RecoveryAttemptDecision(
                should_recover=False,
                attempt_count=attempt_count,
                max_attempts=self.max_attempts,
                reason="Recovery attempt count 不可以小於 0。",
            )

        # ----------------------------------------------------
        # Limit reached
        # ----------------------------------------------------

        if attempt_count >= self.max_attempts:

            return RecoveryAttemptDecision(
                should_recover=False,
                attempt_count=attempt_count,
                max_attempts=self.max_attempts,
                reason="已達到 Recovery 次數上限。",
            )

        # ----------------------------------------------------
        # Recovery allowed
        # ----------------------------------------------------

        return RecoveryAttemptDecision(
            should_recover=True,
            attempt_count=attempt_count,
            max_attempts=self.max_attempts,
            reason="尚未達到 Recovery 次數上限。",
        )


__all__ = [
    "DEFAULT_MAX_RECOVERY_ATTEMPTS",
    "RecoveryAttemptDecision",
    "RecoveryAttemptPolicy",
]
