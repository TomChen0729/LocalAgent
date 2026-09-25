from dataclasses import dataclass
from typing import List

from agent.failure_classifier import FailureCategory

# ============================================================
# Alternative Tool Mapping
# ============================================================
#
# 格式：
#
# 原始 Tool
#     ↓
# Alternative Tools
#
# 注意：
# RecoveryPolicy 只負責「提供候選 Tool」。
#
# 它不負責：
# - 執行 Tool
# - Permission Check
# - Tool Constraint Check
# - Retry
# - Verification
#
# 這些責任仍然由其他元件處理。
# ============================================================

ALTERNATIVE_TOOLS = {
    "read_section": [
        "read_file",
    ],
    "search_files": [
        "read_file",
    ],
}


# ============================================================
# Recovery Decision
# ============================================================


@dataclass(frozen=True)
class RecoveryDecision:
    """
    描述 Recovery Policy 對一次失敗所做出的決策。
    """

    should_recover: bool
    original_tool: str
    failure_category: FailureCategory
    alternatives: List[str]
    reason: str

    def to_dict(self):
        return {
            "should_recover": self.should_recover,
            "original_tool": self.original_tool,
            "failure_category": self.failure_category.value,
            "alternatives": list(self.alternatives),
            "reason": self.reason,
        }


# ============================================================
# Recovery Policy
# ============================================================


class RecoveryPolicy:
    """
    Deterministic Recovery Policy。

    負責：

    1. 判斷目前 Failure 是否允許 Recovery
    2. 找出 Alternative Tools
    3. 建立 RecoveryDecision

    不負責：

    - 執行 Tool
    - 修改 Task State
    - 呼叫 LLM
    - Permission Check
    - Verification
    """

    def __init__(
        self,
        alternative_tools=None,
    ):
        if alternative_tools is None:
            alternative_tools = ALTERNATIVE_TOOLS

        self.alternative_tools = alternative_tools

    # ========================================================
    # Get Alternative Tools
    # ========================================================

    def get_alternative_tools(
        self,
        tool_name: str,
    ) -> List[str]:

        alternatives = self.alternative_tools.get(
            tool_name,
            [],
        )

        return list(alternatives)

    # ========================================================
    # Decide Recovery
    # ========================================================

    def decide(
        self,
        tool_name: str,
        failure_category: FailureCategory,
    ) -> RecoveryDecision:

        alternatives = self.get_alternative_tools(
            tool_name,
        )

        # ----------------------------------------------------
        # 沒有 Alternative Tool
        # ----------------------------------------------------

        if not alternatives:

            return RecoveryDecision(
                should_recover=False,
                original_tool=tool_name,
                failure_category=failure_category,
                alternatives=[],
                reason="沒有可用的 Alternative Tool。",
            )

        # ----------------------------------------------------
        # 不適合 Recovery 的 Failure
        # ----------------------------------------------------

        if failure_category in {
            FailureCategory.PERMISSION_DENIED,
            FailureCategory.CONSTRAINT_VIOLATION,
        }:

            return RecoveryDecision(
                should_recover=False,
                original_tool=tool_name,
                failure_category=failure_category,
                alternatives=[],
                reason="目前的 Failure Category 不允許 Alternative Tool Recovery。",
            )

        # ----------------------------------------------------
        # Unknown Failure
        # ----------------------------------------------------

        if failure_category == FailureCategory.UNKNOWN:

            return RecoveryDecision(
                should_recover=False,
                original_tool=tool_name,
                failure_category=failure_category,
                alternatives=[],
                reason="Unknown Failure 不進行自動 Recovery。",
            )

        # ----------------------------------------------------
        # 可 Recovery
        # ----------------------------------------------------

        return RecoveryDecision(
            should_recover=True,
            original_tool=tool_name,
            failure_category=failure_category,
            alternatives=alternatives,
            reason="存在可用的 Alternative Tool。",
        )


__all__ = [
    "ALTERNATIVE_TOOLS",
    "RecoveryDecision",
    "RecoveryPolicy",
]
