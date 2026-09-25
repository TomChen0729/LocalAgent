import json
from typing import Callable, Dict, Optional


class ToolRunner:
    """
    Tool Runner。

    負責：
    1. Normalize Tool Call
    2. Normalize Arguments
    3. Tool Constraint Check
    4. Permission Check
    5. Tool Dispatch
    6. Tool Exception Handling

    ToolRunner 必須維持原本
    AgentRuntime.execute_tool() 的回傳格式與行為。
    """

    def __init__(
        self,
        tools: Dict[str, Callable],
        permission_manager=None,
        constraint_checker: Optional[Callable] = None,
        constraint_result_handler: Optional[Callable] = None,
    ):
        self.tools = tools
        self.permission_manager = permission_manager
        self.constraint_checker = constraint_checker
        self.constraint_result_handler = constraint_result_handler

    # =========================================================
    # 1. Normalize Tool Call
    # =========================================================

    def normalize_tool_call(
        self,
        tool_call_or_name,
        arguments=None,
    ):
        """
        Normalize different Tool Call formats.

        支援：

        1. Tool name + arguments
        normalize_tool_call(
            "read_file",
            {"path": "README.md"}
        )

        2. Object-style Tool Call
        tool_call.function.name
        tool_call.function.arguments

        3. Dict-style Tool Call
        {
            "function": {
                "name": "read_file",
                "arguments": {
                    "path": "README.md"
                }
            }
        }
        """

        tool_name = None

        # ====================================================
        # 1. Tool name directly provided
        # ====================================================

        if isinstance(
            tool_call_or_name,
            str,
        ):

            tool_name = tool_call_or_name

        # ====================================================
        # 2. Dict-style Tool Call
        # ====================================================

        elif isinstance(
            tool_call_or_name,
            dict,
        ):

            tool_call = tool_call_or_name

            function = tool_call.get(
                "function",
            )

            if not isinstance(
                function,
                dict,
            ):

                return {
                    "success": False,
                    "error": "invalid_tool_call",
                    "message": "無法解析 Tool Call。",
                }

            tool_name = function.get(
                "name",
            )

            if arguments is None:

                arguments = function.get(
                    "arguments",
                    {},
                )

        # ====================================================
        # 3. Object-style Tool Call
        # ====================================================

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
        # 4. Validate Tool Name
        # ====================================================

        if not isinstance(
            tool_name,
            str,
        ) or not tool_name.strip():

            return {
                "success": False,
                "error": "invalid_tool_call",
                "message": "Tool Call 缺少有效的 Tool 名稱。",
            }

        # ====================================================
        # 5. Normalize Arguments
        # ====================================================

        if arguments is None:

            arguments = {}

        # Ollama / LLM 有時候會把 arguments 傳成 JSON string
        if isinstance(
            arguments,
            str,
        ):

            try:

                arguments = json.loads(
                    arguments,
                )

            except json.JSONDecodeError:

                return {
                    "success": False,
                    "error": "invalid_arguments",
                    "message": "Tool arguments 不是有效 JSON。",
                    "tool": tool_name,
                }

        # ====================================================
        # 6. Arguments must be dict
        # ====================================================

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
        # 7. Normalized Result
        # ====================================================

        return {
            "success": True,
            "tool": tool_name,
            "arguments": arguments,
        }



    # =========================================================
    # 2. Tool Constraint
    # =========================================================

    def check_tool_constraint(
        self,
        tool_name: str,
    ):
        """
        使用 Runtime 原本的 Tool Constraint 邏輯。

        不重新實作 Constraint，
        避免改變 Phase 8.3 行為。
        """

        if self.constraint_checker is None:
            return True, ""

        return self.constraint_checker(tool_name)

    # =========================================================
    # 3. Permission
    # =========================================================

    def check_permission(
        self,
        tool_name: str,
        arguments: dict,
    ):
        """
        使用既有 PermissionManager。
        """

        try:

            permission_result = self.permission_manager.check_permission(
                tool_name,
                arguments,
            )

        except Exception as exc:

            return {
                "success": False,
                "error": "permission_check_failed",
                "message": f"Permission Check 執行失敗：{exc}",
                "tool": tool_name,
            }

        if not permission_result.allowed:

            return {
                "success": False,
                "error": "permission_denied",
                "message": permission_result.message,
                "tool": tool_name,
            }

        return None

    # =========================================================
    # 4. Dispatch
    # =========================================================

    def dispatch(
        self,
        tool_name: str,
        arguments: dict,
    ):
        """
        執行實際 Tool。
        """

        if tool_name not in self.tools:

            return {
                "success": False,
                "error": "unknown_tool",
                "message": f"未知 Tool：{tool_name}",
                "tool": tool_name,
            }

        tool = self.tools[tool_name]

        try:

            return tool(**arguments)

        except Exception as exc:

            return {
                "success": False,
                "error": "tool_execution_failed",
                "message": f"Tool 執行失敗：{exc}",
                "tool": tool_name,
            }

    # =========================================================
    # 5. Main Runner
    # =========================================================

    def run(
        self,
        tool_call_or_name,
        arguments=None,
    ):
        """
        執行完整 Tool Pipeline：

        Normalize
            ↓
        Constraint
            ↓
        Permission
            ↓
        Dispatch
        """

        # -----------------------------------------------------
        # Normalize
        # -----------------------------------------------------

        normalized = self.normalize_tool_call(
            tool_call_or_name,
            arguments,
        )

        if not normalized["success"]:
            return normalized

        tool_name = normalized["tool"]
        arguments = normalized["arguments"]

        # -----------------------------------------------------
        # Tool Constraint
        # -----------------------------------------------------

        (
            constraint_allowed,
            constraint_message,
        ) = self.check_tool_constraint(
            tool_name,
        )

        if self.constraint_result_handler is not None:

            self.constraint_result_handler(
                tool_name,
                constraint_allowed,
                constraint_message,
            )

        if not constraint_allowed:

            return {
                "success": False,
                "error": "tool_constraint_denied",
                "message": constraint_message,
                "tool": tool_name,
            }

        # -----------------------------------------------------
        # Permission
        # -----------------------------------------------------

        permission_error = self.check_permission(
            tool_name,
            arguments,
        )

        if permission_error is not None:
            return permission_error

        # -----------------------------------------------------
        # Dispatch
        # -----------------------------------------------------

        return self.dispatch(
            tool_name,
            arguments,
        )
