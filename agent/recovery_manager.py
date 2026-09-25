from agent.failure_classifier import (
    classify_failure,
)

from agent.recovery_policy import (
    RecoveryPolicy,
)

from agent.recovery_selector import (
    RecoverySelector,
)

from agent.recovery_executor import (
    RecoveryExecutor,
)

from agent.recovery_attempt import (
    RecoveryAttemptPolicy,
)

from agent.recovery_arguments import (
    RecoveryArgumentAdapter,
)


class RecoveryManager:
    """
    Recovery Orchestrator

    負責協調：

    Failure Classification
        ↓
    Recovery Policy
        ↓
    Recovery Attempt Policy
        ↓
    Recovery Selection
        ↓
    Recovery Argument Transformation
        ↓
    Recovery Execution

    RecoveryManager 不負責：

    - Task State
    - Tool History
    - Agent Messages
    - Verification
    - Requirement Verification
    """

    def __init__(
        self,
        tool_runner,
        recovery_policy=None,
        recovery_selector=None,
        recovery_executor=None,
        recovery_attempt_policy=None,
        recovery_argument_adapter=None,
    ):
        self.recovery_policy = recovery_policy or RecoveryPolicy()

        self.recovery_selector = recovery_selector or RecoverySelector()

        self.recovery_executor = recovery_executor or RecoveryExecutor(tool_runner)

        self.recovery_attempt_policy = (
            recovery_attempt_policy or RecoveryAttemptPolicy()
        )

        self.recovery_argument_adapter = (
            recovery_argument_adapter or RecoveryArgumentAdapter()
        )

    def handle(
        self,
        original_tool,
        arguments,
        tool_result,
        attempt_count=0,
    ):
        """
        執行一次完整 Recovery Decision Flow。

        注意：
        這個方法只負責 Recovery 本身。

        不修改 Runtime Task State。
        不修改 Tool History。
        不修改 Agent Messages。
        """

        # ========================================================
        # 1. Failure Classification
        # ========================================================

        classification = classify_failure(
            tool_result,
        )

        if not classification.failed:

            return {
                "recovered": False,
                "attempted": False,
                "original_tool": original_tool,
                "failure": classification.to_dict(),
                "reason": ("Tool Result 沒有被判定為 Failure。"),
            }

        failure_category = classification.category

        # ========================================================
        # 2. Recovery Policy
        # ========================================================

        decision = self.recovery_policy.decide(
            original_tool,
            failure_category,
        )

        if not decision.should_recover:

            return {
                "recovered": False,
                "attempted": False,
                "original_tool": original_tool,
                "failure": classification.to_dict(),
                "recovery": decision.to_dict(),
                "reason": decision.reason,
            }

        # ========================================================
        # 3. Recovery Attempt Policy
        # ========================================================

        attempt_decision = self.recovery_attempt_policy.can_recover(
            attempt_count,
        )

        if not attempt_decision.should_recover:

            return {
                "recovered": False,
                "attempted": False,
                "original_tool": original_tool,
                "failure": classification.to_dict(),
                "recovery": decision.to_dict(),
                "attempt": attempt_decision.to_dict(),
                "reason": attempt_decision.reason,
            }

        # ========================================================
        # 4. Recovery Tool Selection
        # ========================================================

        selection = self.recovery_selector.select(
            decision.alternatives,
        )

        if not selection.selected:

            return {
                "recovered": False,
                "attempted": False,
                "original_tool": original_tool,
                "failure": classification.to_dict(),
                "recovery": decision.to_dict(),
                "selection": selection.to_dict(),
                "reason": selection.reason,
            }

        alternative_tool = selection.selected_tool

        # ========================================================
        # 5. Recovery Arguments
        # ========================================================

        transformed = self.recovery_argument_adapter.transform(
            original_tool,
            alternative_tool,
            arguments,
        )

        # ========================================================
        # 6. Execute Recovery Tool
        # ========================================================

        execution = self.recovery_executor.execute(
            alternative_tool,
            transformed.transformed_arguments,
        )

        # ========================================================
        # 7. Return Recovery Result
        # ========================================================

        return {
            "recovered": execution.success,
            "attempted": True,
            "original_tool": original_tool,
            "failure": classification.to_dict(),
            "recovery": decision.to_dict(),
            "selection": selection.to_dict(),
            "arguments": transformed.to_dict(),
            "execution": execution.to_dict(),
        }


__all__ = [
    "RecoveryManager",
]
