from dataclasses import dataclass
from typing import List, Optional

# ============================================================
# Recovery Selection Result
# ============================================================


@dataclass(frozen=True)
class RecoverySelection:
    """
    描述 Alternative Tool Selection 的結果。
    """

    selected_tool: Optional[str]
    candidates: List[str]
    reason: str

    @property
    def selected(self):
        return self.selected_tool

    def to_dict(self):
        return {
            "selected_tool": self.selected_tool,
            "candidates": list(self.candidates),
            "reason": self.reason,
        }


# ============================================================
# Recovery Selector
# ============================================================


class RecoverySelector:
    """
    Deterministic Alternative Tool Selector。

    負責：

    1. 接收 Alternative Tool candidates
    2. 按照既定順序選擇 Tool
    3. 回傳 Selection Result

    不負責：

    - 執行 Tool
    - Permission Check
    - Tool Constraint Check
    - Failure Classification
    - Retry
    - Verification
    - 呼叫 LLM
    """

    def select(
        self,
        candidates: List[str],
    ) -> RecoverySelection:

        # ====================================================
        # 1. Validate candidates
        # ====================================================

        if not isinstance(
            candidates,
            list,
        ):

            return RecoverySelection(
                selected_tool=None,
                candidates=[],
                reason="Alternative Tool candidates 必須是 list。",
            )

        # ====================================================
        # 2. Remove invalid / duplicate candidates
        # ====================================================

        normalized_candidates = []

        for candidate in candidates:

            if not isinstance(
                candidate,
                str,
            ):

                continue

            candidate = candidate.strip()

            if not candidate:

                continue

            if candidate in normalized_candidates:

                continue

            normalized_candidates.append(
                candidate,
            )

        # ====================================================
        # 3. No candidate
        # ====================================================

        if not normalized_candidates:

            return RecoverySelection(
                selected_tool=None,
                candidates=[],
                reason="沒有可用的 Alternative Tool。",
            )

        # ====================================================
        # 4. Deterministic Selection
        # ====================================================

        selected_tool = normalized_candidates[0]

        return RecoverySelection(
            selected_tool=selected_tool,
            candidates=normalized_candidates,
            reason="按照 Alternative Tool 優先順序選擇第一個候選 Tool。",
        )


__all__ = [
    "RecoverySelection",
    "RecoverySelector",
]
