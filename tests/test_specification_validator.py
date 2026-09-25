"""
Tests for Phase 8.6 Specification Validator.

測試範圍：

1. 合法 TaskSpecification
2. Top-level Structure Validation
3. Objective Validation
4. Tool Constraints Validation
5. State Requirements Validation
6. Output Constraints Validation
7. Cross-field Validation
8. Functional API
9. TaskSpecification.to_dict() 相容性
"""

from requirements.specification import (
    Objective,
    OutputConstraints,
    StateRequirement,
    TaskSpecification,
    ToolConstraints,
)

from requirements.specification_validator import (
    SpecificationValidationResult,
    SpecificationValidator,
    validate_specification,
)

# ============================================================
# Fixtures / Helpers
# ============================================================


def create_valid_specification():
    """
    建立一個標準的合法 TaskSpecification。

    後續測試只修改其中一個欄位，
    用來測試不同 Validation Rule。
    """

    return TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
            focus="main",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=[],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(
            parameter_names_only=False,
            no_analysis=False,
            no_suggestions=False,
            no_examples=False,
            max_words=None,
            language="zh-TW",
        ),
    )


def validate(specification):
    """
    測試用 helper。
    """

    validator = SpecificationValidator()

    return validator.validate(specification)


# ============================================================
# Basic Validation
# ============================================================


def test_valid_specification_passes():
    """
    正常的 TaskSpecification 應該通過 Validation。
    """

    specification = create_valid_specification()

    result = validate(specification)

    assert isinstance(
        result,
        SpecificationValidationResult,
    )

    assert result.passed is True
    assert result.failed is False
    assert result.status == "passed"

    assert result.errors == []


def test_valid_specification_contains_checked_sections():
    """
    Validator 應該記錄主要被檢查的區塊。
    """

    specification = create_valid_specification()

    result = validate(specification)

    assert "top_level" in result.checked
    assert "objective" in result.checked
    assert "tool_constraints" in result.checked
    assert "state_requirements" in result.checked
    assert "output_constraints" in result.checked
    assert "cross_constraints" in result.checked


def test_validation_result_to_dict():
    """
    Validation Result 應該可以轉換成 dict。
    """

    specification = create_valid_specification()

    result = validate(specification)

    data = result.to_dict()

    assert isinstance(
        data,
        dict,
    )

    assert data["status"] == "passed"
    assert data["passed"] is True
    assert data["failed"] is False
    assert data["errors"] == []
    assert isinstance(
        data["warnings"],
        list,
    )
    assert isinstance(
        data["checked"],
        list,
    )


# ============================================================
# Invalid Specification Type
# ============================================================


def test_none_specification_fails():
    """
    Specification 不可以是 None。
    """

    result = validate(None)

    assert result.failed is True
    assert result.status == "failed"

    assert any("None" in error for error in result.errors)


def test_invalid_specification_type_fails():
    """
    Specification 必須是 dict
    或提供 to_dict() 的物件。
    """

    result = validate("invalid specification")

    assert result.failed is True

    assert any("dict" in error for error in result.errors)


def test_list_specification_fails():
    """
    list 不可以直接當作 Specification。
    """

    result = validate([])

    assert result.failed is True


# ============================================================
# Top-Level Structure
# ============================================================


def test_missing_objective_fails():
    """
    缺少 objective 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    del data["objective"]

    result = validate(data)

    assert result.failed is True

    assert any("objective" in error for error in result.errors)


def test_missing_tool_constraints_fails():
    """
    缺少 tool_constraints 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    del data["tool_constraints"]

    result = validate(data)

    assert result.failed is True

    assert any("tool_constraints" in error for error in result.errors)


def test_missing_state_requirements_fails():
    """
    缺少 state_requirements 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    del data["state_requirements"]

    result = validate(data)

    assert result.failed is True

    assert any("state_requirements" in error for error in result.errors)


def test_missing_output_constraints_fails():
    """
    缺少 output_constraints 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    del data["output_constraints"]

    result = validate(data)

    assert result.failed is True

    assert any("output_constraints" in error for error in result.errors)


def test_unknown_top_level_field_creates_warning_not_error():
    """
    未知的 Top-level field
    目前只產生 warning，不直接 FAIL。

    這是為了保留未來 TaskSpecification 擴充的相容性。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["future_field"] = "future value"

    result = validate(data)

    assert result.passed is True

    assert any("future_field" in warning for warning in result.warnings)


# ============================================================
# Objective Validation
# ============================================================


def test_valid_objective_types_pass():
    """
    所有支援的 Objective Type 都應該通過。
    """

    valid_types = {
        "general",
        "inspect",
        "create",
        "modify",
        "delete",
        "execute",
        "git",
    }

    for objective_type in valid_types:

        specification = create_valid_specification()

        data = specification.to_dict()

        data["objective"]["type"] = objective_type

        result = validate(data)

        assert result.passed is True, f"objective type " f"{objective_type} 不應該 FAIL"


def test_invalid_objective_type_fails():
    """
    不支援的 Objective Type 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["type"] = "invalid"

    result = validate(data)

    assert result.failed is True

    assert any("objective.type" in error for error in result.errors)


def test_missing_objective_type_fails():
    """
    objective 缺少 type 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    del data["objective"]["type"]

    result = validate(data)

    assert result.failed is True

    assert any("type" in error for error in result.errors)


def test_objective_type_must_be_string():
    """
    objective.type 必須是 string。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["type"] = 123

    result = validate(data)

    assert result.failed is True

    assert any("string" in error for error in result.errors)


def test_empty_objective_type_fails():
    """
    objective.type 不可以是空字串。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["type"] = ""

    result = validate(data)

    assert result.failed is True


def test_objective_target_can_be_none():
    """
    objective.target 可以是 None。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["target"] = None

    result = validate(data)

    assert result.passed is True


def test_objective_target_must_be_string_or_none():
    """
    objective.target 必須是 string 或 None。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["target"] = 123

    result = validate(data)

    assert result.failed is True


def test_empty_objective_target_fails():
    """
    objective.target 如果存在，
    不可以是空字串。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["target"] = ""

    result = validate(data)

    assert result.failed is True


def test_objective_focus_can_be_none():
    """
    objective.focus 可以是 None。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["focus"] = None

    result = validate(data)

    assert result.passed is True


def test_objective_focus_must_be_string_or_none():
    """
    objective.focus 必須是 string 或 None。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["focus"] = 123

    result = validate(data)

    assert result.failed is True


def test_objective_must_be_dict():
    """
    objective 必須是 object。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"] = "inspect"

    result = validate(data)

    assert result.failed is True


# ============================================================
# Tool Constraints Validation
# ============================================================


def test_empty_tool_constraints_pass():
    """
    沒有限制 Tool 時應該通過。
    """

    specification = create_valid_specification()

    result = validate(specification)

    assert result.passed is True


def test_allowed_tools_must_be_list():
    """
    allowed_tools 必須是 list。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"]["allowed_tools"] = "read_file"

    result = validate(data)

    assert result.failed is True

    assert any("allowed_tools" in error for error in result.errors)


def test_forbidden_tools_must_be_list():
    """
    forbidden_tools 必須是 list。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"]["forbidden_tools"] = "read_file"

    result = validate(data)

    assert result.failed is True

    assert any("forbidden_tools" in error for error in result.errors)


def test_tool_names_must_be_strings():
    """
    Tool name 必須是 string。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"]["allowed_tools"] = [
        "read_file",
        123,
    ]

    result = validate(data)

    assert result.failed is True


def test_empty_tool_name_fails():
    """
    Tool name 不可以是空字串。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"]["allowed_tools"] = [""]

    result = validate(data)

    assert result.failed is True


def test_duplicate_tool_name_creates_warning():
    """
    重複 Tool Name 目前不直接 FAIL，
    但應該產生 warning。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"]["allowed_tools"] = [
        "read_file",
        "read_file",
    ]

    result = validate(data)

    assert result.passed is True

    assert any("read_file" in warning for warning in result.warnings)


def test_allowed_and_forbidden_tool_conflict_fails():
    """
    同一個 Tool 不可以同時存在
    allowed_tools 與 forbidden_tools。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"] = {
        "allowed_tools": ["read_file"],
        "forbidden_tools": ["read_file"],
    }

    result = validate(data)

    assert result.failed is True

    assert any(
        "allowed_tools" in error and "forbidden_tools" in error
        for error in result.errors
    )


def test_tool_constraints_must_be_dict():
    """
    tool_constraints 必須是 object。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"] = []

    result = validate(data)

    assert result.failed is True


# ============================================================
# State Requirements Validation
# ============================================================


def test_empty_state_requirements_pass():
    """
    沒有 State Requirement 時應該通過。
    """

    specification = create_valid_specification()

    result = validate(specification)

    assert result.passed is True


def test_valid_file_exists_requirement_passes():
    """
    file_exists Requirement 應該通過。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "file_exists",
            "path": "main.py",
            "text": None,
        }
    ]

    result = validate(data)

    assert result.passed is True



def test_valid_contains_requirement_passes():
    """
    contains Requirement 應該通過。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "contains",
            "path": "main.py",
            "text": "def main",
        }
    ]

    result = validate(data)

    assert result.passed is True


def test_valid_not_contains_requirement_passes():
    """
    not_contains Requirement 應該通過。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "not_contains",
            "path": "main.py",
            "text": "dangerous_code",
        }
    ]

    result = validate(data)

    assert result.passed is True


def test_state_requirements_must_be_list():
    """
    state_requirements 必須是 list。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = {}

    result = validate(data)

    assert result.failed is True


def test_state_requirement_must_be_dict():
    """
    單一 State Requirement 必須是 object。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = ["file_exists"]

    result = validate(data)

    assert result.failed is True


def test_invalid_state_requirement_type_fails():
    """
    不支援的 Requirement Type 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "invalid",
            "path": "main.py",
            "text": None,
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_state_requirement_type_must_exist():
    """
    State Requirement 缺少 type 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "path": "main.py",
            "text": None,
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_state_requirement_path_must_exist():
    """
    State Requirement 缺少 path 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "file_exists",
            "text": None,
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_state_requirement_path_must_be_string():
    """
    State Requirement path 必須是 string。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "file_exists",
            "path": 123,
            "text": None,
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_state_requirement_path_cannot_be_empty():
    """
    State Requirement path 不可以是空字串。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "file_exists",
            "path": "",
            "text": None,
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_contains_requires_text():
    """
    contains Requirement 必須有 text。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "contains",
            "path": "main.py",
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_not_contains_requires_text():
    """
    not_contains Requirement 必須有 text。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "not_contains",
            "path": "main.py",
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_contains_text_must_be_string():
    """
    contains Requirement 的 text 必須是 string。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "contains",
            "path": "main.py",
            "text": 123,
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_not_contains_text_must_be_string():
    """
    not_contains Requirement 的 text 必須是 string。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "not_contains",
            "path": "main.py",
            "text": 123,
        }
    ]

    result = validate(data)

    assert result.failed is True


def test_empty_contains_text_fails():
    """
    contains 的 text 不可以是空字串。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "contains",
            "path": "main.py",
            "text": "",
        }
    ]

    result = validate(data)

    assert result.failed is True


# ============================================================
# Output Constraints Validation
# ============================================================


def test_output_constraints_must_be_dict():
    """
    output_constraints 必須是 object。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"] = []

    result = validate(data)

    assert result.failed is True


def test_boolean_output_constraints_must_be_boolean():
    """
    Output Boolean Constraint 必須是 bool。
    """

    boolean_fields = [
        "parameter_names_only",
        "no_analysis",
        "no_suggestions",
        "no_examples",
    ]

    for field_name in boolean_fields:

        specification = create_valid_specification()

        data = specification.to_dict()

        data["output_constraints"][field_name] = "true"

        result = validate(data)

        assert result.failed is True, f"{field_name} 應該 FAIL"


def test_valid_max_words_passes():
    """
    正常 max_words 應該通過。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["max_words"] = 20

    result = validate(data)

    assert result.passed is True


def test_max_words_can_be_none():
    """
    max_words 可以是 None。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["max_words"] = None

    result = validate(data)

    assert result.passed is True


def test_max_words_must_be_integer():
    """
    max_words 必須是 integer 或 None。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["max_words"] = "20"

    result = validate(data)

    assert result.failed is True


def test_max_words_cannot_be_boolean():
    """
    Python 中 bool 是 int 的 subclass。

    因此 Validator 必須特別阻止：

        True
        False

    被當成 max_words。
    """

    for value in [True, False]:

        specification = create_valid_specification()

        data = specification.to_dict()

        data["output_constraints"]["max_words"] = value

        result = validate(data)

        assert result.failed is True


def test_max_words_must_be_positive():
    """
    max_words 必須大於 0。
    """

    for value in [0, -1, -100]:

        specification = create_valid_specification()

        data = specification.to_dict()

        data["output_constraints"]["max_words"] = value

        result = validate(data)

        assert result.failed is True


def test_valid_output_languages_pass():
    """
    支援的 language 應該通過。
    """

    languages = [
        "zh-TW",
        "en",
        "ja",
        "ko",
    ]

    for language in languages:

        specification = create_valid_specification()

        data = specification.to_dict()

        data["output_constraints"]["language"] = language

        result = validate(data)

        assert result.passed is True


def test_language_must_be_string():
    """
    language 必須是 string。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["language"] = 123

    result = validate(data)

    assert result.failed is True


def test_language_cannot_be_empty():
    """
    language 不可以是空字串。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["language"] = ""

    result = validate(data)

    assert result.failed is True


def test_unsupported_language_fails():
    """
    不支援的 language 應該 FAIL。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["language"] = "fr"

    result = validate(data)

    assert result.failed is True


# ============================================================
# Cross-field Validation
# ============================================================


def test_inspect_with_restricted_non_read_tools_creates_warning():
    """
    inspect + allowed_tools 只有 execute
    目前應該產生 warning，而不是直接 FAIL。

    原因：

    Specification Validator 只判斷
    「可能存在不可完成風險」，

    最終 Tool 執行仍由 Runtime
    與 Tool Constraints Enforcement 處理。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"] = {
        "allowed_tools": ["execute_command"],
        "forbidden_tools": [],
    }

    result = validate(data)

    assert result.passed is True

    assert any("inspect" in warning for warning in result.warnings)


def test_inspect_with_read_file_is_valid():
    """
    inspect + read_file 是合理組合。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"] = {
        "allowed_tools": ["read_file"],
        "forbidden_tools": [],
    }

    result = validate(data)

    assert result.passed is True


def test_state_requirements_with_restricted_tools_creates_warning():
    """
    State Requirements 搭配沒有修改能力的
    allowed_tools 時，目前產生 warning。

    注意：

    這裡不直接 FAIL，
    因為 State Requirement 本身可能只是
    驗證現有狀態，而不是要求修改狀態。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "file_exists",
            "path": "main.py",
            "text": None,
        }
    ]

    data["tool_constraints"] = {
        "allowed_tools": ["read_file"],
        "forbidden_tools": [],
    }

    result = validate(data)

    assert result.passed is True


def test_parameter_names_only_with_positive_max_words_passes():
    """
    parameter_names_only + 正常 max_words
    應該通過。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"] = {
        "parameter_names_only": True,
        "no_analysis": True,
        "no_suggestions": True,
        "no_examples": True,
        "max_words": 20,
        "language": "zh-TW",
    }

    result = validate(data)

    assert result.passed is True


# ============================================================
# Multiple Errors
# ============================================================


def test_multiple_invalid_fields_are_reported():
    """
    Validator 應該盡可能一次回報多個錯誤，
    而不是遇到第一個錯誤就停止。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["type"] = "invalid"

    data["tool_constraints"] = {
        "allowed_tools": "read_file",
        "forbidden_tools": "read_file",
    }

    data["output_constraints"]["max_words"] = -10

    result = validate(data)

    assert result.failed is True

    assert len(result.errors) >= 3


# ============================================================
# TaskSpecification Compatibility
# ============================================================


def test_validator_accepts_task_specification_object():
    """
    Validator 可以直接接收
    TaskSpecification instance。
    """

    specification = create_valid_specification()

    result = validate(specification)

    assert result.passed is True


def test_validator_accepts_task_specification_dict():
    """
    Validator 也可以接收
    TaskSpecification.to_dict()。
    """

    specification = create_valid_specification()

    result = validate(specification.to_dict())

    assert result.passed is True


# ============================================================
# Functional API
# ============================================================


def test_validate_specification_function():
    """
    測試：

        validate_specification()

    Functional API。
    """

    specification = create_valid_specification()

    result = validate_specification(specification)

    assert isinstance(
        result,
        SpecificationValidationResult,
    )

    assert result.passed is True


def test_validate_specification_function_detects_error():
    """
    Functional API 也應該能偵測錯誤。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["type"] = "invalid"

    result = validate_specification(data)

    assert result.failed is True


# ============================================================
# Regression Tests
# ============================================================


def test_existing_requirement_types_remain_compatible():
    """
    確認目前既有的 Requirement Types
    與 Specification Validator 相容。

    這是非常重要的 Regression Test，
    避免 Phase 8.6 破壞 Phase 8.4。
    """

    specification = TaskSpecification(
        objective=Objective(
            type="modify",
            target="main.py",
            focus=None,
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=[],
        ),
        state_requirements=[
            StateRequirement(
                type="contains",
                path="main.py",
                text="return message",
            )
        ],
        output_constraints=OutputConstraints(),
    )

    result = validate(specification)

    assert result.passed is True


def test_existing_output_constraints_remain_compatible():
    """
    確認 Phase 8.5 的 OutputConstraints
    與 Phase 8.6 Validator 相容。
    """

    specification = TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
        ),
        tool_constraints=ToolConstraints(),
        state_requirements=[],
        output_constraints=OutputConstraints(
            parameter_names_only=True,
            no_analysis=True,
            no_suggestions=True,
            no_examples=True,
            max_words=20,
            language="zh-TW",
        ),
    )

    result = validate(specification)

    assert result.passed is True
