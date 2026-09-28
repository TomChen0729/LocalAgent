"""
Auto Test Runner for LocalAgent.

在 Agent 寫完程式碼後自動偵測並執行測試，
將測試結果回傳給 LLM，讓 Agent 自動修復。

目前支援：pytest（Python）
"""

import shutil
import subprocess
from pathlib import Path


class TestRunner:
    """
    偵測專案的測試框架並在檔案寫入後自動執行測試。

    設計原則：
    1. 不使用 shell=True
    2. 不需要 Permission Layer（測試是唯讀操作）
    3. 截斷過長的輸出，避免爆 context window
    4. 結果格式化成 Agent 可理解的系統訊息
    """

    # 測試檔案的 glob pattern
    TEST_PATTERNS = [
        "test_*.py",
        "*_test.py",
    ]

    # 輸出行數上限（避免 context 爆炸）
    MAX_OUTPUT_LINES = 60

    # 測試執行 timeout（秒）
    DEFAULT_TIMEOUT = 120

    # pytest 執行參數
    PYTEST_ARGS = [
        "-x",           # 遇到第一個失敗就停止
        "--tb=short",   # 短格式 traceback
        "-q",           # 安靜模式
    ]

    def __init__(self, project_path):
        self.project_path = Path(project_path)

    # ----------------------------------------------------------
    # Detection
    # ----------------------------------------------------------

    def has_test_files(self) -> bool:
        """確認專案中是否有測試檔案。"""
        for pattern in self.TEST_PATTERNS:
            if any(self.project_path.rglob(pattern)):
                return True
        return False

    def pytest_available(self) -> bool:
        """確認 pytest 是否已安裝。"""
        return shutil.which("pytest") is not None

    def should_run(self, written_files: set) -> bool:
        """
        根據這一輪寫入的檔案判斷是否要執行測試。

        判斷條件（全部成立才執行）：
        1. 有 Python 檔案被寫入或修改
        2. 專案中存在測試檔案
        3. pytest 已安裝

        Parameters
        ----------
        written_files : set
            這一輪 write_file / edit_file 操作的路徑集合。
        """
        if not written_files:
            return False

        has_python_file = any(
            str(f).endswith(".py")
            for f in written_files
        )

        if not has_python_file:
            return False

        return self.has_test_files() and self.pytest_available()

    # ----------------------------------------------------------
    # Execution
    # ----------------------------------------------------------

    def run(self) -> dict:
        """
        執行 pytest 並回傳結構化結果。

        Returns
        -------
        dict：
            success   : bool   — 全部測試通過為 True
            exit_code : int    — pytest 的 exit code
            output    : str    — 截斷後的輸出（stdout + stderr）
            truncated : bool   — 輸出是否被截斷
            available : bool   — pytest 是否可用
        """
        pytest_exe = shutil.which("pytest")

        if not pytest_exe:
            return {
                "success": False,
                "exit_code": -1,
                "output": "pytest not found in PATH.",
                "truncated": False,
                "available": False,
            }

        try:
            result = subprocess.run(
                [pytest_exe, *self.PYTEST_ARGS],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                timeout=self.DEFAULT_TIMEOUT,
            )

            combined = (result.stdout or "") + (result.stderr or "")
            lines = combined.splitlines()
            truncated = False

            if len(lines) > self.MAX_OUTPUT_LINES:
                lines = lines[-self.MAX_OUTPUT_LINES:]
                truncated = True

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "output": "\n".join(lines),
                "truncated": truncated,
                "available": True,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"pytest 執行超過 {self.DEFAULT_TIMEOUT} 秒，已終止。",
                "truncated": False,
                "available": True,
            }

        except Exception as exc:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"pytest 執行失敗：{exc}",
                "truncated": False,
                "available": True,
            }

    # ----------------------------------------------------------
    # Formatting
    # ----------------------------------------------------------

    def format_for_agent(self, result: dict) -> str:
        """
        將測試結果格式化成 LLM 可理解的系統訊息。
        """
        status = "PASS ✅" if result["success"] else "FAIL ❌"
        output = result.get("output", "(no output)")
        truncated_note = (
            "\n[輸出已截斷，只顯示最後部分]"
            if result.get("truncated")
            else ""
        )

        lines = [
            "AUTO TEST RESULT",
            f"Status: {status}",
            f"Exit Code: {result['exit_code']}",
            "",
            "--- Output ---",
            output,
            truncated_note,
        ]

        if not result["success"]:
            lines += [
                "",
                "測試失敗。",
                "請根據上方 Test Output 分析失敗原因，",
                "並使用 edit_file 修復相關程式碼。",
                "修復後 Runtime 會自動再次執行測試。",
                "不要在測試尚未通過時給出最終回答。",
            ]
        else:
            lines += [
                "",
                "所有測試通過。",
                "可以繼續下一步或給出最終回答。",
            ]

        return "\n".join(lines)
