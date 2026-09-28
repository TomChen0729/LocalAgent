"""
Specification Validator
=======================

Phase 8.6

負責對 TaskSpecification 進行
Deterministic Validation。

設計原則：

    RequirementParser
            ↓
      TaskSpecification
            ↓
    SpecificationValidator
            ↓
       PASS / FAIL
            ↓
        AgentRuntime

本模組：

1. 不呼叫 LLM
2. 不執行 Tool
3. 不修改 Project State
4. 不負責 Requirement Verification
5. 不負責 Output Verification

只負責確認：

    TaskSpecification
        ↓
    結構是否合法
    欄位是否合法
    型別是否合法
    值是否合法
    Constraint 是否一致
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

# ============================================================
# Validation Constants
# ============================================================

# ------------------------------------------------------------
# Objective
# ------------------------------------------------------------

ALLOWED_OBJECTIVE_TYPES = {
    "general",
    "inspect",
    "create",
    "modify",
    "delete",
    "execute",
    "git",
}


# ------------------------------------------------------------
# Tool Constraints
# ------------------------------------------------------------

TOOL_CONSTRAINT_KEYS = {
    "allowed_tools",
    "forbidden_tools",
}


# ------------------------------------------------------------
# Output Constraints
# ------------------------------------------------------------

OUTPUT_CONSTRAINT_KEYS = {
    "parameter_names_only",
    "no_analysis",
    "no_suggestions",
    "no_examples",
    "max_words",
    "language",
}


ALLOWED_OUTPUT_LANGUAGES = {
    "zh-TW",
    "en",
    "ja",
    "ko",
}


# ------------------------------------------------------------
# State Requirement
# ------------------------------------------------------------

ALLOWED_STATE_REQUIREMENT_TYPES = {
    "file_exists",
    # "file_not_exists",
    "contains",
    "not_contains",
}


# ============================================================
# Validation Result
# ============================================================


@dataclass
class SpecificationValidationResult:
    """
    TaskSpecification Validation Result。

    status:
        passed
        failed

    errors:
        所有 deterministic validation errors。

    warnings:
        不會直接阻止執行的問題。

    checked:
        實際檢查了哪些區塊。
    """

    status: str

    errors: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    checked: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "failed": self.failed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checked": list(self.checked),
        }


# ============================================================
# Validator
# ============================================================


class SpecificationValidator:
    """
    Phase 8.6 TaskSpecification Validator。

    使用方式：

        validator = SpecificationValidator()

        result = validator.validate(
            specification
        )

        if not result.passed:
            ...
    """

    # ========================================================
    # Public API
    # ========================================================

    def validate(
        self,
        specification,
    ) -> SpecificationValidationResult:
        """
        驗證 TaskSpecification。

        不直接 import TaskSpecification，
        避免 requirements.specification
        與 validator 產生循環依賴。

        因此採用 duck typing：

            hasattr(specification, "to_dict")

        或：

            dict
        """

        result = SpecificationValidationResult(status="passed")

        # ----------------------------------------------------
        # 1. Normalize Specification
        # ----------------------------------------------------

        specification_data = self._normalize_specification(
            specification,
            result,
        )

        if specification_data is None:

            result.status = "failed"

            return result

        # ----------------------------------------------------
        # 2. Validate Top-Level Structure
        # ----------------------------------------------------

        self._validate_top_level_structure(
            specification_data,
            result,
        )

        # ----------------------------------------------------
        # 3. Objective
        # ----------------------------------------------------

        self._validate_objective(
            specification_data,
            result,
        )

        # ----------------------------------------------------
        # 4. Tool Constraints
        # ----------------------------------------------------

        self._validate_tool_constraints(
            specification_data,
            result,
        )

        # ----------------------------------------------------
        # 5. State Requirements
        # ----------------------------------------------------

        self._validate_state_requirements(
            specification_data,
            result,
        )

        # ----------------------------------------------------
        # 6. Output Constraints
        # ----------------------------------------------------

        self._validate_output_constraints(
            specification_data,
            result,
        )

        # ----------------------------------------------------
        # 7. Cross-field Validation
        # ----------------------------------------------------

        self._validate_cross_constraints(
            specification_data,
            result,
        )

        # ----------------------------------------------------
        # Final Status
        # ----------------------------------------------------

        if result.errors:

            result.status = "failed"

        else:

            result.status = "passed"

        return result

    # ========================================================
    # Normalize
    # ========================================================

    def _normalize_specification(
        self,
        specification,
        result,
    ) -> Optional[Dict[str, Any]]:
        """
        將 TaskSpecification
        轉成 deterministic dict。

        支援：

            TaskSpecification
            dict

        不支援：

            None
            list
            string
            arbitrary object
        """

        if specification is None:

            result.errors.append("TaskSpecification 不可以是 None。")

            return None

        # ----------------------------------------------------
        # Dict
        # ----------------------------------------------------

        if isinstance(
            specification,
            dict,
        ):

            return specification

        # ----------------------------------------------------
        # TaskSpecification-like Object
        # ----------------------------------------------------

        to_dict = getattr(
            specification,
            "to_dict",
            None,
        )

        if callable(to_dict):

            try:

                data = to_dict()

            except Exception as exc:

                result.errors.append("TaskSpecification.to_dict() " f"執行失敗：{exc}")

                return None

            if not isinstance(
                data,
                dict,
            ):

                result.errors.append("TaskSpecification.to_dict() " "必須回傳 dict。")

                return None

            return data

        # ----------------------------------------------------
        # Invalid
        # ----------------------------------------------------

        result.errors.append(
            "Specification 必須是 dict " "或提供 to_dict() 的 TaskSpecification。"
        )

        return None

    # ========================================================
    # Top-Level Structure
    # ========================================================

    def _validate_top_level_structure(
        self,
        specification,
        result,
    ):
        """
        驗證 TaskSpecification 最外層結構。
        """

        result.checked.append("top_level")

        required_fields = {
            "objective",
            "tool_constraints",
            "state_requirements",
            "output_constraints",
        }

        for field_name in required_fields:

            if field_name not in specification:

                result.errors.append(f"缺少必要欄位：{field_name}")

        # ----------------------------------------------------
        # Top-level unknown fields
        #
        # 不直接 FAIL。
        #
        # 這是為了讓未來 Phase 擴充
        # TaskSpecification 時保持 backward compatible。
        # ----------------------------------------------------

        known_fields = required_fields | {
            "action_checklist",  # Phase 10: Action Checklist 功能
        }

        for field_name in specification:

            if field_name not in known_fields:

                result.warnings.append(
                    f"TaskSpecification 包含未知欄位：" f"{field_name}"
                )

    # ========================================================
    # Objective
    # ========================================================

    def _validate_objective(
        self,
        specification,
        result,
    ):
        """
        驗證：

            objective
                type
                target
                focus
        """

        result.checked.append("objective")

        if "objective" not in specification:

            return

        objective = specification.get("objective")

        if not isinstance(
            objective,
            dict,
        ):

            result.errors.append("objective 必須是 object。")

            return

        # ----------------------------------------------------
        # Required type
        # ----------------------------------------------------

        if "type" not in objective:

            result.errors.append("objective 缺少必要欄位：type")

        else:

            objective_type = objective.get("type")

            if not isinstance(
                objective_type,
                str,
            ):

                result.errors.append("objective.type 必須是 string。")

            elif not objective_type.strip():

                result.errors.append("objective.type 不可以是空字串。")

            elif objective_type not in ALLOWED_OBJECTIVE_TYPES:

                result.errors.append("objective.type 不支援：" f"{objective_type}")

        # ----------------------------------------------------
        # target
        # ----------------------------------------------------

        if "target" in objective:

            target = objective.get("target")

            if target is not None and not isinstance(
                target,
                str,
            ):

                result.errors.append("objective.target " "必須是 string 或 null。")

            elif (
                isinstance(
                    target,
                    str,
                )
                and not target.strip()
            ):

                result.errors.append("objective.target " "如果存在，不可以是空字串。")

        # ----------------------------------------------------
        # focus
        # ----------------------------------------------------

        if "focus" in objective:

            focus = objective.get("focus")

            if focus is not None and not isinstance(
                focus,
                str,
            ):

                result.errors.append("objective.focus " "必須是 string 或 null。")

    # ========================================================
    # Tool Constraints
    # ========================================================

    def _validate_tool_constraints(
        self,
        specification,
        result,
    ):
        """
        驗證：

            tool_constraints
                allowed_tools
                forbidden_tools
        """

        result.checked.append("tool_constraints")

        if "tool_constraints" not in specification:

            return

        constraints = specification.get("tool_constraints")

        if not isinstance(
            constraints,
            dict,
        ):

            result.errors.append("tool_constraints 必須是 object。")

            return

        # ----------------------------------------------------
        # allowed_tools
        # ----------------------------------------------------

        allowed_tools = constraints.get(
            "allowed_tools",
            [],
        )

        self._validate_tool_list(
            allowed_tools,
            "allowed_tools",
            result,
        )

        # ----------------------------------------------------
        # forbidden_tools
        # ----------------------------------------------------

        forbidden_tools = constraints.get(
            "forbidden_tools",
            [],
        )

        self._validate_tool_list(
            forbidden_tools,
            "forbidden_tools",
            result,
        )

        # ----------------------------------------------------
        # Intersection
        # ----------------------------------------------------

        if isinstance(
            allowed_tools,
            list,
        ) and isinstance(
            forbidden_tools,
            list,
        ):

            allowed_set = set(allowed_tools)

            forbidden_set = set(forbidden_tools)

            intersection = allowed_set & forbidden_set

            if intersection:

                result.errors.append(
                    "allowed_tools 與 "
                    "forbidden_tools 不可以同時包含：" + ", ".join(sorted(intersection))
                )

    def _validate_tool_list(
        self,
        tools,
        field_name,
        result,
    ):
        """
        驗證 Tool List。
        """

        if not isinstance(
            tools,
            list,
        ):

            result.errors.append(f"tool_constraints.{field_name} " "必須是 list。")

            return

        seen: Set[str] = set()

        for index, tool_name in enumerate(tools):

            if not isinstance(
                tool_name,
                str,
            ):

                result.errors.append(
                    f"tool_constraints." f"{field_name}[{index}] " "必須是 string。"
                )

                continue

            if not tool_name.strip():

                result.errors.append(
                    f"tool_constraints." f"{field_name}[{index}] " "不可以是空字串。"
                )

                continue

            if tool_name in seen:

                result.warnings.append(
                    f"tool_constraints." f"{field_name} " f"包含重複 Tool：{tool_name}"
                )

            seen.add(tool_name)

    # ========================================================
    # State Requirements
    # ========================================================

    def _validate_state_requirements(
        self,
        specification,
        result,
    ):
        """
        驗證：

            state_requirements

        目前支援：

            file_exists
            file_not_exists
            contains
            not_contains
        """

        result.checked.append("state_requirements")

        if "state_requirements" not in specification:

            return

        requirements = specification.get("state_requirements")

        if not isinstance(
            requirements,
            list,
        ):

            result.errors.append("state_requirements 必須是 list。")

            return

        for index, requirement in enumerate(requirements):

            self._validate_state_requirement(
                requirement,
                index,
                result,
            )

    def _validate_state_requirement(
        self,
        requirement,
        index,
        result,
    ):
        """
        驗證單一 State Requirement。
        """

        prefix = f"state_requirements[{index}]"

        if not isinstance(
            requirement,
            dict,
        ):

            result.errors.append(f"{prefix} 必須是 object。")

            return

        # ----------------------------------------------------
        # type
        # ----------------------------------------------------

        requirement_type = requirement.get("type")

        if requirement_type is None:

            result.errors.append(f"{prefix} 缺少必要欄位：type")

            return

        if not isinstance(
            requirement_type,
            str,
        ):

            result.errors.append(f"{prefix}.type 必須是 string。")

            return

        if requirement_type not in (ALLOWED_STATE_REQUIREMENT_TYPES):

            result.errors.append(f"{prefix}.type 不支援：" f"{requirement_type}")

            return

        # ----------------------------------------------------
        # path
        # ----------------------------------------------------

        path = requirement.get("path")

        if path is None:

            result.errors.append(f"{prefix} 缺少必要欄位：path")

        elif not isinstance(
            path,
            str,
        ):

            result.errors.append(f"{prefix}.path 必須是 string。")

        elif not path.strip():

            result.errors.append(f"{prefix}.path 不可以是空字串。")

        # ----------------------------------------------------
        # contains / not_contains
        # ----------------------------------------------------

        if requirement_type in {
            "contains",
            "not_contains",
        }:

            text = requirement.get("text")

            if text is None:

                result.errors.append(f"{prefix} 缺少必要欄位：text")

            elif not isinstance(
                text,
                str,
            ):

                result.errors.append(f"{prefix}.text 必須是 string。")

            elif not text:

                result.errors.append(f"{prefix}.text 不可以是空字串。")

    # ========================================================
    # Output Constraints
    # ========================================================

    def _validate_output_constraints(
        self,
        specification,
        result,
    ):
        """
        驗證：

            output_constraints

        支援：

            parameter_names_only
            no_analysis
            no_suggestions
            no_examples
            max_words
            language
        """

        result.checked.append("output_constraints")

        if "output_constraints" not in specification:

            return

        constraints = specification.get("output_constraints")

        if not isinstance(
            constraints,
            dict,
        ):

            result.errors.append("output_constraints " "必須是 object。")

            return

        # ----------------------------------------------------
        # Boolean Constraints
        # ----------------------------------------------------

        boolean_fields = {
            "parameter_names_only",
            "no_analysis",
            "no_suggestions",
            "no_examples",
        }

        for field_name in boolean_fields:

            if field_name not in constraints:

                continue

            value = constraints.get(field_name)

            if not isinstance(
                value,
                bool,
            ):

                result.errors.append(
                    f"output_constraints." f"{field_name} " "必須是 boolean。"
                )

        # ----------------------------------------------------
        # max_words
        # ----------------------------------------------------

        if "max_words" in constraints:

            max_words = constraints.get("max_words")

            if max_words is not None:

                if isinstance(
                    max_words,
                    bool,
                ):

                    result.errors.append(
                        "output_constraints." "max_words " "不可以是 boolean。"
                    )

                elif not isinstance(
                    max_words,
                    int,
                ):

                    result.errors.append(
                        "output_constraints." "max_words " "必須是 integer 或 null。"
                    )

                elif max_words <= 0:

                    result.errors.append(
                        "output_constraints." "max_words " "必須大於 0。"
                    )

        # ----------------------------------------------------
        # language
        # ----------------------------------------------------

        if "language" in constraints:

            language = constraints.get("language")

            if not isinstance(
                language,
                str,
            ):

                result.errors.append(
                    "output_constraints." "language " "必須是 string。"
                )

            elif not language.strip():

                result.errors.append(
                    "output_constraints." "language " "不可以是空字串。"
                )

            elif language not in ALLOWED_OUTPUT_LANGUAGES:

                result.errors.append(
                    "output_constraints." "language " f"不支援：{language}"
                )

    # ========================================================
    # Cross Constraint Validation
    # ========================================================

    def _validate_cross_constraints(
        self,
        specification,
        result,
    ):
        """
        驗證不同 Specification 區塊
        之間的邏輯一致性。
        """

        result.checked.append("cross_constraints")

        objective = specification.get(
            "objective",
            {},
        )

        tool_constraints = specification.get(
            "tool_constraints",
            {},
        )

        state_requirements = specification.get(
            "state_requirements",
            [],
        )

        output_constraints = specification.get(
            "output_constraints",
            {},
        )

        # ----------------------------------------------------
        # Defensive Type Check
        # ----------------------------------------------------

        if not isinstance(
            objective,
            dict,
        ):

            return

        if not isinstance(
            tool_constraints,
            dict,
        ):

            return

        if not isinstance(
            state_requirements,
            list,
        ):

            return

        if not isinstance(
            output_constraints,
            dict,
        ):

            return

        objective_type = objective.get("type")

        allowed_tools = tool_constraints.get(
            "allowed_tools",
            [],
        )

        forbidden_tools = tool_constraints.get(
            "forbidden_tools",
            [],
        )

        # ----------------------------------------------------
        # inspect Objective
        #
        # inspect 通常需要讀取能力。
        #
        # 如果 User 明確限制 allowed_tools，
        # 而 read_file 完全不在允許清單，
        # 這是一個 specification-level
        # inconsistency。
        #
        # 但不直接 FAIL。
        #
        # 因為 Agent 可能使用其他合法 Tool。
        # ----------------------------------------------------

        if (
            objective_type == "inspect"
            and isinstance(
                allowed_tools,
                list,
            )
            and allowed_tools
            and "read_file" not in allowed_tools
            and "list_files" not in allowed_tools
            and "search_files" not in allowed_tools
        ):

            result.warnings.append(
                "objective=inspect，但 "
                "allowed_tools 沒有 read_file、"
                "list_files 或 search_files。"
            )

        # ----------------------------------------------------
        # State Requirements 與 Tool Constraints
        #
        # 如果 Requirement 需要修改檔案，
        # 但 allowed_tools 完全禁止修改，
        # 會造成不可完成的 Specification。
        # ----------------------------------------------------

        modifying_tools = {
            "write_file",
            "edit_file",
            "delete_file",
            "create_directory",
            "execute_command",
            "git_commit",
        }

        has_mutating_requirement = False

        for requirement in state_requirements:

            if not isinstance(
                requirement,
                dict,
            ):
                continue

            requirement_type = requirement.get("type")

            if requirement_type in {
                "file_exists",
                # "file_not_exists",
                "contains",
                "not_contains",
            }:

                has_mutating_requirement = True

        if (
            has_mutating_requirement
            and isinstance(
                allowed_tools,
                list,
            )
            and allowed_tools
            and not (set(allowed_tools) & modifying_tools)
        ):

            result.warnings.append(
                "State Requirements 可能需要 "
                "Project State 改變，但 "
                "allowed_tools 沒有任何可能修改狀態的 Tool。"
            )

        # ----------------------------------------------------
        # Explicitly Forbidden Tool
        #
        # allowed / forbidden conflict
        # 已在 Tool Constraint validation
        # 處理。
        # ----------------------------------------------------

        if isinstance(
            allowed_tools,
            list,
        ) and isinstance(
            forbidden_tools,
            list,
        ):

            conflict = set(allowed_tools) & set(forbidden_tools)

            if conflict:

                # 這裡不重複產生 error。
                pass

        # ----------------------------------------------------
        # parameter_names_only
        #
        # 這個 Constraint 本身不要求
        # no_analysis 等必須為 True。
        #
        # Runtime 的 Semantic Verifier
        # 會各自處理。
        # ----------------------------------------------------

        if output_constraints.get(
            "parameter_names_only",
            False,
        ):

            if output_constraints.get("max_words") is not None:

                max_words = output_constraints.get("max_words")

                if (
                    isinstance(
                        max_words,
                        int,
                    )
                    and max_words < 1
                ):

                    result.errors.append(
                        "parameter_names_only 啟用時，" "max_words 必須大於 0。"
                    )

    # ========================================================
    # Convenience API
    # ========================================================


def validate_specification(
    specification,
) -> SpecificationValidationResult:
    """
    Functional API。

    方便 Runtime / Tests 直接呼叫：

        result = validate_specification(
            specification
        )
    """

    validator = SpecificationValidator()

    return validator.validate(specification)


# ============================================================
# Public Exports
# ============================================================

__all__ = [
    "SpecificationValidationResult",
    "SpecificationValidator",
    "validate_specification",
    "ALLOWED_OBJECTIVE_TYPES",
    "ALLOWED_OUTPUT_LANGUAGES",
    "ALLOWED_STATE_REQUIREMENT_TYPES",
]
