from dataclasses import dataclass
from typing import Any, Dict

# ============================================================
# Recovery Argument Transformation Result
# ============================================================


@dataclass(frozen=True)
class RecoveryArguments:
    """
    描述 Alternative Tool 使用的 Arguments。
    """

    original_arguments: Dict[str, Any]
    transformed_arguments: Dict[str, Any]
    changed: bool
    reason: str

    def to_dict(self):
        return {
            "original_arguments": dict(
                self.original_arguments,
            ),
            "transformed_arguments": dict(
                self.transformed_arguments,
            ),
            "changed": self.changed,
            "reason": self.reason,
        }


# ============================================================
# Recovery Argument Adapter
# ============================================================


class RecoveryArgumentAdapter:
    """
    負責將原始 Tool Arguments 轉換成
    Alternative Tool 所需要的 Arguments。

    不負責：

    - Tool Execution
    - Permission
    - Constraint
    - Failure Classification
    - Recovery Selection
    """

    def transform(
        self,
        original_tool: str,
        alternative_tool: str,
        arguments: Dict[str, Any],
    ) -> RecoveryArguments:

        if not isinstance(
            arguments,
            dict,
        ):

            return RecoveryArguments(
                original_arguments={},
                transformed_arguments={},
                changed=False,
                reason="Tool arguments 必須是 dict。",
            )

        original_arguments = dict(
            arguments,
        )

        # ====================================================
        # read_section → read_file
        # ====================================================

        if original_tool == "read_section" and alternative_tool == "read_file":

            transformed_arguments = {}

            if "path" in original_arguments:

                transformed_arguments["path"] = original_arguments["path"]

            return RecoveryArguments(
                original_arguments=original_arguments,
                transformed_arguments=transformed_arguments,
                changed=(transformed_arguments != original_arguments),
                reason=("移除 read_section 專用參數，" "轉換為 read_file arguments。"),
            )

        # ====================================================
        # Default
        # ====================================================

        return RecoveryArguments(
            original_arguments=original_arguments,
            transformed_arguments=original_arguments,
            changed=False,
            reason="Alternative Tool 不需要特殊 Arguments 轉換。",
        )


__all__ = [
    "RecoveryArguments",
    "RecoveryArgumentAdapter",
]
