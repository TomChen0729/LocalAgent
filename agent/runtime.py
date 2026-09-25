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
    read_section,
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

from requirements.parser import (
    RequirementParser,
    RequirementParserError,
)

from requirements.specification import (
    TaskSpecification,
    OutputConstraints,
)
from requirements.specification_validator import (
    SpecificationValidator,
)
from requirements.output_verifier import (
    verify_output,
    count_words,
    detect_output_language,
)

from agent.permissions import PermissionManager
from agent.state import (
    create_task_state,
    start_task,
    finish_task,
    update_task_state,
)
from agent.tool_runner import ToolRunner
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

# ============================================================
# Agent Runtime Configuration
# ============================================================

MAX_TOOL_CALLS = 20

# 同一個 Tool + 完全相同 arguments
# 連續出現幾次後視為重複
MAX_REPEATED_TOOL_CALLS = 3

# Requirement Verification
#
# 當 Requirement 持續 FAIL，
# 但 Agent 沒有產生有效進展時，
# 最多允許幾次。
MAX_REQUIREMENT_FAILURES = 3

# Output Constraint Verification
#
# 當 Final Answer 持續不符合 Output Constraints，
# 最多允許幾次 Recovery。
MAX_OUTPUT_VERIFICATION_FAILURES = 3

# 需要在執行後進行驗證的 Tool
VERIFICATION_REQUIRED_TOOLS = {
    "write_file",
    "edit_file",
    "create_directory",
    "delete_file",
    "git_commit",
}


# ============================================================
# Phase 8.4
#
# 可能改變 Project State 的 Tool
# ============================================================

PROGRESS_MAKING_TOOLS = {
    "write_file",
    "edit_file",
    "create_directory",
    "delete_file",
    "git_commit",
    "execute_command",
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
        # Phase 8.2
        #
        # Requirement Parser
        # ----------------------------------------------------
        self.requirement_parser = RequirementParser(
            model=self.model,
        )
        # ----------------------------------------------------
        # Phase 8.6
        #
        # Specification Validator
        # ----------------------------------------------------
        self.specification_validator = SpecificationValidator()
        # ----------------------------------------------------
        # Phase 5
        #
        # Permission Manager
        # ----------------------------------------------------
        self.permission_manager = PermissionManager(
            permission_callback=self._permission_callback,
        )
        self.tool_runner = ToolRunner(
            tools=self._build_tool_registry(),
            permission_manager=self.permission_manager,
            constraint_checker=self.check_tool_constraints,
            constraint_result_handler=self.show_tool_constraint_result,
        )
        # ----------------------------------------------------
        # Phase 9.3
        #
        # Recovery Components
        # ----------------------------------------------------

        self.recovery_policy = RecoveryPolicy()

        self.recovery_selector = RecoverySelector()

        self.recovery_executor = RecoveryExecutor(
            self.tool_runner,
        )

        self.recovery_attempt_policy = RecoveryAttemptPolicy()

        self.recovery_argument_adapter = RecoveryArgumentAdapter()
        # ----------------------------------------------------
        # LLM Messages
        # ----------------------------------------------------
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
        self.task_state = create_task_state()

    def _build_tool_registry(self):
        """
        建立 Agent Tool Registry。

        使用 wrapper，而不是直接保存 module-level
        function reference。

        這樣可以保持：
        - Runtime 測試中的 monkeypatch
        - Tool replacement
        - Tool mocking
        - 未來 Tool 動態替換

        的相容性。
        """

        return {
            # -------------------------------------------------
            # File Tools
            # -------------------------------------------------
            "list_files": lambda **kwargs: list_files(**kwargs),
            "file_exists": lambda **kwargs: file_exists(**kwargs),
            "read_file": lambda **kwargs: read_file(**kwargs),
            "read_section": lambda **kwargs: read_section(**kwargs),
            "write_file": lambda **kwargs: write_file(**kwargs),
            "create_directory": lambda **kwargs: create_directory(**kwargs),
            "search_files": lambda **kwargs: search_files(**kwargs),
            "edit_file": lambda **kwargs: edit_file(**kwargs),
            "delete_file": lambda **kwargs: delete_file(**kwargs),
            # -------------------------------------------------
            # Command Tool
            # -------------------------------------------------
            "execute_command": self._execute_command_tool,
            # -------------------------------------------------
            # Git Tools
            # -------------------------------------------------
            "git_status": lambda **kwargs: git_status(),
            "git_diff": lambda **kwargs: git_diff(),
            "git_log": self._git_log_tool,
            "git_commit": self._git_commit_tool,
        }

    def _execute_command_tool(
        self,
        program="",
        arguments=None,
        timeout=60,
    ):
        """
        Command Tool Adapter。
        """

        if arguments is None:
            arguments = []

        return execute_command(
            program=program,
            arguments=arguments,
            timeout=timeout,
        )

    def _git_log_tool(
        self,
        limit=10,
    ):
        """
        Git Log Tool Adapter。
        """

        return git_log(limit)

    def _git_commit_tool(
        self,
        message="",
    ):
        """
        Git Commit Tool Adapter。
        """

        return git_commit(message)

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

        pytest / 非互動環境：
            不要求 stdin。

        正常 CLI：
            使用 PermissionManager CLI callback。
        """

        if "PYTEST_CURRENT_TEST" in os.environ or not sys.stdin.isatty():
            return True

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

        start_task(
            self.task_state,
            user_input,
        )

    def finish_task(
        self,
        status,
    ):
        """
        結束目前 Task。
        """

        finish_task(
            self.task_state,
            status,
        )

    def update_task_state(
        self,
        tool_name,
        tool_result,
    ):
        """
        Tool 執行完成後更新 Task State。
        """

        update_task_state(
            self.task_state,
            self.tool_call_count,
            tool_name,
            tool_result,
        )

    # ========================================================
    # Phase 8.2
    # Task Specification Parser
    # ========================================================

    def parse_task_specification(
        self,
        user_input,
    ):
        """
        使用 LLM Requirement Parser
        將 User Query 解析成 TaskSpecification。

        Parser 失敗時：
            fallback 到舊版 deterministic extraction。
        """

        try:

            specification = self.requirement_parser.parse(user_input)

        except RequirementParserError as exc:

            self.task_state["parser_status"] = "failed"
            self.task_state["parser_error"] = str(exc)
            self.task_state["task_specification"] = None

            if SHOW_AGENT_TRACE:

                print()
                print("⚠️ Runtime：LLM Requirement Parser 失敗。")
                print(f"   Error：{exc}")
                print("   Runtime：Fallback 到舊版 Deterministic Extraction。")

            return None

        except Exception as exc:

            self.task_state["parser_status"] = "failed"
            self.task_state["parser_error"] = str(exc)
            self.task_state["task_specification"] = None

            if SHOW_AGENT_TRACE:

                print()
                print("⚠️ Runtime：Requirement Parser 發生未預期錯誤。")
                print(f"   Error：{exc}")
                print("   Runtime：Fallback 到舊版 Deterministic Extraction。")

            return None

        # ----------------------------------------------------
        # Parser Success
        # ----------------------------------------------------

        if not isinstance(
            specification,
            TaskSpecification,
        ):

            self.task_state["parser_status"] = "failed"
            self.task_state["parser_error"] = (
                "Requirement Parser 回傳的結果不是 TaskSpecification。"
            )
            self.task_state["task_specification"] = None

            if SHOW_AGENT_TRACE:

                print()
                print("⚠️ Runtime：Requirement Parser 回傳格式錯誤。")
                print("   Runtime：Fallback 到舊版 Deterministic Extraction。")

            return None

        self.task_state["parser_status"] = "passed"
        self.task_state["parser_error"] = None
        self.task_state["task_specification"] = specification.to_dict()

        return specification

    def show_task_specification(
        self,
        specification,
    ):
        """
        顯示 Runtime 建立的 TaskSpecification。
        """

        if not SHOW_AGENT_TRACE:
            return

        if not isinstance(
            specification,
            TaskSpecification,
        ):
            return

        specification_dict = specification.to_dict()

        print()
        print("📋 Runtime：已建立 Task Specification")

        print(
            "   Objective："
            + json.dumps(
                specification_dict.get(
                    "objective",
                    {},
                ),
                ensure_ascii=False,
            )
        )

        print(
            "   Tool Constraints："
            + json.dumps(
                specification_dict.get(
                    "tool_constraints",
                    {},
                ),
                ensure_ascii=False,
            )
        )

        print(
            "   State Requirements："
            + json.dumps(
                specification_dict.get(
                    "state_requirements",
                    [],
                ),
                ensure_ascii=False,
            )
        )

        print(
            "   Output Constraints："
            + json.dumps(
                specification_dict.get(
                    "output_constraints",
                    {},
                ),
                ensure_ascii=False,
            )
        )

    # ========================================================
    # Phase 8.6
    # Specification Validation
    # ========================================================

    def validate_task_specification(
        self,
        specification,
    ):
        """
        Phase 8.6：

        使用 SpecificationValidator
        對 TaskSpecification 進行 Runtime Validation。

        Runtime 本身不負責重新實作 Specification
        的欄位驗證邏輯。

        Validation Authority：

            requirements/specification_validator.py

        Runtime 只負責：

            1. 呼叫 Validator
            2. 保存 Validation Result
            3. PASS → 繼續 Runtime
            4. FAIL → 停止 Task
        """

        # ----------------------------------------------------
        # 基本型別檢查
        # ----------------------------------------------------

        if not isinstance(
            specification,
            TaskSpecification,
        ):

            result = {
                "status": "failed",
                "passed": False,
                "failed": True,
                "errors": ["Runtime 收到的 Specification " "不是 TaskSpecification。"],
                "warnings": [],
                "checked": [],
            }

            self.task_state["specification_validation_status"] = "failed"

            self.task_state["specification_validation_result"] = result

            if SHOW_AGENT_TRACE:

                print()
                print("🛑 Runtime：" "Specification Validation FAIL")

                print("   Reason：" "Specification 型別錯誤。")
            self.finish_task("stopped")
            return result

        # ----------------------------------------------------
        # SpecificationValidator
        # ----------------------------------------------------

        try:

            result = self.specification_validator.validate(specification)

        except Exception as exc:

            result = {
                "status": "failed",
                "passed": False,
                "failed": True,
                "errors": ["Specification Validator " f"執行失敗：{exc}"],
                "warnings": [],
                "checked": [],
            }

        # ----------------------------------------------------
        # Normalize Result
        # ----------------------------------------------------

        if hasattr(
            result,
            "to_dict",
        ):

            result_data = result.to_dict()

        elif isinstance(
            result,
            dict,
        ):

            result_data = result

        else:

            result_data = {
                "status": "failed",
                "passed": False,
                "failed": True,
                "errors": ["Specification Validator " "回傳未知結果格式。"],
                "warnings": [],
                "checked": [],
            }

        # ----------------------------------------------------
        # Runtime State
        # ----------------------------------------------------

        validation_status = result_data.get(
            "status",
            "failed",
        )

        validation_passed = bool(
            result_data.get(
                "passed",
                validation_status == "passed",
            )
        )

        self.task_state["specification_validation_status"] = (
            "passed" if validation_passed else "failed"
        )

        self.task_state["specification_validation_result"] = result_data

        # ----------------------------------------------------
        # Trace
        # ----------------------------------------------------

        if SHOW_AGENT_TRACE:

            print()
            print(
                "🔐 Specification Validation："
                f"{self.task_state['specification_validation_status']}"
            )

            checked = result_data.get(
                "checked",
                [],
            )

            if checked:

                print("   Checked：" f"{', '.join(checked)}")

            warnings = result_data.get(
                "warnings",
                [],
            )

            if warnings:

                print("   Warnings：")

                for warning in warnings:

                    print(f"      - {warning}")

            errors = result_data.get(
                "errors",
                [],
            )

            if errors:

                print("   Errors：")

                for error in errors:

                    print(f"      - {error}")

        # ----------------------------------------------------
        # PASS
        # ----------------------------------------------------

        if validation_passed:

            return result_data

        # ----------------------------------------------------
        # FAIL
        #
        # Fail Closed
        #
        # 非法 Specification 不可以進入 Agent Loop。
        # ----------------------------------------------------

        self.finish_task("stopped")

        return result_data

    # ========================================================
    # Phase 8.3
    # Tool Constraints Enforcement
    # ========================================================

    def check_tool_constraints(
        self,
        tool_name,
    ):
        """
        檢查目前 TaskSpecification
        是否允許執行指定 Tool。
        """

        specification_data = self.task_state.get("task_specification")

        if not isinstance(
            specification_data,
            dict,
        ):
            return (
                True,
                "目前沒有 Task Tool Constraint。",
            )

        tool_constraints = specification_data.get(
            "tool_constraints",
            {},
        )

        if not isinstance(
            tool_constraints,
            dict,
        ):
            return (
                False,
                "Task Tool Constraint 格式錯誤：tool_constraints 必須是 object。",
            )

        allowed_tools = tool_constraints.get(
            "allowed_tools",
            [],
        )

        forbidden_tools = tool_constraints.get(
            "forbidden_tools",
            [],
        )

        if not isinstance(
            allowed_tools,
            list,
        ):
            return (
                False,
                "Task Tool Constraint 格式錯誤：allowed_tools 必須是 list。",
            )

        if not isinstance(
            forbidden_tools,
            list,
        ):
            return (
                False,
                "Task Tool Constraint 格式錯誤：forbidden_tools 必須是 list。",
            )

        # ----------------------------------------------------
        # Forbidden Tool
        # ----------------------------------------------------

        if tool_name in forbidden_tools:

            return (
                False,
                f"Tool '{tool_name}' 被目前 Task 的 forbidden_tools 禁止使用。",
            )

        # ----------------------------------------------------
        # Allowed Tool
        # ----------------------------------------------------

        if allowed_tools:

            if tool_name not in allowed_tools:

                return (
                    False,
                    (
                        f"Tool '{tool_name}' "
                        "不在目前 Task 的 allowed_tools 中，"
                        "因此禁止執行。"
                    ),
                )

        return (
            True,
            f"Tool '{tool_name}' 通過 Task Tool Constraint。",
        )

    def show_tool_constraint_result(
        self,
        tool_name,
        allowed,
        message,
    ):
        """
        顯示 Phase 8.3 Tool Constraint Trace。
        """

        if not SHOW_AGENT_TRACE:
            return

        print()

        if allowed:
            print("🛡️ Tool Constraint：" f"{tool_name} → ALLOWED")
        else:
            print("🛑 Tool Constraint：" f"{tool_name} → DENIED")

        print("   Reason：" f"{message}")

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

        Tool 的實際執行交由 ToolRunner。
        Runtime 保留 execute_tool() 作為對外介面，
        避免修改既有 Agent Loop 與測試。
        """

        return self.tool_runner.run(
            tool_call_or_name,
            arguments,
        )

    # ========================================================
    # Phase 9.3
    # Recovery Orchestration
    # ========================================================

    def attempt_tool_recovery(
        self,
        original_tool,
        arguments,
        tool_result,
    ):
        """
        嘗試針對 Tool Failure 執行 Alternative Tool Recovery。

        Runtime 只負責 orchestration：

            Failure Classification
                    ↓
            Recovery Policy
                    ↓
            Recovery Selection
                    ↓
            Recovery Attempt Control
                    ↓
            Argument Transformation
                    ↓
            Recovery Execution

        實際 Tool 執行仍然交給 ToolRunner。
        """

        # ----------------------------------------------------
        # 1. Failure Classification
        # ----------------------------------------------------

        classification = classify_failure(
            tool_result,
        )

        if SHOW_AGENT_TRACE:

            print()

            print(
                "🧭 Runtime："
                "Failure Classification"
            )

            print(
                "   Failed："
                f"{classification.failed}"
            )

            print(
                "   Category："
                f"{classification.category.value}"
            )

            print(
                "   Retryable："
                f"{classification.retryable}"
            )

        if not classification.failed:

            return {
                "recovered": False,
                "attempted": False,
                "original_tool": original_tool,
                "failure": classification.to_dict(),
                "reason": "Tool Result 沒有被判定為 Failure。",
            }

        failure_category = classification.category

        self.task_state["last_recovery_category"] = failure_category.value

        # ----------------------------------------------------
        # 2. Recovery Policy
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 3. Recovery Attempt Limit
        # ----------------------------------------------------

        attempt_count = self.task_state.get(
            "recovery_attempt_count",
            0,
        )

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

        # ----------------------------------------------------
        # 4. Select Alternative Tool
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 5. Transform Arguments
        # ----------------------------------------------------

        transformed = self.recovery_argument_adapter.transform(
            original_tool,
            alternative_tool,
            arguments,
        )

        # ----------------------------------------------------
        # 5.5 Validate Transformed Arguments
        # ----------------------------------------------------

        if not isinstance(
            transformed.transformed_arguments,
            dict,
        ):

            return {
                "recovered": False,
                "attempted": False,
                "original_tool": original_tool,
                "failure": classification.to_dict(),
                "recovery": decision.to_dict(),
                "selection": selection.to_dict(),
                "arguments": transformed.to_dict(),
                "reason": (
                    "Recovery Arguments Transformation "
                    "產生無效的 arguments。"
                ),
            }

        # ----------------------------------------------------
        # 6. Register Recovery Attempt
        # ----------------------------------------------------

        self.task_state["recovery_attempt_count"] = attempt_count + 1

        self.task_state["last_recovery_tool"] = alternative_tool

        # ----------------------------------------------------
        # 7. Execute Alternative Tool
        # ----------------------------------------------------

        execution = self.recovery_executor.execute(
            alternative_tool,
            transformed.transformed_arguments,
        )

        self.task_state["last_recovery_result"] = execution.to_dict()

        # ----------------------------------------------------
        # 8. Runtime Trace
        # ----------------------------------------------------

        if SHOW_AGENT_TRACE:

            print()
            print("♻️ Runtime：Tool Recovery")

            print("   Original Tool：" f"{original_tool}")

            print("   Failure Category：" f"{failure_category.value}")

            print("   Alternative Tool：" f"{alternative_tool}")

            print("   Arguments Changed：" f"{transformed.changed}")

            print("   Recovery Result：" f"{execution.success}")

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
            "read_section": "需要讀取指定檔案中的特定章節。",
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

                summary = line[len("SUMMARY:") :].strip()

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
                    "result": "驗證失敗：Tool arguments 缺少 path。",
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
                    "result": "驗證失敗：Tool arguments 缺少 path。",
                }

            exists_result = file_exists(path)

            if exists_result is True:

                return {
                    "status": "verified",
                    "verification_tool": "file_exists",
                    "result": (f"驗證成功：資料夾 {path} 已存在。"),
                }

            return {
                "status": "failed",
                "verification_tool": "file_exists",
                "result": (f"驗證失敗：資料夾 {path} 不存在。"),
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
                    "result": "驗證失敗：Tool arguments 缺少 path。",
                }

            exists_result = file_exists(path)

            if exists_result is False:

                return {
                    "status": "verified",
                    "verification_tool": "file_exists",
                    "result": (f"驗證成功：檔案 {path} 已不存在。"),
                }

            return {
                "status": "failed",
                "verification_tool": "file_exists",
                "result": (f"驗證失敗：檔案 {path} 仍然存在。"),
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
                "目前仍有 Requirement 未符合。\n"
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
        Parser Failure 時的 legacy fallback。
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
            r"\s*=\s*"
            r"\"[^\"]*\")",
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
            r"(?:改成|修改成|變成)" r"\s*" r"([A-Za-z0-9_ .!?/\\-]+)",
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
            print("📋 Runtime：已建立 Structured Requirements")

            print("   Requirements：" f"{len(requirements)}")

    def verify_current_requirements(
        self,
    ):
        """
        使用 Structured Requirements
        進行 Deterministic Requirement Verification。
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
                "message": "沒有 Structured Requirements 可驗證。",
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

        print(
            "   Passed："
            + str(
                result.get(
                    "passed_count",
                    result.get(
                        "passed",
                        0,
                    ),
                )
            )
        )

        print(
            "   Failed："
            + str(
                result.get(
                    "failed_count",
                    result.get(
                        "failed",
                        0,
                    ),
                )
            )
        )

        for index, item in enumerate(
            result.get(
                "results",
                [],
            ),
            start=1,
        ):

            print(f"   [{index}] " f"{item['status']} - " f"{item['message']}")

    # ========================================================
    # Phase 8.4
    # Requirement Failure / Progress Control
    # ========================================================

    def _requirement_result_signature(
        self,
        requirement_result,
    ):
        """
        建立 Requirement Verification
        的 deterministic signature。
        """

        try:

            return json.dumps(
                requirement_result,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )

        except Exception:

            return str(requirement_result)

    def reset_requirement_failure_state(
        self,
    ):

        self.task_state["requirement_failure_count"] = 0

        self.task_state["requirement_progress_since_failure"] = False

    def register_requirement_progress(
        self,
        tool_name,
        tool_result,
    ):
        """
        記錄 Requirement Recovery 是否產生進展。
        """

        if tool_name not in PROGRESS_MAKING_TOOLS:
            return

        tool_failed = False

        if isinstance(
            tool_result,
            dict,
        ):

            if tool_result.get("success") is False:

                tool_failed = True

            if tool_result.get("error"):

                tool_failed = True

        if tool_failed:
            return

        self.task_state["requirement_progress_since_failure"] = True

        if SHOW_AGENT_TRACE:

            print()
            print("📈 Runtime：" f"Tool '{tool_name}' " "被視為 Recovery Progress。")

    def handle_requirement_failure(
        self,
        requirement_result,
    ):
        """
        Phase 8.4：

        防止 Requirement FAIL 無限循環。
        """

        current_signature = self._requirement_result_signature(requirement_result)

        previous_signature = self.task_state.get("last_requirement_signature")

        has_state_change = (
            previous_signature is not None and previous_signature != current_signature
        )

        has_tool_progress = self.task_state.get(
            "requirement_progress_since_failure",
            False,
        )

        has_progress = has_tool_progress or has_state_change

        if has_progress:

            self.task_state["requirement_failure_count"] = 0

            if SHOW_AGENT_TRACE:

                print()
                print("📈 Runtime：" "Requirement FAIL，" "但偵測到有效進展。")

                if has_tool_progress:

                    print("   原因：" "Agent 執行了可能改變狀態的 Tool。")

                if has_state_change:

                    print("   原因：" "Requirement Verification " "實際結果發生變化。")

        else:

            self.task_state["requirement_failure_count"] += 1

            failure_count = self.task_state["requirement_failure_count"]

            if SHOW_AGENT_TRACE:

                print()
                print("⚠️ Runtime：" "Requirement FAIL 且目前沒有偵測到進展。")

                print(
                    "   Failure Count："
                    f"{failure_count}/"
                    f"{MAX_REQUIREMENT_FAILURES}"
                )

        self.task_state["last_requirement_signature"] = current_signature

        self.task_state["requirement_progress_since_failure"] = False

        failure_count = self.task_state["requirement_failure_count"]

        if failure_count >= MAX_REQUIREMENT_FAILURES:

            if SHOW_AGENT_TRACE:

                print()
                print("🛑 Runtime：" "Requirement 長時間沒有產生有效進展。")

                print("   已達到最大無進展失敗次數：" f"{MAX_REQUIREMENT_FAILURES}")

                print("🛑 Runtime：" "停止目前 Task，避免 Agent 無限循環。")

            self.finish_task("stopped")

            return False

        return True

    # ========================================================
    # Phase 8.5
    # Output Constraints
    # ========================================================

    def get_output_constraints(
        self,
    ):
        """
        取得目前 TaskSpecification 的
        Output Constraints。

        回傳 dict。

        如果沒有 Specification，
        回傳空 Constraint。
        """

        specification_data = self.task_state.get("task_specification")

        if not isinstance(
            specification_data,
            dict,
        ):
            return {}

        output_constraints = specification_data.get(
            "output_constraints",
            {},
        )

        if not isinstance(
            output_constraints,
            dict,
        ):
            return {}

        return output_constraints

    def has_active_output_constraints(
        self,
    ):
        """
        判斷目前是否真的存在
        需要 Enforcement 的 Output Constraint。

        language = "zh-TW"
        是 OutputConstraints 的預設值。

        預設值本身不代表 User 明確提出
        Language Constraint。

        因此：

            language == "zh-TW"
                → 不算 active

        只有：

            language != "zh-TW"
                → 才算 active
        """

        constraints = self.get_output_constraints()

        if not constraints:
            return False

        # ----------------------------------------------------
        # Semantic Constraints
        # ----------------------------------------------------

        if constraints.get(
            "parameter_names_only",
            False,
        ):
            return True

        if constraints.get(
            "no_analysis",
            False,
        ):
            return True

        if constraints.get(
            "no_suggestions",
            False,
        ):
            return True

        if constraints.get(
            "no_examples",
            False,
        ):
            return True

        # ----------------------------------------------------
        # max_words
        # ----------------------------------------------------

        if constraints.get("max_words") is not None:

            return True

        # ----------------------------------------------------
        # Language
        # ----------------------------------------------------

        language = constraints.get(
            "language",
            "zh-TW",
        )

        if language != "zh-TW":
            return True

        return False

    # --------------------------------------------------------
    # Compatibility Wrapper
    # --------------------------------------------------------

    def count_output_words(
        self,
        text,
    ):
        """
        相容舊版 Runtime API。

        實際 word counting
        已移至 requirements.output_verifier。
        """

        return count_words(text)

    # --------------------------------------------------------
    # Compatibility Wrapper
    # --------------------------------------------------------

    def detect_output_language(
        self,
        text,
    ):
        """
        相容舊版 Runtime API。

        實際 language detection
        已移至 requirements.output_verifier。
        """

        return detect_output_language(text)

    # --------------------------------------------------------
    # Deterministic Output Verification
    # --------------------------------------------------------

    def verify_output_constraints_deterministic(
        self,
        answer,
    ):
        """
        Phase 8.5：

        呼叫獨立的 Output Verifier
        進行 deterministic verification。

        Runtime 本身不負責：

        - 計算 word count
        - 判斷 suggestion
        - 判斷 example
        - language heuristic

        這些責任交給：

            requirements/output_verifier.py
        """

        constraints_data = self.get_output_constraints()

        # ----------------------------------------------------
        # 沒有 Output Constraints
        # ----------------------------------------------------

        if not constraints_data:

            return {
                "passed": True,
                "violations": [],
                "word_count": self.count_output_words(answer),
                "detected_language": (self.detect_output_language(answer)),
                "result": None,
            }

        # ----------------------------------------------------
        # Runtime dict
        # → OutputConstraints
        # ----------------------------------------------------

        try:

            constraints = OutputConstraints(
                parameter_names_only=bool(
                    constraints_data.get(
                        "parameter_names_only",
                        False,
                    )
                ),
                no_analysis=bool(
                    constraints_data.get(
                        "no_analysis",
                        False,
                    )
                ),
                no_suggestions=bool(
                    constraints_data.get(
                        "no_suggestions",
                        False,
                    )
                ),
                no_examples=bool(
                    constraints_data.get(
                        "no_examples",
                        False,
                    )
                ),
                max_words=constraints_data.get("max_words"),
                language=constraints_data.get(
                    "language",
                    "zh-TW",
                ),
            )

        except Exception as exc:

            return {
                "passed": False,
                "violations": [f"OutputConstraints 建立失敗：{exc}"],
                "word_count": self.count_output_words(answer),
                "detected_language": (self.detect_output_language(answer)),
                "result": None,
            }

        # ----------------------------------------------------
        # 真正交給 Output Verifier
        # ----------------------------------------------------

        verifier_result = verify_output(
            answer,
            constraints,
        )

        # ----------------------------------------------------
        # 建立 Runtime API 使用的 violations
        # ----------------------------------------------------

        violations = []

        for result in verifier_result.get(
            "results",
            [],
        ):

            if result.get("status") == "failed":

                constraint_name = result.get(
                    "constraint",
                    "unknown",
                )

                message = result.get(
                    "message",
                    "Output Constraint violation",
                )

                violations.append(f"{constraint_name}: {message}")

        return {
            "passed": verifier_result.get(
                "all_passed",
                False,
            ),
            "violations": violations,
            "word_count": self.count_output_words(answer),
            "detected_language": (self.detect_output_language(answer)),
            "result": verifier_result,
        }

    # --------------------------------------------------------
    # Semantic Output Verification
    # --------------------------------------------------------

    def verify_output_constraints_semantic(
        self,
        answer,
    ):
        """
        使用 Qwen 進行 Semantic Output Verification。

        驗證：

        - parameter_names_only
        - no_analysis
        - no_suggestions
        - no_examples

        Verifier 必須只輸出 JSON。

        注意：

        requirements/output_verifier.py
        不負責呼叫 LLM。

        Semantic Verification 屬於
        Agent Runtime 的 orchestration responsibility，
        因此保留在 Runtime。
        """

        constraints = self.get_output_constraints()

        semantic_constraints = {
            "parameter_names_only": bool(
                constraints.get(
                    "parameter_names_only",
                    False,
                )
            ),
            "no_analysis": bool(
                constraints.get(
                    "no_analysis",
                    False,
                )
            ),
            "no_suggestions": bool(
                constraints.get(
                    "no_suggestions",
                    False,
                )
            ),
            "no_examples": bool(
                constraints.get(
                    "no_examples",
                    False,
                )
            ),
        }

        # ----------------------------------------------------
        # 沒有 Semantic Constraint
        # ----------------------------------------------------

        if not any(semantic_constraints.values()):

            return {
                "passed": True,
                "violations": [],
                "reason": (
                    "目前沒有需要 Semantic " "Verification 的 Output Constraint。"
                ),
            }

        verifier_prompt = f"""
你是 LocalAgent 的 Output Constraint Verifier。

你的工作不是回答使用者問題。

你的工作是判斷「Agent 最終回答」
是否符合指定的輸出限制。

Output Constraints：

{json.dumps(
    semantic_constraints,
    ensure_ascii=False,
    indent=2,
)}

Agent Final Answer：

---BEGIN ANSWER---
{answer}
---END ANSWER---

請嚴格依照 Output Constraints 判斷。

規則：

1. parameter_names_only = true
   → 回答只能包含參數名稱或與參數名稱直接相關的必要資訊。
   → 不可以加入參數功能分析、使用方式、教學、解釋。

2. no_analysis = true
   → 不可以分析原因、優缺點、設計邏輯或推論。

3. no_suggestions = true
   → 不可以提出建議、推薦、改善方向或「可以考慮」。

4. no_examples = true
   → 不可以提供範例、sample、example 或示範內容。

如果沒有違反任何啟用中的 Constraint：

{{
  "passed": true,
  "violations": [],
  "reason": "符合所有 Output Constraints"
}}

如果有違反：

{{
  "passed": false,
  "violations": [
    "違反的 constraint"
  ],
  "reason": "簡短說明"
}}

只輸出 JSON。
不要輸出 Markdown。
不要輸出額外文字。
"""

        try:

            response = chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": verifier_prompt,
                    }
                ],
            )

            content = response.message.content if response.message else ""

            if not content:

                return {
                    "passed": False,
                    "violations": ["Semantic Verifier 沒有回傳結果。"],
                    "reason": "Verifier Empty Response",
                }

            # ------------------------------------------------
            # Remove Markdown Fence
            # ------------------------------------------------

            cleaned = content.strip()

            if cleaned.startswith("```json"):

                cleaned = cleaned[len("```json") :]

                if cleaned.endswith("```"):

                    cleaned = cleaned[:-3]

                cleaned = cleaned.strip()

            elif cleaned.startswith("```"):

                cleaned = cleaned[3:]

                if cleaned.endswith("```"):

                    cleaned = cleaned[:-3]

                cleaned = cleaned.strip()

            verifier_result = json.loads(cleaned)

            if not isinstance(
                verifier_result,
                dict,
            ):

                raise ValueError("Semantic Verifier 結果不是 object。")

            passed = bool(
                verifier_result.get(
                    "passed",
                    False,
                )
            )

            violations = verifier_result.get(
                "violations",
                [],
            )

            if not isinstance(
                violations,
                list,
            ):

                violations = [str(violations)]

            return {
                "passed": passed,
                "violations": violations,
                "reason": str(
                    verifier_result.get(
                        "reason",
                        "",
                    )
                ),
            }

        except Exception as exc:

            # ------------------------------------------------
            # Fail Closed
            # ------------------------------------------------

            return {
                "passed": False,
                "violations": ["Semantic Output Verification 執行失敗。"],
                "reason": (f"Verifier Error：{exc}"),
            }

    # --------------------------------------------------------
    # Combined Output Verification
    # --------------------------------------------------------

    def verify_output_constraints(
        self,
        answer,
    ):
        """
        Phase 8.5 完整 Output Verification。

        流程：

            Final Answer
                 ↓
            Deterministic
                 ↓
            Semantic
                 ↓
               PASS/FAIL
        """

        deterministic_result = self.verify_output_constraints_deterministic(answer)

        # ----------------------------------------------------
        # Deterministic FAIL
        #
        # 不需要再浪費一次 LLM Verifier。
        # ----------------------------------------------------

        if not deterministic_result["passed"]:

            result = {
                "passed": False,
                "status": "failed",
                "deterministic": (deterministic_result),
                "semantic": None,
                "violations": (deterministic_result["violations"]),
            }

            self.task_state["output_verification_status"] = "failed"

            self.task_state["output_verification_result"] = result

            return result

        # ----------------------------------------------------
        # Semantic Verification
        # ----------------------------------------------------

        semantic_result = self.verify_output_constraints_semantic(answer)

        violations = []

        violations.extend(
            semantic_result.get(
                "violations",
                [],
            )
        )

        passed = deterministic_result["passed"] and semantic_result["passed"]

        result = {
            "passed": passed,
            "status": ("passed" if passed else "failed"),
            "deterministic": (deterministic_result),
            "semantic": semantic_result,
            "violations": violations,
        }

        self.task_state["output_verification_status"] = result["status"]

        self.task_state["output_verification_result"] = result

        return result

    # --------------------------------------------------------
    # Output Verification Context
    # --------------------------------------------------------

    def add_output_verification_context(
        self,
        output_result,
    ):
        """
        將 Output Verification 結果
        回傳給 Agent。

        Agent 可以根據這個 Context
        重新產生符合限制的 Final Answer。
        """

        result_text = json.dumps(
            output_result,
            ensure_ascii=False,
            indent=2,
        )

        constraints_text = json.dumps(
            self.get_output_constraints(),
            ensure_ascii=False,
            indent=2,
        )

        message = (
            "OUTPUT CONSTRAINT VERIFICATION\n"
            "Runtime 已檢查 Agent Final Answer。\n\n"
            "Output Constraints:\n"
            f"{constraints_text}\n\n"
            "Verification Result:\n"
            f"{result_text}\n\n"
        )

        if output_result.get("passed"):

            message += "結果：PASS\n" "Final Answer 符合 Output Constraints。"

        else:

            message += (
                "結果：FAIL\n"
                "Final Answer 不符合 Output Constraints。\n"
                "請重新產生 Final Answer。\n"
                "不要忽略上述 Constraint。\n"
                "不要假裝原本的回答符合限制。"
            )

        self.messages.append(
            {
                "role": "system",
                "content": message,
            }
        )

    # --------------------------------------------------------
    # Output Verification Trace
    # --------------------------------------------------------

    def show_output_verification_result(
        self,
        result,
    ):

        if not SHOW_AGENT_TRACE:
            return

        print()

        print("📝 Output Constraint Verification：" f"{result['status']}")

        deterministic = result.get("deterministic") or {}

        if "word_count" in deterministic:

            print("   Word Count：" f"{deterministic['word_count']}")

        if deterministic.get("detected_language"):

            print("   Language：" f"{deterministic['detected_language']}")

        violations = result.get(
            "violations",
            [],
        )

        if violations:

            print("   Violations：")

            for violation in violations:

                print(f"      - {violation}")

    # --------------------------------------------------------
    # Output Failure Control
    # --------------------------------------------------------

    def handle_output_verification_failure(
        self,
        output_result,
    ):
        """
        防止 Output Constraint Verification
        無限 Recovery。

        FAIL
          ↓
        Recovery
          ↓
        FAIL
          ↓
        ...
          ↓
        3 次
          ↓
        STOP
        """

        self.task_state["output_verification_failure_count"] += 1

        failure_count = self.task_state["output_verification_failure_count"]

        if SHOW_AGENT_TRACE:

            print()

            print("⚠️ Runtime：" "Output Constraint Verification FAIL。")

            print(
                "   Failure Count："
                f"{failure_count}/"
                f"{MAX_OUTPUT_VERIFICATION_FAILURES}"
            )

        self.add_output_verification_context(output_result)

        if failure_count >= MAX_OUTPUT_VERIFICATION_FAILURES:

            if SHOW_AGENT_TRACE:

                print()

                print("🛑 Runtime：" "Output Constraint 長時間未符合。")

                print("🛑 Runtime：" "停止目前 Task，避免無限循環。")

            self.finish_task("stopped")

            return False

        return True

    def reset_output_verification_failure_state(
        self,
    ):

        self.task_state["output_verification_failure_count"] = 0

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
        # Phase 8.2
        # LLM Requirement Parser
        # ====================================================

        task_specification = self.parse_task_specification(user_input)

        if task_specification is not None:

            self.show_task_specification(task_specification)

            # ====================================================
            # Phase 8.6
            #
            # Specification Validation Gate
            # ====================================================

            specification_validation = self.validate_task_specification(
                task_specification
            )

            # ----------------------------------------------------
            # Specification Validation FAIL
            #
            # 不允許進入 Agent Loop。
            # ----------------------------------------------------

            if not specification_validation.get(
                "passed",
                False,
            ):

                errors = specification_validation.get(
                    "errors",
                    [],
                )

                if errors:

                    error_text = "; ".join(str(error) for error in errors)

                else:

                    error_text = "Task Specification " "未通過 Validation。"

                return (
                    "Agent 已停止目前任務："
                    "Task Specification "
                    "未通過 Specification Validation。"
                    f"\n原因：{error_text}"
                )

            # ----------------------------------------------------
            # Specification Validation PASS
            # ----------------------------------------------------

            requirements = task_specification.get_verifier_requirements()

            self.set_structured_requirements(requirements)

        else:

            # ------------------------------------------------
            # Parser Failure
            #
            # 保留原本 Phase 8.2 fallback。
            # ------------------------------------------------

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

                        print("🔧 Tool：" f"{tool_name}")

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

                            print("⚠️ 偵測到重複 Tool 呼叫：" f"{tool_name}")

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

                    # =========================================
                    # Phase 8.4
                    # Requirement Recovery Progress
                    # =========================================

                    if self.task_state["requirements"]:

                        self.register_requirement_progress(
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

                    # =================================================
                    # Phase 9.3
                    # Tool Failure Recovery
                    # =================================================
                    #
                    # 原始 Tool Failure
                    #       ↓
                    # Failure Classification
                    #       ↓
                    # Recovery Policy
                    #       ↓
                    # Recovery Selector
                    #       ↓
                    # Recovery Attempt Policy
                    #       ↓
                    # Recovery Argument Adapter
                    #       ↓
                    # Recovery Executor
                    #       ↓
                    # ToolRunner
                    #
                    # 注意：
                    # Recovery 不是取代原始 Tool Result。
                    #
                    # 原始 Tool Result 仍然保留在 LLM Context。
                    # Recovery Result 則額外加入 Context。
                    # =================================================

                    recovery_result = self.attempt_tool_recovery(
                        original_tool=tool_name,
                        arguments=arguments,
                        tool_result=tool_result,
                    )

                    # -------------------------------------------------
                    # Recovery Attempted
                    # -------------------------------------------------

                    if recovery_result.get("attempted"):

                        recovery_tool = recovery_result.get(
                            "execution",
                            {},
                        ).get("tool")

                        recovery_tool_arguments = recovery_result.get(
                            "arguments",
                            {},
                        ).get(
                            "transformed_arguments",
                            {},
                        )

                        recovery_execution = recovery_result.get(
                            "execution",
                            {},
                        )

                        recovery_tool_result = recovery_execution.get("result")

                        # ---------------------------------------------
                        # Recovery Tool History
                        # ---------------------------------------------

                        self.tool_history.append(
                            {
                                "tool_name": recovery_tool,
                                "arguments": recovery_tool_arguments,
                                "result": recovery_tool_result,
                                "recovery": True,
                                "original_tool": tool_name,
                            }
                        )

                        # ---------------------------------------------
                        # Recovery Task State
                        # ---------------------------------------------

                        self.update_task_state(
                            recovery_tool,
                            recovery_tool_result,
                        )

                        # ---------------------------------------------
                        # Recovery Progress
                        # ---------------------------------------------

                        if self.task_state["requirements"]:

                            self.register_requirement_progress(
                                recovery_tool,
                                recovery_tool_result,
                            )

                        # ---------------------------------------------
                        # Recovery Result → LLM
                        # ---------------------------------------------

                        recovery_message = (
                            "TOOL RECOVERY RESULT\n"
                            f"Original Tool: {tool_name}\n"
                            f"Original Tool Result:\n"
                            f"{tool_result}\n\n"
                            f"Recovery Tool: {recovery_tool}\n"
                            f"Recovery Result:\n"
                            f"{recovery_tool_result}\n\n"
                            f"Recovery Status: "
                            f"{'SUCCESS' if recovery_result.get('recovered') else 'FAILED'}"
                        )

                        self.messages.append(
                            {
                                "role": "system",
                                "content": recovery_message,
                            }
                        )

                        if SHOW_AGENT_TRACE:

                            print()

                            print("♻️ Runtime：" "Recovery 已加入 Agent Context")

                            print("   Recovery Tool：" f"{recovery_tool}")

                            print(
                                "   Recovery Status："
                                f"{'SUCCESS' if recovery_result.get('recovered') else 'FAILED'}"
                            )

                        # ---------------------------------------------
                        # Recovery Tool Verification
                        # ---------------------------------------------
                        #
                        # Recovery Tool 本身也必須遵守原本的
                        # Verification Pipeline。
                        #
                        # 例如：
                        #
                        # read_section 失敗
                        #      ↓
                        # read_file Recovery
                        #      ↓
                        # read_file 成功
                        #
                        # read_file 不需要 Verification，
                        # 所以直接繼續。
                        #
                        # 如果未來 Recovery Tool 是
                        # write_file / edit_file 等，
                        # 則會進入正常 Verification。
                        # ---------------------------------------------

                        if recovery_tool and self.needs_verification(recovery_tool):

                            if SHOW_AGENT_TRACE:

                                print()

                                print("🔍 Runtime：" "Recovery Tool 需要結果驗證。")

                            recovery_verification = self.verify_tool_result(
                                recovery_tool,
                                recovery_tool_arguments,
                                recovery_tool_result,
                            )

                            self.update_verification_state(recovery_verification)

                            self.show_verification_result(recovery_verification)

                            self.add_verification_context(
                                recovery_tool,
                                recovery_verification,
                            )

                            # -----------------------------------------
                            # Recovery Requirement Verification
                            # -----------------------------------------

                            if (
                                recovery_verification["status"] == "verified"
                                and self.task_state["requirements"]
                            ):

                                recovery_requirement_result = (
                                    self.verify_current_requirements()
                                )

                                self.show_requirement_result(
                                    recovery_requirement_result
                                )

                                self.add_requirement_verification_context(
                                    recovery_requirement_result
                                )

                                if SHOW_AGENT_TRACE:

                                    print()

                                    print(
                                        "🧠 Runtime："
                                        "Recovery Requirement "
                                        f"{recovery_requirement_result['status']}"
                                    )

                                if recovery_requirement_result["status"] == "failed":

                                    should_continue = self.handle_requirement_failure(
                                        recovery_requirement_result
                                    )

                                    if not should_continue:

                                        return (
                                            "Agent 已停止目前任務："
                                            "Recovery 後 Requirement "
                                            "仍持續未完成，"
                                            "且 Runtime 未偵測到有效進展，"
                                            "因此停止以避免無限循環。"
                                        )

                                else:

                                    self.reset_requirement_failure_state()

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

                        self.add_verification_context(tool_name, verification)

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

                                should_continue = self.handle_requirement_failure(
                                    requirement_result
                                )

                                if not should_continue:

                                    return (
                                        "Agent 已停止目前任務："
                                        "Requirement 持續未完成，"
                                        "且 Runtime 未偵測到有效進展，"
                                        "因此停止以避免無限循環。"
                                    )

                            # ---------------------------------
                            # Requirement PASS
                            # ---------------------------------

                            else:

                                self.reset_requirement_failure_state()

                # =================================================
                # MAX TOOL CALLS
                # =================================================

                if tool_limit_reached:

                    return (
                        "Agent 已達到最大 Tool "
                        "呼叫次數限制 "
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

                        print("⚠️ Runtime：" "Requirement 尚未完成。")

                    should_continue = self.handle_requirement_failure(
                        requirement_result
                    )

                    if not should_continue:

                        return (
                            "Agent 已停止目前任務："
                            "Requirement 持續未完成，"
                            "且 Runtime 未偵測到有效進展，"
                            "因此停止以避免無限循環。"
                        )

                    if SHOW_AGENT_TRACE:

                        print("   Runtime：" "返回 Agent Loop " "嘗試進行 Recovery。")

                    continue

                # ---------------------------------------------
                # Requirement PASS
                # ---------------------------------------------

                self.reset_requirement_failure_state()

                self.update_requirement_state(
                    "passed",
                    final_answer,
                )

            # =================================================
            # Phase 8.5
            #
            # Output Constraint Verification
            #
            # Final Answer
            #      ↓
            # output_verifier.py
            #      ↓
            # Deterministic PASS/FAIL
            #      ↓
            # Semantic Verification
            #      ↓
            # PASS / FAIL
            # =================================================

            if self.has_active_output_constraints():

                output_result = self.verify_output_constraints(final_answer)

                self.show_output_verification_result(output_result)

                # ---------------------------------------------
                # Output Constraint FAIL
                # ---------------------------------------------

                if not output_result["passed"]:

                    should_continue = self.handle_output_verification_failure(
                        output_result
                    )

                    if not should_continue:

                        return (
                            "Agent 已停止目前任務："
                            "Final Answer 持續不符合 "
                            "Output Constraints，"
                            "因此停止以避免無限循環。"
                        )

                    if SHOW_AGENT_TRACE:

                        print()

                        print(
                            "   Runtime："
                            "返回 Agent Loop，"
                            "要求 Agent 重新產生符合 "
                            "Output Constraints 的回答。"
                        )

                    continue

                # ---------------------------------------------
                # Output Constraint PASS
                # ---------------------------------------------

                self.reset_output_verification_failure_state()

            # =================================================
            # Final Answer PASS
            # =================================================

            self.finish_task("completed")

            return final_answer
