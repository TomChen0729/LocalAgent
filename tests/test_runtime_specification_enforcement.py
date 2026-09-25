import json

import pytest

from agent.runtime import AgentRuntime
from requirements.specification import (
    Objective,
    OutputConstraints,
    StateRequirement,
    TaskSpecification,
    ToolConstraints,
)
from requirements.specification_validator import (
    SpecificationValidator,
)


# ============================================================
# Test Helpers
# ============================================================


def create_valid_specification():
    """
    建立一份合法的 TaskSpecification。
    """

    return TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
            focus="主要功能",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=[],
        ),
        state_requirements=[
            StateRequirement(
                type="file_exists",
                path="main.py",
            )
        ],
        output_constraints=OutputConstraints(
            parameter_names_only=False,
            no_analysis=False,
            no_suggestions=False,
            no_examples=False,
            max_words=None,
            language="zh-TW",
        ),
    )


def create_runtime():
    """
    建立 AgentRuntime。
    """

    return AgentRuntime(
        model="qwen3:8b",
    )


# ============================================================
# SpecificationValidator Basic Tests
# ============================================================


def test_valid_specification_passes():
    """
    合法 TaskSpecification 應該通過 SpecificationValidator。
    """

    specification = create_valid_specification()

    validator = SpecificationValidator()

    result = validator.validate(specification)

    assert result.passed is True
    assert result.failed is False
    assert result.errors == []


def test_invalid_objective_type_fails():
    """
    不支援的 objective type 應該被拒絕。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["type"] = "invalid_objective"

    validator = SpecificationValidator()

    result = validator.validate(data)

    assert result.passed is False
    assert result.failed is True
    assert any(
        "objective.type" in error
        for error in result.errors
    )


def test_invalid_tool_constraints_type_fails():
    """
    allowed_tools 如果不是 list，
    SpecificationValidator 應該拒絕。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"]["allowed_tools"] = "read_file"

    validator = SpecificationValidator()

    result = validator.validate(data)

    assert result.passed is False
    assert result.failed is True
    assert any(
        "allowed_tools" in error
        for error in result.errors
    )


def test_allowed_and_forbidden_tool_conflict_fails():
    """
    同一個 Tool 不可以同時存在於
    allowed_tools 與 forbidden_tools。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["tool_constraints"] = {
        "allowed_tools": [
            "read_file",
        ],
        "forbidden_tools": [
            "read_file",
        ],
    }

    validator = SpecificationValidator()

    result = validator.validate(data)

    assert result.passed is False
    assert result.failed is True

    assert any(
        "allowed_tools" in error
        and "forbidden_tools" in error
        for error in result.errors
    )


def test_invalid_state_requirement_type_fails():
    """
    不支援的 State Requirement type
    應該被拒絕。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "file_not_exists",
            "path": "missing.py",
            "text": None,
        }
    ]

    validator = SpecificationValidator()

    result = validator.validate(data)

    assert result.passed is False
    assert result.failed is True

    assert any(
        "state_requirements[0].type" in error
        for error in result.errors
    )


def test_contains_requirement_without_text_fails():
    """
    contains Requirement 必須具有 text。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["state_requirements"] = [
        {
            "type": "contains",
            "path": "main.py",
            "text": None,
        }
    ]

    validator = SpecificationValidator()

    result = validator.validate(data)

    assert result.passed is False
    assert result.failed is True

    assert any(
        "text" in error
        for error in result.errors
    )


def test_invalid_max_words_fails():
    """
    max_words 必須是正整數。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["max_words"] = -10

    validator = SpecificationValidator()

    result = validator.validate(data)

    assert result.passed is False
    assert result.failed is True

    assert any(
        "max_words" in error
        for error in result.errors
    )


def test_invalid_language_fails():
    """
    不支援的 language 應該被拒絕。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    data["output_constraints"]["language"] = "xx"

    validator = SpecificationValidator()

    result = validator.validate(data)

    assert result.passed is False
    assert result.failed is True

    assert any(
        "language" in error
        for error in result.errors
    )


# ============================================================
# Runtime Specification State Tests
# ============================================================


def test_runtime_can_store_task_specification():
    """
    AgentRuntime 應該可以保存 TaskSpecification。
    """

    runtime = create_runtime()

    specification = create_valid_specification()

    runtime.start_task(
        "確認 main.py 是否存在"
    )

    runtime.task_state["task_specification"] = (
        specification.to_dict()
    )

    stored_specification = runtime.task_state[
        "task_specification"
    ]

    assert isinstance(
        stored_specification,
        dict,
    )

    assert (
        stored_specification["objective"]["type"]
        == "inspect"
    )

    assert (
        stored_specification["objective"]["target"]
        == "main.py"
    )


def test_runtime_task_specification_can_be_validated():
    """
    Runtime 保存的 TaskSpecification
    應該可以交給 SpecificationValidator。
    """

    runtime = create_runtime()

    specification = create_valid_specification()

    runtime.start_task(
        "確認 main.py 是否存在"
    )

    runtime.task_state["task_specification"] = (
        specification.to_dict()
    )

    validator = SpecificationValidator()

    result = validator.validate(
        runtime.task_state["task_specification"]
    )

    assert result.passed is True


def test_runtime_detects_invalid_task_specification():
    """
    Runtime State 中如果存在非法 Specification，
    SpecificationValidator 應該能偵測。
    """

    runtime = create_runtime()

    specification = create_valid_specification()

    data = specification.to_dict()

    data["objective"]["type"] = "invalid_objective"

    runtime.start_task(
        "測試非法 specification"
    )

    runtime.task_state["task_specification"] = data

    validator = SpecificationValidator()

    result = validator.validate(
        runtime.task_state["task_specification"]
    )

    assert result.passed is False


# ============================================================
# Validation Result Tests
# ============================================================


def test_validation_result_contains_checked_sections():
    """
    Validation Result 應該記錄已檢查的區域。
    """

    specification = create_valid_specification()

    validator = SpecificationValidator()

    result = validator.validate(specification)

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

    validator = SpecificationValidator()

    result = validator.validate(specification)

    data = result.to_dict()

    assert isinstance(
        data,
        dict,
    )

    assert data["status"] == "passed"

    assert data["errors"] == []

    assert data["warnings"] == []

    assert data["passed"] is True

    assert data["failed"] is False


# ============================================================
# Runtime Integration Preparation Tests
# ============================================================


def test_runtime_initial_task_state_has_no_specification():
    """
    新建立的 Runtime Task，
    在 Parser 尚未執行前不應該有 Specification。
    """

    runtime = create_runtime()

    runtime.start_task(
        "測試 Task"
    )

    assert runtime.task_state[
        "task_specification"
    ] is None


def test_runtime_initial_parser_state():
    """
    新 Task 的 Parser 狀態應該是 None。
    """

    runtime = create_runtime()

    runtime.start_task(
        "測試 Task"
    )

    assert runtime.task_state[
        "parser_status"
    ] is None

    assert runtime.task_state[
        "parser_error"
    ] is None


def test_valid_specification_serialization_is_json_safe():
    """
    TaskSpecification.to_dict()
    應該可以安全序列化成 JSON。
    """

    specification = create_valid_specification()

    data = specification.to_dict()

    serialized = json.dumps(
        data,
        ensure_ascii=False,
    )

    assert isinstance(
        serialized,
        str,
    )

    restored = json.loads(
        serialized
    )

    assert restored["objective"]["type"] == "inspect"
    assert restored["objective"]["target"] == "main.py"
    
# ============================================================
# Runtime Specification Validation Gate Tests
# ============================================================


def test_runtime_specification_validation_gate_allows_valid_specification():
    """
    合法 TaskSpecification 通過 Validation 後，
    Runtime 不應該停止 Task。
    """

    runtime = create_runtime()

    runtime.start_task(
        "確認 main.py 是否存在"
    )

    specification = create_valid_specification()

    result = runtime.validate_task_specification(
        specification
    )

    assert result["status"] == "passed"
    assert result["passed"] is True
    assert result["failed"] is False

    assert (
        runtime.task_state[
            "specification_validation_status"
        ]
        == "passed"
    )

    assert (
        runtime.task_state[
            "specification_validation_result"
        ]["passed"]
        is True
    )

    assert runtime.task_state["status"] != "stopped"


def test_runtime_specification_validation_gate_stops_invalid_specification():
    """
    非法 TaskSpecification 未通過 Validation 時，
    Runtime 必須停止 Task。
    """

    runtime = create_runtime()

    runtime.start_task(
        "測試非法 specification"
    )

    invalid_specification = TaskSpecification(
        objective=Objective(
            type="invalid_objective",
            target="main.py",
            focus="主要功能",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=[],
        ),
        state_requirements=[
            StateRequirement(
                type="file_exists",
                path="main.py",
            )
        ],
        output_constraints=OutputConstraints(
            parameter_names_only=False,
            no_analysis=False,
            no_suggestions=False,
            no_examples=False,
            max_words=None,
            language="zh-TW",
        ),
    )

    result = runtime.validate_task_specification(
        invalid_specification
    )

    assert result["status"] == "failed"
    assert result["passed"] is False
    assert result["failed"] is True

    assert (
        runtime.task_state[
            "specification_validation_status"
        ]
        == "failed"
    )

    assert (
        runtime.task_state[
            "specification_validation_result"
        ]["passed"]
        is False
    )

    assert runtime.task_state["status"] == "stopped"


def test_runtime_specification_validation_gate_fails_closed_on_validator_exception(
    monkeypatch,
):
    """
    SpecificationValidator 發生 Exception 時，
    Runtime 必須 Fail Closed：

    Validator 失敗
        ↓
    Validation FAILED
        ↓
    Runtime STOP
    """

    runtime = create_runtime()

    runtime.start_task(
        "測試 Validator Exception"
    )

    specification = create_valid_specification()

    def raise_validator_exception(
        specification,
    ):
        raise RuntimeError(
            "測試用 Validator Exception"
        )

    monkeypatch.setattr(
        runtime.specification_validator,
        "validate",
        raise_validator_exception,
    )

    result = runtime.validate_task_specification(
        specification
    )

    assert result["status"] == "failed"
    assert result["passed"] is False
    assert result["failed"] is True

    assert any(
        "Validator 執行失敗"
        in error
        for error in result["errors"]
    )

    assert (
        runtime.task_state[
            "specification_validation_status"
        ]
        == "failed"
    )

    assert runtime.task_state["status"] == "stopped"


def test_runtime_specification_validation_gate_rejects_invalid_object():
    """
    Runtime 收到不是 TaskSpecification 的物件時，
    必須拒絕並停止 Task。
    """

    runtime = create_runtime()

    runtime.start_task(
        "測試非法 Specification Object"
    )

    invalid_specification = {
        "objective": {
            "type": "inspect",
            "target": "main.py",
        }
    }

    result = runtime.validate_task_specification(
        invalid_specification
    )

    assert result["status"] == "failed"
    assert result["passed"] is False
    assert result["failed"] is True

    assert any(
        "不是 TaskSpecification"
        in error
        for error in result["errors"]
    )

    assert (
        runtime.task_state[
            "specification_validation_status"
        ]
        == "failed"
    )

    assert runtime.task_state["status"] == "stopped"
    
# ============================================================
# Runtime.run() Specification Validation Gate Tests
# ============================================================


def test_runtime_run_stops_before_agent_loop_when_specification_is_invalid(
    monkeypatch,
):
    """
    run() 收到非法 TaskSpecification 時：

        Parser
            ↓
        Specification Validator
            ↓
        FAIL
            ↓
        STOP

    不應該進入 Agent Loop。
    """

    runtime = create_runtime()

    invalid_specification = TaskSpecification(
        objective=Objective(
            type="invalid_objective",
            target="main.py",
            focus="主要功能",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=[],
        ),
        state_requirements=[
            StateRequirement(
                type="file_exists",
                path="main.py",
            )
        ],
        output_constraints=OutputConstraints(
            parameter_names_only=False,
            no_analysis=False,
            no_suggestions=False,
            no_examples=False,
            max_words=None,
            language="zh-TW",
        ),
    )

    # --------------------------------------------------------
    # Mock Requirement Parser
    #
    # 不真的呼叫 Qwen，
    # 直接讓 Parser 回傳非法 Specification。
    # --------------------------------------------------------

    monkeypatch.setattr(
        runtime,
        "parse_task_specification",
        lambda user_input: invalid_specification,
    )

    # --------------------------------------------------------
    # 如果 Agent Loop 被執行，
    # chat() 就會被呼叫。
    #
    # 這裡故意讓它直接失敗，
    # 這樣可以確認 Runtime 是否錯誤進入 Agent Loop。
    # --------------------------------------------------------

    def unexpected_chat_call(*args, **kwargs):
        pytest.fail(
            "Specification Validation FAIL 後不應該進入 Agent Loop。"
            "但 chat() 被呼叫了。"
        )

    monkeypatch.setattr(
        "agent.runtime.chat",
        unexpected_chat_call,
    )

    result = runtime.run(
        "測試非法 specification"
    )

    # --------------------------------------------------------
    # Runtime 應該停止
    # --------------------------------------------------------

    assert (
        runtime.task_state["status"]
        == "stopped"
    )

    assert (
        runtime.task_state[
            "specification_validation_status"
        ]
        == "failed"
    )

    assert (
        runtime.task_state[
            "specification_validation_result"
        ]["passed"]
        is False
    )

    # --------------------------------------------------------
    # run() 應該直接回傳停止訊息
    # --------------------------------------------------------

    assert (
        "未通過 Specification Validation"
        in result
    )


def test_runtime_run_does_not_execute_tool_after_specification_validation_failure(
    monkeypatch,
):
    """
    Specification Validation FAIL 後：

        run()
          ↓
        Validation FAIL
          ↓
        STOP

    execute_tool() 絕對不應該被呼叫。
    """

    runtime = create_runtime()

    invalid_specification = TaskSpecification(
        objective=Objective(
            type="invalid_objective",
            target="main.py",
            focus="主要功能",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=[],
        ),
        state_requirements=[
            StateRequirement(
                type="file_exists",
                path="main.py",
            )
        ],
        output_constraints=OutputConstraints(
            parameter_names_only=False,
            no_analysis=False,
            no_suggestions=False,
            no_examples=False,
            max_words=None,
            language="zh-TW",
        ),
    )

    # --------------------------------------------------------
    # Parser 直接回傳非法 Specification
    # --------------------------------------------------------

    monkeypatch.setattr(
        runtime,
        "parse_task_specification",
        lambda user_input: invalid_specification,
    )

    # --------------------------------------------------------
    # 如果 execute_tool 被呼叫，
    # 代表 Specification Validation Gate 失效。
    # --------------------------------------------------------

    def unexpected_tool_execution(*args, **kwargs):
        pytest.fail(
            "Specification Validation FAIL 後不應該執行 Tool。"
            "但 execute_tool() 被呼叫了。"
        )

    monkeypatch.setattr(
        runtime,
        "execute_tool",
        unexpected_tool_execution,
    )

    # --------------------------------------------------------
    # 同樣禁止 Agent Loop 的 chat()
    # --------------------------------------------------------

    def unexpected_chat_call(*args, **kwargs):
        pytest.fail(
            "Specification Validation FAIL 後不應該進入 Agent Loop。"
            "但 chat() 被呼叫了。"
        )

    monkeypatch.setattr(
        "agent.runtime.chat",
        unexpected_chat_call,
    )

    result = runtime.run(
        "建立 test.txt"
    )

    # --------------------------------------------------------
    # Runtime 必須停止
    # --------------------------------------------------------

    assert (
        runtime.task_state["status"]
        == "stopped"
    )

    assert (
        runtime.task_state[
            "specification_validation_status"
        ]
        == "failed"
    )

    assert (
        runtime.task_state[
            "specification_validation_result"
        ]["passed"]
        is False
    )

    assert (
        "未通過 Specification Validation"
        in result
    )