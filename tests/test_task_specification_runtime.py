from agent.runtime import AgentRuntime
from requirements.specification import (
    Objective,
    OutputConstraints,
    StateRequirement,
    TaskSpecification,
    ToolConstraints,
)


def test_runtime_initializes_requirement_parser():
    agent = AgentRuntime(model="qwen3:8b")

    assert agent.requirement_parser is not None
    assert agent.requirement_parser.model == "qwen3:8b"


def test_task_specification_can_be_stored():
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
            focus="main",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=["read_file"],
            forbidden_tools=[],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(
            parameter_names_only=True,
            no_analysis=True,
            no_suggestions=True,
            no_examples=True,
            language="zh-TW",
        ),
    )

    agent.task_state["task_specification"] = specification.to_dict()

    assert agent.task_state["task_specification"]["objective"]["type"] == "inspect"

    assert agent.task_state["task_specification"]["objective"]["target"] == "main.py"


def test_state_requirements_remain_compatible_with_verifier():
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="modify",
            target="main.py",
        ),
        tool_constraints=ToolConstraints(),
        state_requirements=[
            StateRequirement(
                type="contains",
                path="main.py",
                text="return message",
            )
        ],
        output_constraints=OutputConstraints(),
    )

    requirements = specification.get_verifier_requirements()

    assert requirements == [
        {
            "type": "contains",
            "path": "main.py",
            "text": "return message",
        }
    ]


# ============================================================
# Phase 8.3
# Tool Constraints Enforcement
# ============================================================


def test_tool_constraint_allows_tool_in_allow_list():
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=["read_file"],
            forbidden_tools=[],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(),
    )

    agent.task_state["task_specification"] = specification.to_dict()

    allowed, message = agent.check_tool_constraints("read_file")

    assert allowed is True
    assert "allowed" in message.lower() or "通過" in message


def test_tool_constraint_denies_tool_not_in_allow_list():
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=["read_file"],
            forbidden_tools=[],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(),
    )

    agent.task_state["task_specification"] = specification.to_dict()

    allowed, message = agent.check_tool_constraints("write_file")

    assert allowed is False
    assert "write_file" in message
    assert "allowed_tools" in message


def test_tool_constraint_denies_forbidden_tool():
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=["delete_file"],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(),
    )

    agent.task_state["task_specification"] = specification.to_dict()

    allowed, message = agent.check_tool_constraints("delete_file")

    assert allowed is False
    assert "delete_file" in message
    assert "forbidden_tools" in message


def test_tool_constraint_allows_any_tool_when_no_constraints():
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="general",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[],
            forbidden_tools=[],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(),
    )

    agent.task_state["task_specification"] = specification.to_dict()

    allowed, message = agent.check_tool_constraints("write_file")

    assert allowed is True


def test_tool_constraint_allows_any_tool_without_task_specification():
    agent = AgentRuntime(model="qwen3:8b")

    agent.task_state["task_specification"] = None

    allowed, message = agent.check_tool_constraints("write_file")

    assert allowed is True


def test_execute_tool_denies_forbidden_tool_before_execution(
    monkeypatch,
):
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="modify",
            target="main.py",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=["read_file"],
            forbidden_tools=[],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(),
    )

    agent.task_state["task_specification"] = specification.to_dict()

    execution_called = False

    def fake_write_file(**arguments):
        nonlocal execution_called
        execution_called = True
        return "WRITE EXECUTED"

    monkeypatch.setattr(
        "agent.runtime.write_file",
        fake_write_file,
    )

    result = agent.execute_tool(
        "write_file",
        {
            "path": "test.txt",
            "content": "Hello",
        },
    )

    assert result["success"] is False
    assert result["error"] == "tool_constraint_denied"
    assert result["tool"] == "write_file"

    # 最重要的 Assertion：
    #
    # Tool Constraint 被拒絕後，
    # 真正的 write_file 絕對不能執行。
    assert execution_called is False


def test_execute_tool_allows_tool_after_constraint_check(
    monkeypatch,
):
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="inspect",
            target="main.py",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=["read_file"],
            forbidden_tools=[],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(),
    )

    agent.task_state["task_specification"] = specification.to_dict()

    monkeypatch.setattr(
        agent.permission_manager,
        "check_permission",
        lambda tool_name, arguments: type(
            "PermissionResult",
            (),
            {
                "allowed": True,
                "message": "allowed",
            },
        )(),
    )

    monkeypatch.setattr(
        "agent.runtime.read_file",
        lambda **arguments: "Hello LocalAgent",
    )

    result = agent.execute_tool(
        "read_file",
        {
            "path": "main.py",
        },
    )

    assert result == "Hello LocalAgent"


def test_forbidden_tool_has_priority_over_allow_list():
    agent = AgentRuntime(model="qwen3:8b")

    specification = TaskSpecification(
        objective=Objective(
            type="general",
        ),
        tool_constraints=ToolConstraints(
            allowed_tools=[
                "read_file",
                "delete_file",
            ],
            forbidden_tools=[
                "delete_file",
            ],
        ),
        state_requirements=[],
        output_constraints=OutputConstraints(),
    )

    # 這個 Specification 理論上本身會被 validate()
    # 視為 invalid，這裡只測試 Runtime Constraint
    # 的拒絕邏輯。
    agent.task_state["task_specification"] = specification.to_dict()

    allowed, message = agent.check_tool_constraints("delete_file")

    assert allowed is False
    assert "forbidden_tools" in message
