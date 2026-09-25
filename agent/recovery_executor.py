from dataclasses import dataclass
from typing import Any, Dict, Optional

# ============================================================
# Recovery Execution Result
# ============================================================


@dataclass(frozen=True)
class RecoveryExecutionResult:
    """
    描述一次 Alternative Tool Recovery 執行結果。
    """

    success: bool
    tool: Optional[str]
    arguments: Dict[str, Any]
    result: Any
    recovery: bool
    message: str

    def to_dict(self):
        return {
            "success": self.success,
            "tool": self.tool,
            "arguments": dict(self.arguments),
            "result": self.result,
            "recovery": self.recovery,
            "message": self.message,
        }


# ============================================================
# Recovery Executor
# ============================================================


class RecoveryExecutor:
    """
    負責執行已經選定的 Alternative Tool。

    RecoveryExecutor 不負責：

    - Failure Classification
    - Alternative Tool Selection
    - Permission Check
    - Tool Constraint Check
    - Tool Dispatch
    - Retry Policy
    - Verification

    實際 Tool 執行一律交給 ToolRunner。
    """

    def __init__(self, tool_runner):
        self.tool_runner = tool_runner

    # ========================================================
    # Execute Alternative Tool
    # ========================================================

    def execute(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> RecoveryExecutionResult:

        if arguments is None:
            arguments = {}

        # ----------------------------------------------------
        # Validate Tool Name
        # ----------------------------------------------------

        if (
            not isinstance(
                tool_name,
                str,
            )
            or not tool_name.strip()
        ):

            return RecoveryExecutionResult(
                success=False,
                tool=None,
                arguments=arguments,
                result=None,
                recovery=True,
                message="Alternative Tool 名稱無效。",
            )

        # ----------------------------------------------------
        # Execute Through ToolRunner
        # ----------------------------------------------------

        result = self.tool_runner.run(
            tool_name,
            arguments,
        )

        # ----------------------------------------------------
        # Normalize Success
        # ----------------------------------------------------

        if isinstance(
            result,
            dict,
        ):

            success = result.get(
                "success",
                True,
            )

        else:

            success = True

        return RecoveryExecutionResult(
            success=bool(success),
            tool=tool_name,
            arguments=arguments,
            result=result,
            recovery=True,
            message=(
                "Alternative Tool 執行成功。"
                if success
                else "Alternative Tool 執行失敗。"
            ),
        )


__all__ = [
    "RecoveryExecutionResult",
    "RecoveryExecutor",
]
