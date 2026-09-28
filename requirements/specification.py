from dataclasses import dataclass, field
from typing import Any

SUPPORTED_REQUIREMENT_TYPES = {
    "file_exists",
    "contains",
    "not_contains",
}

SUPPORTED_OBJECTIVE_TYPES = {
    "inspect",
    "create",
    "modify",
    "delete",
    "execute",
    "git",
    "general",
}


@dataclass
class Objective:
    """
    描述使用者目前想完成的主要工作。
    """

    type: str = "general"
    target: str | None = None
    focus: str | None = None

    def validate(self) -> list[str]:
        errors = []

        if self.type not in SUPPORTED_OBJECTIVE_TYPES:
            errors.append(f"不支援的 objective type：{self.type}")

        if self.target is not None and not isinstance(
            self.target,
            str,
        ):
            errors.append("objective.target 必須是字串或 None。")

        if self.focus is not None and not isinstance(
            self.focus,
            str,
        ):
            errors.append("objective.focus 必須是字串或 None。")

        return errors


@dataclass
class ToolConstraints:
    """
    描述 Agent 可以或不可以使用哪些 Tools。
    """

    allowed_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors = []

        if not isinstance(self.allowed_tools, list):
            errors.append("allowed_tools 必須是 list。")

        if not isinstance(self.forbidden_tools, list):
            errors.append("forbidden_tools 必須是 list。")

        if isinstance(self.allowed_tools, list):
            for tool in self.allowed_tools:
                if not isinstance(tool, str):
                    errors.append("allowed_tools 中的項目必須是字串。")

        if isinstance(self.forbidden_tools, list):
            for tool in self.forbidden_tools:
                if not isinstance(tool, str):
                    errors.append("forbidden_tools 中的項目必須是字串。")

        if isinstance(self.allowed_tools, list) and isinstance(
            self.forbidden_tools, list
        ):
            overlap = set(self.allowed_tools) & set(self.forbidden_tools)

            if overlap:
                errors.append(
                    "同一個 Tool 不可以同時出現在 "
                    "allowed_tools 與 forbidden_tools："
                    f"{sorted(overlap)}"
                )

        return errors


@dataclass
class StateRequirement:
    """
    描述可以透過實際專案狀態驗證的 Requirement。

    這個結構與目前 verifier.py 的契約相容。
    """

    type: str
    path: str
    text: str | None = None

    def to_verifier_requirement(self) -> dict[str, Any]:
        """
        轉換成現有 requirements.verifier
        可以直接接受的 dict。
        """

        result = {
            "type": self.type,
            "path": self.path,
        }

        if self.text is not None:
            result["text"] = self.text

        return result

    def validate(self) -> list[str]:
        errors = []

        if self.type not in SUPPORTED_REQUIREMENT_TYPES:
            errors.append(f"不支援的 state requirement type：" f"{self.type}")

        if not isinstance(self.path, str) or not self.path.strip():
            errors.append("state requirement 的 path " "必須是非空字串。")

        if self.type in {
            "contains",
            "not_contains",
        }:
            if not isinstance(self.text, str):
                errors.append(f"{self.type} Requirement " "必須具有 text。")

        return errors


@dataclass
class OutputConstraints:
    """
    描述最終回答的格式與內容限制。
    """

    parameter_names_only: bool = False
    no_analysis: bool = False
    no_suggestions: bool = False
    no_examples: bool = False
    max_words: int | None = None
    language: str = "zh-TW"

    def validate(self) -> list[str]:
        errors = []

        boolean_fields = {
            "parameter_names_only": self.parameter_names_only,
            "no_analysis": self.no_analysis,
            "no_suggestions": self.no_suggestions,
            "no_examples": self.no_examples,
        }

        for field_name, value in boolean_fields.items():
            if not isinstance(value, bool):
                errors.append(f"{field_name} 必須是 boolean。")

        if self.max_words is not None:
            if not isinstance(self.max_words, int) or self.max_words <= 0:
                errors.append("max_words 必須是正整數或 None。")

        if not isinstance(self.language, str):
            errors.append("language 必須是字串。")

        return errors


@dataclass
class TaskSpecification:
    """
    使用者單一任務的結構化規格。

    LLM Parser 負責產生這個結構，
    Runtime 負責依照這個結構執行，
    Verifier 負責驗證實際狀態。
    """

    objective: Objective = field(default_factory=Objective)

    tool_constraints: ToolConstraints = field(default_factory=ToolConstraints)

    state_requirements: list[StateRequirement] = field(default_factory=list)

    output_constraints: OutputConstraints = field(default_factory=OutputConstraints)

    # Action Checklist：必須被「執行」的操作，由 Runtime 程式碼追蹤
    # 與 state_requirements（驗證檔案系統狀態）互補：
    #   state_requirements = "檔案系統應該長這樣"
    #   action_checklist   = "這些操作必須被執行過"
    action_checklist: list["ActionItem"] = field(default_factory=list)

    def validate(self) -> list[str]:
        """
        驗證整份 Task Specification。
        """

        errors = []

        errors.extend(self.objective.validate())

        errors.extend(self.tool_constraints.validate())

        if not isinstance(
            self.state_requirements,
            list,
        ):
            errors.append("state_requirements 必須是 list。")
        else:
            for index, requirement in enumerate(self.state_requirements):
                if not isinstance(
                    requirement,
                    StateRequirement,
                ):
                    errors.append(
                        f"state_requirements[{index}] " "必須是 StateRequirement。"
                    )
                    continue

                requirement_errors = requirement.validate()

                for error in requirement_errors:
                    errors.append(f"state_requirements[{index}]: " f"{error}")

        errors.extend(self.output_constraints.validate())

        return errors

    def is_valid(self) -> bool:
        return not self.validate()

    def get_verifier_requirements(
        self,
    ) -> list[dict[str, Any]]:
        """
        將 state_requirements 轉成目前
        verifier.py 使用的格式。
        """

        return [
            requirement.to_verifier_requirement()
            for requirement in self.state_requirements
        ]

    def get_pending_actions(self) -> list["ActionItem"]:
        """回傳尚未完成的 action items。"""
        return [item for item in self.action_checklist if not item.done]

    def mark_action_done(self, action_type: str) -> bool:
        """
        將第一個符合 action_type 且尚未完成的 item 標記為已完成。
        回傳是否有任何 item 被標記。
        """
        for item in self.action_checklist:
            if item.action_type == action_type and not item.done:
                item.done = True
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """
        將 TaskSpecification 轉成普通 dict。

        方便：
        - debug
        - log
        - 傳給 LLM
        - pytest 驗證
        """

        return {
            "objective": {
                "type": self.objective.type,
                "target": self.objective.target,
                "focus": self.objective.focus,
            },
            "tool_constraints": {
                "allowed_tools": (self.tool_constraints.allowed_tools),
                "forbidden_tools": (self.tool_constraints.forbidden_tools),
            },
            "state_requirements": [
                {
                    "type": requirement.type,
                    "path": requirement.path,
                    "text": requirement.text,
                }
                for requirement in self.state_requirements
            ],
            "output_constraints": {
                "parameter_names_only": (self.output_constraints.parameter_names_only),
                "no_analysis": (self.output_constraints.no_analysis),
                "no_suggestions": (self.output_constraints.no_suggestions),
                "no_examples": (self.output_constraints.no_examples),
                "max_words": (self.output_constraints.max_words),
                "language": (self.output_constraints.language),
            },
            "action_checklist": [
                {
                    "action_type": item.action_type,
                    "description": item.description,
                    "done": item.done,
                }
                for item in self.action_checklist
            ],
        }


# ============================================================
# ActionItem — 代表「必須被執行的操作」
#
# 與 StateRequirement 的差異：
#   StateRequirement = 驗證「檔案系統狀態」（是否存在、是否包含）
#   ActionItem       = 追蹤「操作是否執行過」（git commit、git push 等）
#
# action_type 到 tool 的對應：
#   "git_commit"     → tool: git_commit
#   "git_push"       → tool: git_run(subcommand=push)
#   "git_add"        → tool: git_run(subcommand=add)
#   "edit_file"      → tool: edit_file（target 為 path）
#   "write_file"     → tool: write_file（target 為 path）
#   "execute_command"→ tool: execute_command（target 為 program）
# ============================================================

SUPPORTED_ACTION_TYPES = {
    "git_commit",
    "git_push",
    "git_add",
    "edit_file",
    "write_file",
    "execute_command",
    "delete_file",
}


@dataclass
class ActionItem:
    """
    代表一個必須被執行的操作。
    Runtime 在每次 Tool Call 成功後更新 done 狀態。
    """

    action_type: str       # SUPPORTED_ACTION_TYPES 之一
    description: str       # 人類可讀的描述，顯示給使用者
    target: str | None = None   # 可選：檔案路徑或程式名稱，用於更精確的比對
    done: bool = False

    def validate(self) -> list[str]:
        errors = []
        if self.action_type not in SUPPORTED_ACTION_TYPES:
            errors.append(f"不支援的 action_type：{self.action_type}")
        if not isinstance(self.description, str) or not self.description.strip():
            errors.append("ActionItem description 必須是非空字串。")
        return errors

    def matches_tool_call(self, tool_name: str, arguments: dict) -> bool:
        """
        判斷一個 Tool Call 是否可以完成這個 ActionItem。
        """
        if self.action_type == "git_commit" and tool_name == "git_commit":
            return True
        if self.action_type == "git_push" and tool_name == "git_run":
            subcommand = str(arguments.get("subcommand", "")).lower()
            return subcommand == "push"
        if self.action_type == "git_add" and tool_name == "git_run":
            subcommand = str(arguments.get("subcommand", "")).lower()
            return subcommand == "add"
        if self.action_type == "edit_file" and tool_name == "edit_file":
            if self.target:
                path = str(arguments.get("path", ""))
                return self.target in path or path.endswith(self.target)
            return True
        if self.action_type == "write_file" and tool_name == "write_file":
            if self.target:
                path = str(arguments.get("path", ""))
                return self.target in path or path.endswith(self.target)
            return True
        if self.action_type == "execute_command" and tool_name == "execute_command":
            if self.target:
                program = str(arguments.get("program", "")).lower()
                return program == self.target.lower()
            return True
        if self.action_type == "delete_file" and tool_name == "delete_file":
            if self.target:
                path = str(arguments.get("path", ""))
                return self.target in path or path.endswith(self.target)
            return True
        return False
