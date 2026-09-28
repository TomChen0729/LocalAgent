"""
Phase 9.4 - Parameter Correction

負責處理 Tool execution failure 中，
可以被安全判斷與修正的參數問題。

設計原則：

1. 不直接執行 Tool
2. 不直接修改 Project
3. 不呼叫 LLM
4. 不猜測未知參數
5. 只回傳 correction result
6. 真正的 Tool execution 仍由 ToolRunner 負責
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CorrectionResult:
    """
    Parameter Correction 的結果。
    """

    corrected: bool

    arguments: Dict[str, Any]

    reason: Optional[str] = None


class ParameterCorrection:
    """
    Parameter Correction Engine。

    目前採用 deterministic correction。

    不負責：
        - Tool execution
        - Permission
        - Recovery orchestration
        - LLM reasoning

    只負責：
        arguments + error
            ↓
        correction decision
    """

    def __init__(self):
        pass

    # ========================================================
    # Public API
    # ========================================================

    def correct(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        error: Optional[str] = None,
    ) -> CorrectionResult:

        # ----------------------------------------------------
        # 保留原始 arguments
        # ----------------------------------------------------

        original_arguments = dict(arguments)

        # ----------------------------------------------------
        # 沒有 error
        #
        # 代表目前沒有 correction 的必要。
        # ----------------------------------------------------

        if not error:
            return CorrectionResult(
                corrected=False,
                arguments=original_arguments,
                reason=None,
            )

        # ----------------------------------------------------
        # read_file
        # ----------------------------------------------------

        if tool_name == "read_file":

            return self._correct_read_file(
                original_arguments,
                error,
            )

        # ----------------------------------------------------
        # 其他 Tool
        #
        # 尚未建立 deterministic correction rule。
        # 不應該任意修改 arguments。
        # ----------------------------------------------------

        return CorrectionResult(
            corrected=False,
            arguments=original_arguments,
            reason=(
                f"目前沒有 {tool_name} 的 " "deterministic parameter correction rule。"
            ),
        )

    # ========================================================
    # read_file correction
    # ========================================================

    def _correct_read_file(
        self,
        arguments: Dict[str, Any],
        error: str,
    ) -> CorrectionResult:

        # ----------------------------------------------------
        # path 不存在
        # ----------------------------------------------------

        if "path" not in arguments:

            return CorrectionResult(
                corrected=False,
                arguments=arguments,
                reason="read_file 缺少必要參數 path。",
            )

        path = arguments["path"]

        # ----------------------------------------------------
        # path 必須是 string
        # ----------------------------------------------------

        if not isinstance(path, str):

            return CorrectionResult(
                corrected=False,
                arguments=arguments,
                reason="read_file 的 path 必須是 string。",
            )

        # ----------------------------------------------------
        # 目前 Phase 9.4 不直接猜測檔案名稱。
        #
        # 例如：
        #
        # README.tx
        #
        # 不能直接猜：
        #
        # README.md
        #
        # 除非未來加入明確的 project context / file matching
        # 機制。
        # ----------------------------------------------------

        return CorrectionResult(
            corrected=False,
            arguments=arguments,
            reason=("目前無法安全判斷 read_file " "參數應如何修正。"),
        )
