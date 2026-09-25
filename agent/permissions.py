from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class PermissionResult:
    """
    Permission 檢查結果。
    """

    allowed: bool
    action: str
    message: str


class PermissionManager:
    """
    LocalAgent Permission Layer。

    負責在 Tool 真正執行以前，
    判斷目前 Tool 是否允許執行。

    Permission Policy：

        read
            → 自動允許

        write
            → 詢問使用者

        edit
            → 詢問使用者

        delete
            → 明確確認

        commit
            → 詢問使用者

        execute
            → 詢問使用者
    """

    TOOL_ACTIONS = {
        "list_files": "read",
        "file_exists": "read",
        "read_file": "read",
        "search_files": "read",
        "read_section": "read",
        "write_file": "write",
        "edit_file": "edit",
        "create_directory": "write",
        "delete_file": "delete",
        "git_status": "read",
        "git_diff": "read",
        "git_log": "read",
        "git_commit": "commit",
        "execute_command": "execute",
    }

    def __init__(
        self,
        permission_callback: Optional[Callable[[str, str, dict], bool]] = None,
        auto_approve: bool = False,
    ):
        """
        Parameters
        ----------
        permission_callback:
            當需要詢問使用者時使用的 callback。

        auto_approve:
            測試環境可以設定 True，
            讓 Permission Layer 自動允許。
        """

        self.permission_callback = permission_callback
        self.auto_approve = auto_approve

        self.history = []

    # --------------------------------------------------
    # Tool → Permission Mapping
    # --------------------------------------------------

    def get_action(self, tool_name: str) -> Optional[str]:
        """
        取得 Tool 對應的 Permission Action。
        """

        return self.TOOL_ACTIONS.get(tool_name)

    # --------------------------------------------------
    # Permission Check
    # --------------------------------------------------

    def check_permission(
        self,
        tool_name: str,
        arguments: dict,
    ) -> PermissionResult:
        """
        檢查目前 Tool 是否可以執行。
        """

        action = self.get_action(tool_name)

        # --------------------------------------------------
        # Unknown Tool
        # --------------------------------------------------

        if action is None:
            result = PermissionResult(
                allowed=False,
                action="unknown",
                message=(
                    f"Tool '{tool_name}' 沒有設定 Permission Policy，" "因此禁止執行。"
                ),
            )

            self._record(
                tool_name,
                action,
                arguments,
                result,
            )

            return result

        # --------------------------------------------------
        # Read
        # --------------------------------------------------

        if action == "read":
            result = PermissionResult(
                allowed=True,
                action=action,
                message=(f"Tool '{tool_name}' 屬於 read 操作，" "自動允許。"),
            )

            self._record(
                tool_name,
                action,
                arguments,
                result,
            )

            return result

        # --------------------------------------------------
        # Test Mode
        # --------------------------------------------------

        if self.auto_approve:
            result = PermissionResult(
                allowed=True,
                action=action,
                message=(
                    f"Tool '{tool_name}' 屬於 {action} 操作，"
                    "目前為 auto_approve 模式，因此允許。"
                ),
            )

            self._record(
                tool_name,
                action,
                arguments,
                result,
            )

            return result

        # --------------------------------------------------
        # Ask User
        # --------------------------------------------------

        if self.permission_callback is not None:
            try:
                allowed = bool(
                    self.permission_callback(
                        tool_name,
                        action,
                        arguments,
                    )
                )

            except Exception as exc:
                result = PermissionResult(
                    allowed=False,
                    action=action,
                    message=(f"Permission callback 執行失敗：{exc}"),
                )

                self._record(
                    tool_name,
                    action,
                    arguments,
                    result,
                )

                return result

            if allowed:
                result = PermissionResult(
                    allowed=True,
                    action=action,
                    message=(f"使用者允許 Tool '{tool_name}' " f"執行 {action} 操作。"),
                )
            else:
                result = PermissionResult(
                    allowed=False,
                    action=action,
                    message=(f"使用者拒絕 Tool '{tool_name}' " f"執行 {action} 操作。"),
                )

            self._record(
                tool_name,
                action,
                arguments,
                result,
            )

            return result

        # --------------------------------------------------
        # No Callback
        # --------------------------------------------------

        result = PermissionResult(
            allowed=False,
            action=action,
            message=(
                f"Tool '{tool_name}' 需要使用者確認，"
                "但目前沒有 Permission callback，"
                "因此禁止執行。"
            ),
        )

        self._record(
            tool_name,
            action,
            arguments,
            result,
        )

        return result

    # --------------------------------------------------
    # CLI Permission Callback
    # --------------------------------------------------

    @staticmethod
    def cli_permission_callback(
        tool_name: str,
        action: str,
        arguments: dict,
    ) -> bool:
        """
        CLI 環境使用的 Permission Callback。

        讓使用者直接在終端機確認。
        """

        print()
        print("=" * 60)
        print("Permission Request")
        print("=" * 60)

        print(f"Tool   : {tool_name}")
        print(f"Action : {action}")
        print(f"Args   : {arguments}")

        print()

        if action == "delete":
            print("⚠️ 這是 DELETE 操作。")

            answer = input("確定要執行刪除操作嗎？請輸入 DELETE：")

            return answer.strip() == "DELETE"

        answer = input("是否允許此操作？(y/N)：")

        return answer.strip().lower() in {
            "y",
            "yes",
        }

    # --------------------------------------------------
    # History
    # --------------------------------------------------

    def _record(
        self,
        tool_name: str,
        action: Optional[str],
        arguments: dict,
        result: PermissionResult,
    ):
        self.history.append(
            {
                "tool": tool_name,
                "action": action,
                "arguments": arguments,
                "allowed": result.allowed,
                "message": result.message,
            }
        )

    def get_history(self):
        """
        取得 Permission History。
        """

        return list(self.history)

    def clear_history(self):
        """
        清除 Permission History。
        """

        self.history.clear()
