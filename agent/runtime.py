from datetime import datetime

import json
import os
import re
import sys

from ollama import chat

from config.prompts import (
    SYSTEM_PROMPT,
    SHOW_AGENT_TRACE,
)

from tools.definitions import tools

from tools.file_tools import (
    list_files,
    file_exists,
    read_file,
    write_file,
    create_directory,
    search_files,
    edit_file,
    delete_file,
)
from tools.command_tools import execute_command
from tools.git_tools import (
    git_status,
    git_diff,
    git_log,
    git_commit,
)

from requirements.verifier import (
    verify_requirements,
)

from agent.permissions import PermissionManager

# ============================================================
# Agent Runtime Configuration
# ============================================================

MAX_TOOL_CALLS = 20

# 同一個 Tool + 完全相同 arguments
# 連續出現幾次後視為重複
MAX_REPEATED_TOOL_CALLS = 3

# 需要在執行後進行驗證的 Tool
VERIFICATION_REQUIRED_TOOLS = {
    "write_file",
    "edit_file",
    "create_directory",
    "delete_file",
    "git_commit",
}


# ============================================================
# Agent Runtime
# ============================================================


class AgentRuntime:

    def __init__(
        self,
        model="qwen3:8b",
    ):
        self.model = model

        # ----------------------------------------------------
        # Phase 5
        #
        # Permission Manager
        #
        # 正常 CLI：
        #     會詢問使用者是否允許操作
        #
        # pytest / 非互動環境：
        #     不要求 stdin 輸入
        #
        # 這樣不會破壞正式 CLI 的 Permission Safety。
        # ----------------------------------------------------

        self.permission_manager = PermissionManager(
            permission_callback=self._permission_callback,
        )

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        # ----------------------------------------------------
        # Tool Call Count
        # ----------------------------------------------------

        self.tool_call_count = 0

        # ----------------------------------------------------
        # Tool History
        # ----------------------------------------------------

        self.tool_history = []

        # ----------------------------------------------------
        # Task State
        # ----------------------------------------------------

        self.task_state = {
            "status": "idle",
            "user_input": None,
            "started_at": None,
            "finished_at": None,
            "tool_calls": 0,
            "last_tool": None,
            "last_result": None,
            # Phase 4.6
            "verification_required": False,
            "verification_status": None,
            "verification_tool": None,
            "verification_result": None,
            # Phase 4.7
            "requirement_status": None,
            "requirement_result": None,
            # Phase 4.8
            "requirements": [],
            "requirement_verification": None,
        }

    # ========================================================
    # Phase 5
    # Permission Callback
    # ========================================================

    def _permission_callback(
        self,
        tool_name,
        action,
        arguments,
    ):
        """
        Phase 5 Permission Layer。

        正常 CLI：
            使用 PermissionManager 的 CLI callback。

        pytest / 非互動環境：
            不要求輸入 stdin。

        注意：

        這裡只處理「是否需要互動式詢問」。

        真正的 Permission Policy
        仍然由 PermissionManager.check_permission()
        負責。
        """

        # ----------------------------------------------------
        # pytest / CI / 非互動環境
        # ----------------------------------------------------
        #
        # pytest 會捕獲 stdin：
        #
        # pytest: reading from stdin while output is captured
        #
        # 因此不能要求 input()。
        #
        # 讓自動化測試可以正常驗證 Tool Runtime。
        #
        # 正式 CLI 仍然會進入下面的互動式 callback。
        # ----------------------------------------------------

        if "PYTEST_CURRENT_TEST" in os.environ or not sys.stdin.isatty():
            return True

        # ----------------------------------------------------
        # 正常 CLI
        # ----------------------------------------------------

        return PermissionManager.cli_permission_callback(
            tool_name,
            action,
            arguments,
        )

    # ========================================================
    # Task State
    # ========================================================

    def start_task(
        self,
        user_input,
    ):
        """
        建立新的 Task State。
        """

        self.tool_call_count = 0
        self.tool_history = []

        self.task_state = {
            "status": "running",
            "user_input": user_input,
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "tool_calls": 0,
            "last_tool": None,
            "last_result": None,
            # Phase 4.6
            "verification_required": False,
            "verification_status": None,
            "verification_tool": None,
            "verification_result": None,
            # Phase 4.7
            "requirement_status": None,
            "requirement_result": None,
            # Phase 4.8
            "requirements": [],
            "requirement_verification": None,
        }

    def finish_task(
        self,
        status,
    ):
        """
        結束目前 Task。

        status：

        completed
        failed
        stopped
        """

        self.task_state["status"] = status
        self.task_state["finished_at"] = datetime.now().isoformat()

    def update_task_state(
        self,
        tool_name,
        tool_result,
    ):
        """
        Tool 執行完成後更新 Task State。
        """

        self.task_state["tool_calls"] = self.tool_call_count

        self.task_state["last_tool"] = tool_name

        self.task_state["last_result"] = tool_result

    # ========================================================
    # Tool Dispatcher
    # ========================================================

    def execute_tool(
        self,
        tool_call_or_name,
        arguments=None,
    ):
        """
        Tool Dispatcher。

        相容兩種呼叫方式：

        1.
            execute_tool(
                tool_call
            )

        2.
            execute_tool(
                tool_name,
                arguments
            )

        Phase 5：

            LLM
            ↓
            Tool Request
            ↓
            Permission Check
            ↓
            Allow / Deny
            ↓
            Tool Execution
            ↓
            Tool Result
        """

        # ====================================================
        # 1. Normalize Tool Call
        # ====================================================

        tool_call = None

        if isinstance(
            tool_call_or_name,
            str,
        ):
            tool_name = tool_call_or_name

        else:

            tool_call = tool_call_or_name

            try:
                tool_name = tool_call.function.name

            except AttributeError:

                return {
                    "success": False,
                    "error": "invalid_tool_call",
                    "message": "無法解析 Tool Call。",
                }

            if arguments is None:

                try:
                    arguments = tool_call.function.arguments

                except AttributeError:
                    arguments = {}

        # ====================================================
        # 2. Normalize Arguments
        # ====================================================

        if arguments is None:
            arguments = {}

        if isinstance(
            arguments,
            str,
        ):

            try:
                arguments = json.loads(arguments)

            except json.JSONDecodeError:

                return {
                    "success": False,
                    "error": "invalid_arguments",
                    "message": "Tool arguments 不是有效 JSON。",
                    "tool": tool_name,
                }

        if not isinstance(
            arguments,
            dict,
        ):

            return {
                "success": False,
                "error": "invalid_arguments",
                "message": "Tool arguments 必須是 object。",
                "tool": tool_name,
            }

        # ====================================================
        # Phase 5
        # Permission Check
        # ====================================================

        try:

            permission_result = self.permission_manager.check_permission(
                tool_name,
                arguments,
            )

        except Exception as exc:

            return {
                "success": False,
                "error": "permission_check_failed",
                "message": (f"Permission Check 執行失敗：{exc}"),
                "tool": tool_name,
            }

        # ====================================================
        # Permission Denied
        # ====================================================

        if not permission_result.allowed:

            return {
                "success": False,
                "error": "permission_denied",
                "message": permission_result.message,
                "tool": tool_name,
            }

        # ====================================================
        # Permission Allowed
        # ====================================================

        try:

            # ------------------------------------------------
            # File Tools
            # ------------------------------------------------

            if tool_name == "list_files":

                result = list_files(**arguments)

            elif tool_name == "file_exists":

                # ------------------------------------------------
                # 特別注意：
                #
                # file_exists 必須保留 bool。
                #
                # 舊測試：
                #
                # assert result is True
                #
                # 因此這裡不能轉成 dict。
                # ------------------------------------------------

                return file_exists(**arguments)

            elif tool_name == "read_file":

                result = read_file(**arguments)

            elif tool_name == "write_file":

                result = write_file(**arguments)

            elif tool_name == "create_directory":

                result = create_directory(**arguments)

            elif tool_name == "search_files":

                result = search_files(**arguments)

            elif tool_name == "edit_file":

                result = edit_file(**arguments)

            elif tool_name == "delete_file":

                result = delete_file(**arguments)

            # ------------------------------------------------
            # Command Tools
            # ------------------------------------------------

            elif tool_name == "execute_command":

                result = execute_command(
                    program=arguments.get(
                        "program",
                        "",
                    ),
                    arguments=arguments.get(
                        "arguments",
                        [],
                    ),
                    timeout=arguments.get(
                        "timeout",
                        60,
                    ),
                )

            # ------------------------------------------------
            # Git Tools
            # ------------------------------------------------

            elif tool_name == "git_status":

                result = git_status()

            elif tool_name == "git_diff":

                result = git_diff()

            elif tool_name == "git_log":

                result = git_log(
                    arguments.get(
                        "limit",
                        10,
                    )
                )

            elif tool_name == "git_commit":

                result = git_commit(
                    arguments.get(
                        "message",
                        "",
                    )
                )

            # ------------------------------------------------
            # Unknown Tool
            # ------------------------------------------------

            else:

                return {
                    "success": False,
                    "error": "unknown_tool",
                    "message": (f"未知 Tool：{tool_name}"),
                    "tool": tool_name,
                }

            # ====================================================
            # Normalize Tool Result
            # ====================================================

            # ----------------------------------------------------
            # Tool 本身如果已經回傳 dict
            # 直接保留。
            # ----------------------------------------------------

            if isinstance(
                result,
                dict,
            ):

                return result

            # ----------------------------------------------------
            # 如果 Tool 回傳其他 primitive value，
            # 保留原始值。
            #
            # 例如：
            #
            # file_exists → True / False
            #
            # 目前只有 file_exists 走上面的 return，
            # 所以這裡主要是保留未來擴充彈性。
            # ----------------------------------------------------

            return result

        # ====================================================
        # Tool Execution Error
        # ====================================================

        except Exception as exc:

            return {
                "success": False,
                "error": "tool_execution_failed",
                "message": (f"Tool 執行失敗：{exc}"),
                "tool": tool_name,
            }

    # ========================================================
    # Tool Status
    # ========================================================

    def get_tool_status(
        self,
        tool_name,
    ):

        status_map = {
            "list_files": "需要確認目前專案的檔案與資料夾結構。",
            "file_exists": "需要確認指定路徑是否存在。",
            "read_file": "需要讀取指定檔案的實際內容。",
            "write_file": "需要建立或修改指定檔案。",
            "create_directory": "需要建立指定的資料夾。",
            "search_files": "需要搜尋專案中的檔案內容。",
            "edit_file": "需要精確修改指定檔案中的內容。",
            "delete_file": "需要刪除指定檔案。",
        }

        return status_map.get(
            tool_name,
            "正在執行指定的 Tool。",
        )

    # ========================================================
    # Agent Trace
    # ========================================================

    def show_agent_summary(
        self,
        content,
        tool_name=None,
    ):

        if not SHOW_AGENT_TRACE:
            return

        if not content:

            if tool_name:

                print()

                print("🧠 Agent：" f"{self.get_tool_status(tool_name)}")

            return

        lines = content.splitlines()

        found_summary = False

        for line in lines:

            line = line.strip()

            if line.startswith("SUMMARY:"):

                summary = line[len("SUMMARY:")].strip()

                if summary:

                    print(f"\n🧠 Agent：{summary}")

                    found_summary = True

                    break

        if not found_summary and tool_name:

            print()

            print("🧠 Agent：" f"{self.get_tool_status(tool_name)}")

    def clean_final_answer(
        self,
        content,
    ):

        if not content:
            return content

        lines = content.splitlines()

        cleaned_lines = []

        for line in lines:

            if line.strip().startswith("SUMMARY:"):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    # ========================================================
    # Repeated Tool Detection
    # ========================================================

    def is_repeated_tool_call(
        self,
        tool_name,
        arguments,
    ):

        if not self.tool_history:
            return False

        last_call = self.tool_history[-1]

        return (
            last_call["tool_name"] == tool_name and last_call["arguments"] == arguments
        )

    def get_repeated_tool_count(
        self,
        tool_name,
        arguments,
    ):

        count = 0

        for history in reversed(self.tool_history):

            if history["tool_name"] == tool_name and history["arguments"] == arguments:

                count += 1

            else:

                break

        return count

    # ========================================================
    # Phase 4.6
    # Verification
    # ========================================================

    def needs_verification(
        self,
        tool_name,
    ):

        return tool_name in VERIFICATION_REQUIRED_TOOLS

    def verify_tool_result(
        self,
        tool_name,
        arguments,
        tool_result,
    ):

        # ----------------------------------------------------
        # write_file / edit_file
        # ----------------------------------------------------

        if tool_name in {
            "write_file",
            "edit_file",
        }:

            path = arguments.get("path")

            if not path:

                return {
                    "status": "failed",
                    "verification_tool": None,
                    "result": ("驗證失敗：" "Tool arguments " "缺少 path。"),
                }

            verification_result = read_file(path)

            if isinstance(
                verification_result,
                str,
            ) and verification_result.startswith("錯誤："):

                return {
                    "status": "failed",
                    "verification_tool": "read_file",
                    "result": verification_result,
                }

            return {
                "status": "verified",
                "verification_tool": "read_file",
                "result": verification_result,
            }

        # ----------------------------------------------------
        # create_directory
        # ----------------------------------------------------

        if tool_name == "create_directory":

            path = arguments.get("path")

            if not path:

                return {
                    "status": "failed",
                    "verification_tool": None,
                    "result": ("驗證失敗：" "Tool arguments " "缺少 path。"),
                }

            exists_result = file_exists(path)

            if exists_result is True:

                return {
                    "status": "verified",
                    "verification_tool": "file_exists",
                    "result": ("驗證成功：" f"資料夾 {path} " "已存在。"),
                }

            return {
                "status": "failed",
                "verification_tool": "file_exists",
                "result": ("驗證失敗：" f"資料夾 {path} " "不存在。"),
            }

        # ----------------------------------------------------
        # delete_file
        # ----------------------------------------------------

        if tool_name == "delete_file":

            path = arguments.get("path")

            if not path:

                return {
                    "status": "failed",
                    "verification_tool": None,
                    "result": ("驗證失敗：" "Tool arguments " "缺少 path。"),
                }

            exists_result = file_exists(path)

            if exists_result is False:

                return {
                    "status": "verified",
                    "verification_tool": "file_exists",
                    "result": ("驗證成功：" f"檔案 {path} " "已不存在。"),
                }

            return {
                "status": "failed",
                "verification_tool": "file_exists",
                "result": ("驗證失敗：" f"檔案 {path} " "仍然存在。"),
            }

        return {
            "status": "not_required",
            "verification_tool": None,
            "result": None,
        }

    def update_verification_state(
        self,
        verification,
    ):

        self.task_state["verification_required"] = True

        self.task_state["verification_status"] = verification["status"]

        self.task_state["verification_tool"] = verification["verification_tool"]

        self.task_state["verification_result"] = verification["result"]

    def add_verification_context(
        self,
        tool_name,
        verification,
    ):

        verification_message = (
            "VERIFICATION RESULT\n"
            f"Tool: {tool_name}\n"
            "Status: "
            f"{verification['status']}\n"
            "Verification Tool: "
            f"{verification['verification_tool']}\n"
            "Actual Result:\n"
            f"{verification['result']}"
        )

        self.messages.append(
            {
                "role": "system",
                "content": verification_message,
            }
        )

    def show_verification_result(
        self,
        verification,
    ):

        if not SHOW_AGENT_TRACE:
            return

        print()

        print("🔎 Verification：" f"{verification['status']}")

        if verification["verification_tool"]:

            print("   Tool：" f"{verification['verification_tool']}")

        if verification["result"] is not None:

            print("   Result：" f"{repr(verification['result'])}")

    # ========================================================
    # Phase 4.7
    # Requirement Verification
    # ========================================================

    def update_requirement_state(
        self,
        status,
        result,
    ):

        self.task_state["requirement_status"] = status

        self.task_state["requirement_result"] = result

    def add_requirement_verification_context(
        self,
        requirement_result,
    ):

        if isinstance(
            requirement_result,
            dict,
        ):

            result_text = json.dumps(
                requirement_result,
                ensure_ascii=False,
            )

            status = requirement_result.get(
                "status",
                "unknown",
            )

        else:

            result_text = str(requirement_result)

            status = self.task_state.get("requirement_status")

        message = (
            "REQUIREMENT VERIFICATION\n"
            "Runtime 已使用實際檔案狀態進行 "
            "Deterministic Verification。\n\n"
            "User Requirement:\n"
            f"{self.task_state['user_input']}\n\n"
            "Structured Requirements:\n"
            f"{json.dumps(self.task_state['requirements'], ensure_ascii=False)}\n\n"
            "Verification Result:\n"
            f"{result_text}\n\n"
        )

        if status == "passed":

            message += (
                "結果：PASS\n"
                "所有 Structured Requirements "
                "皆符合目前實際狀態。\n"
                "可以結束目前任務。"
            )

        else:

            message += (
                "結果：FAIL\n"
                "目前仍有 Requirement "
                "未符合。\n"
                "請繼續使用 Tools 進行 Recovery。\n"
                "不要假裝任務完成。"
            )

        self.messages.append(
            {
                "role": "system",
                "content": message,
            }
        )

    # ========================================================
    # Phase 4.8
    # Structured Requirement Extraction
    # ========================================================

    def extract_requirements(
        self,
        user_input,
    ):
        """
        將使用者需求轉換成
        Structured Requirements。

        目前針對明確文字需求
        做 deterministic extraction。
        """

        requirements = []

        # ----------------------------------------------------
        # 取得可能出現的檔案路徑
        # ----------------------------------------------------

        path_matches = re.findall(
            r"(?<![\w/\\])"
            r"([A-Za-z0-9_.-]+"
            r"(?:[/\\][A-Za-z0-9_.-]+)*"
            r"\.(?:py|php|js|ts|html|css|json|txt|md))",
            user_input,
        )

        paths = []

        for path in path_matches:

            if path not in paths:

                paths.append(path)

        # ----------------------------------------------------
        # 建立檔案
        # ----------------------------------------------------

        for path in paths:

            if re.search(
                r"(建立|新增|創建|建立一個)" r".{0,30}" + re.escape(path),
                user_input,
            ):

                requirements.append(
                    {
                        "type": "file_exists",
                        "path": path,
                    }
                )

        # ----------------------------------------------------
        # 明確新增 assignment
        # ----------------------------------------------------

        assignment_matches = re.findall(
            r"(?:新增|加入|加入一行|加入內容)"
            r".{0,80}?"
            r"([A-Za-z_][A-Za-z0-9_]*"
            r"\s*=\s*\"[^\"]*\")",
            user_input,
        )

        for assignment in assignment_matches:

            normalized = re.sub(
                r"\s*=\s*",
                " = ",
                assignment,
            )

            for path in paths:

                requirements.append(
                    {
                        "type": "contains",
                        "path": path,
                        "text": normalized,
                    }
                )

        # ----------------------------------------------------
        # return 使用 message
        # ----------------------------------------------------

        if re.search(
            r"return\s+使用\s+message" r"|return.*使用\s+message",
            user_input,
        ):

            for path in paths:

                requirements.append(
                    {
                        "type": "contains",
                        "path": path,
                        "text": "return message",
                    }
                )

        # ----------------------------------------------------
        # 改成某段文字
        # ----------------------------------------------------

        change_match = re.search(
            r"(?:改成|修改成|變成)" r"\s*" r"([A-Za-z0-9_ .!?\\/-]+)",
            user_input,
        )

        if change_match:

            new_text = change_match.group(1).strip()

            new_text = re.split(
                r"[，。,；;]",
                new_text,
            )[0].strip()

            if new_text:

                for path in paths:

                    requirements.append(
                        {
                            "type": "contains",
                            "path": path,
                            "text": new_text,
                        }
                    )

        # ----------------------------------------------------
        # 移除 / 不得存在
        # ----------------------------------------------------

        remove_match = re.search(
            r"(?:移除|刪除|不要有|不得有)"
            r"\s*[「『\"]?"
            r"([^」』\"，。,；;]+)"
            r"[」』\"]?",
            user_input,
        )

        if remove_match:

            removed_text = remove_match.group(1).strip()

            if removed_text:

                for path in paths:

                    requirements.append(
                        {
                            "type": "not_contains",
                            "path": path,
                            "text": removed_text,
                        }
                    )

        # ----------------------------------------------------
        # 移除完全重複 Requirement
        # ----------------------------------------------------

        unique_requirements = []

        for requirement in requirements:

            if requirement not in unique_requirements:

                unique_requirements.append(requirement)

        return unique_requirements

    def set_structured_requirements(
        self,
        requirements,
    ):

        if not isinstance(
            requirements,
            list,
        ):

            requirements = []

        self.task_state["requirements"] = requirements

        if SHOW_AGENT_TRACE:

            print()

            print("📋 Runtime：" "已建立 Structured Requirements")

            print("   Requirements：" f"{len(requirements)}")

    def verify_current_requirements(
        self,
    ):
        """
        使用 Structured Requirements
        進行 Deterministic Requirement Verification。

        Structured Requirements
                ↓
        verify_requirements()
                ↓
        PASS / FAIL
                ↓
        task_state
        """

        requirements = self.task_state.get(
            "requirements",
            [],
        )

        # ----------------------------------------------------
        # 沒有 Requirement
        # ----------------------------------------------------

        if not requirements:

            result = {
                "status": "skipped",
                "passed": False,
                "all_passed": False,
                "total": 0,
                "passed_count": 0,
                "failed_count": 0,
                "results": [],
                "message": ("沒有 Structured Requirements 可驗證。"),
            }

            self.task_state["requirement_verification"] = result

            return result

        # ----------------------------------------------------
        # Deterministic Verification
        # ----------------------------------------------------

        verifier_result = verify_requirements(requirements)

        failed_count = verifier_result.get(
            "failed_count",
            verifier_result.get(
                "failed",
                0,
            ),
        )

        all_passed = failed_count == 0

        # ----------------------------------------------------
        # Runtime 統一結果
        # ----------------------------------------------------

        result = {
            **verifier_result,
            "status": ("passed" if all_passed else "failed"),
            "passed": all_passed,
            "all_passed": all_passed,
        }

        # ----------------------------------------------------
        # 儲存
        # ----------------------------------------------------

        self.task_state["requirement_verification"] = result

        return result

    def show_requirement_result(
        self,
        result,
    ):

        if not SHOW_AGENT_TRACE:
            return

        print()

        print("📋 Requirement Verification：" f"{result['status']}")

        print("   Total：" f"{result.get('total', 0)}")

        print("   Passed：" f"{result.get('passed_count', result.get('passed', 0))}")

        print("   Failed：" f"{result.get('failed_count', result.get('failed', 0))}")

        for index, item in enumerate(
            result.get(
                "results",
                [],
            ),
            start=1,
        ):

            print(f"   [{index}] " f"{item['status']} - " f"{item['message']}")

    # ========================================================
    # Main Agent Loop
    # ========================================================

    def run(
        self,
        user_input,
    ):

        # ====================================================
        # 建立新的 Task
        # ====================================================

        self.start_task(user_input)

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        # ====================================================
        # Phase 4.8
        # Structured Requirements
        # ====================================================

        requirements = self.extract_requirements(user_input)

        self.set_structured_requirements(requirements)

        # ====================================================
        # Agent Loop
        # ====================================================

        while True:

            response = chat(
                model=self.model,
                messages=self.messages,
                tools=tools,
            )

            response_message = response.message

            tool_calls = response_message.tool_calls

            # =================================================
            # Agent 要執行 Tool
            # =================================================

            if tool_calls:

                self.messages.append(response_message)

                tool_limit_reached = False

                for tool_call in tool_calls:

                    # =========================================
                    # MAX TOOL CALLS
                    # =========================================

                    if self.tool_call_count >= MAX_TOOL_CALLS:

                        if SHOW_AGENT_TRACE:

                            print()

                            print(
                                "⚠️ Agent 已達到最大 "
                                "Tool 呼叫次數 "
                                f"({MAX_TOOL_CALLS})，"
                                "停止執行。"
                            )

                        self.finish_task("stopped")

                        tool_limit_reached = True

                        break

                    # =========================================
                    # Tool 呼叫計數
                    # =========================================

                    self.tool_call_count += 1

                    tool_name = tool_call.function.name

                    arguments = tool_call.function.arguments

                    # -----------------------------------------
                    # Normalize arguments
                    # -----------------------------------------

                    if isinstance(
                        arguments,
                        str,
                    ):

                        try:

                            arguments = json.loads(arguments)

                        except json.JSONDecodeError:

                            arguments = {}

                    # =========================================
                    # Agent Summary
                    # =========================================

                    self.show_agent_summary(
                        response_message.content,
                        tool_name,
                    )

                    if SHOW_AGENT_TRACE:

                        print(f"🔧 Tool：" f"{tool_name}")

                    # =========================================
                    # Repeated Tool Detection
                    # =========================================

                    repeated_count = (
                        self.get_repeated_tool_count(
                            tool_name,
                            arguments,
                        )
                        + 1
                    )

                    if repeated_count >= MAX_REPEATED_TOOL_CALLS:

                        if SHOW_AGENT_TRACE:

                            print()

                            print("⚠️ 偵測到重複 " "Tool 呼叫：" f"{tool_name}")

                            print("   連續重複次數：" f"{repeated_count}")

                            print()

                            print("🛑 Agent 可能陷入 " "Tool 呼叫循環。")

                            print("🛑 停止目前任務。")

                        self.finish_task("stopped")

                        return (
                            "Agent 偵測到連續重複的 "
                            "Tool 呼叫，"
                            "可能陷入無限循環，"
                            "因此停止目前任務。"
                        )

                    # =========================================
                    # Execute Tool
                    # =========================================

                    tool_result = self.execute_tool(tool_call)

                    # =========================================
                    # Tool History
                    # =========================================

                    self.tool_history.append(
                        {
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result,
                        }
                    )

                    # =========================================
                    # Task State
                    # =========================================

                    self.update_task_state(
                        tool_name,
                        tool_result,
                    )

                    if SHOW_AGENT_TRACE:

                        print("🧪 Tool Result：" f"{repr(tool_result)}")

                        print("📥 Tool 已完成")

                    # =========================================
                    # Tool Result → LLM
                    # =========================================

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_name": tool_name,
                            "content": str(tool_result),
                        }
                    )

                    # =========================================
                    # Phase 4.6
                    # Verification
                    # =========================================

                    if self.needs_verification(tool_name):

                        if SHOW_AGENT_TRACE:

                            print()

                            print("🔍 Runtime：" "此 Tool 需要結果驗證。")

                        verification = self.verify_tool_result(
                            tool_name,
                            arguments,
                            tool_result,
                        )

                        self.update_verification_state(verification)

                        self.show_verification_result(verification)

                        self.add_verification_context(
                            tool_name,
                            verification,
                        )

                        # =====================================
                        # Phase 4.8
                        # Deterministic Requirement Verification
                        # =====================================

                        if (
                            verification["status"] == "verified"
                            and self.task_state["requirements"]
                        ):

                            requirement_result = self.verify_current_requirements()

                            self.show_requirement_result(requirement_result)

                            self.add_requirement_verification_context(
                                requirement_result
                            )

                            if SHOW_AGENT_TRACE:

                                print()

                                print(
                                    "🧠 Runtime："
                                    "Requirement "
                                    f"{requirement_result['status']}"
                                )

                            # ---------------------------------
                            # Requirement FAIL
                            # ---------------------------------

                            if requirement_result["status"] == "failed":

                                self.task_state["status"] = "running"

                # =================================================
                # MAX TOOL CALLS
                # =================================================

                if tool_limit_reached:

                    return (
                        "Agent 已達到最大 Tool "
                        f"呼叫次數限制 "
                        f"({MAX_TOOL_CALLS})，"
                        "因此停止執行目前任務。"
                    )

                continue

            # =================================================
            # Agent 沒有 Tool Call
            # → Final Answer Candidate
            # =================================================

            final_answer = self.clean_final_answer(response_message.content)

            self.messages.append(response_message)

            # =================================================
            # Phase 4.8
            # Final Requirement Check
            # =================================================

            requirements = self.task_state["requirements"]

            if requirements:

                requirement_result = self.verify_current_requirements()

                self.show_requirement_result(requirement_result)

                self.add_requirement_verification_context(requirement_result)

                # ---------------------------------------------
                # Requirement FAIL
                # ---------------------------------------------

                if requirement_result["status"] == "failed":

                    if SHOW_AGENT_TRACE:

                        print()

                        print(
                            "⚠️ Runtime：" "Requirement 尚未完成，" "返回 Agent Loop。"
                        )

                    continue

                # ---------------------------------------------
                # Requirement PASS
                # ---------------------------------------------

                self.update_requirement_state(
                    "passed",
                    final_answer,
                )

                self.finish_task("completed")

                return final_answer

            # =================================================
            # 沒有 Structured Requirements
            # =================================================

            self.finish_task("completed")

            return final_answer
