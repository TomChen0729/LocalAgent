from unittest.mock import Mock

from agent.runtime import AgentRuntime


def create_runtime():
    """
    建立 AgentRuntime 測試實例。

    這裡不實際呼叫 Ollama，
    只測試 Recovery Orchestration。
    """

    runtime = AgentRuntime.__new__(
        AgentRuntime,
    )

    runtime.task_state = {
        "recovery_attempt_count": 0,
        "last_recovery_tool": None,
        "last_recovery_result": None,
        "last_recovery_category": None,
    }

    return runtime


def test_attempt_tool_recovery_success():
    """
    測試：

        read_section failure
            ↓
        read_file recovery
            ↓
        success
    """

    runtime = create_runtime()

    # --------------------------------------------------
    # Mock Recovery Components
    # --------------------------------------------------

    runtime.recovery_policy = Mock()
    runtime.recovery_selector = Mock()
    runtime.recovery_attempt_policy = Mock()
    runtime.recovery_argument_adapter = Mock()
    runtime.recovery_executor = Mock()

    # --------------------------------------------------
    # Failure Classification
    # --------------------------------------------------

    # RecoveryPolicy decision
    policy_decision = Mock()

    policy_decision.should_recover = True
    policy_decision.alternatives = [
        "read_file",
    ]
    policy_decision.reason = "Alternative tool available"
    policy_decision.to_dict.return_value = {
        "should_recover": True,
        "alternatives": ["read_file"],
    }

    runtime.recovery_policy.decide.return_value = policy_decision

    # --------------------------------------------------
    # Recovery Attempt
    # --------------------------------------------------

    attempt_decision = Mock()

    attempt_decision.should_recover = True
    attempt_decision.reason = "Recovery allowed"
    attempt_decision.to_dict.return_value = {
        "should_recover": True,
    }

    runtime.recovery_attempt_policy.can_recover.return_value = attempt_decision

    # --------------------------------------------------
    # Recovery Selection
    # --------------------------------------------------

    selection = Mock()

    selection.selected = True
    selection.selected_tool = "read_file"
    selection.reason = "Selected first alternative"

    selection.to_dict.return_value = {
        "selected_tool": "read_file",
    }

    runtime.recovery_selector.select.return_value = selection

    # --------------------------------------------------
    # Argument Transformation
    # --------------------------------------------------

    transformed = Mock()

    transformed.transformed_arguments = {
        "path": "README.md",
    }

    transformed.changed = True

    transformed.to_dict.return_value = {
        "changed": True,
        "transformed_arguments": {
            "path": "README.md",
        },
    }

    runtime.recovery_argument_adapter.transform.return_value = transformed

    # --------------------------------------------------
    # Recovery Execution
    # --------------------------------------------------

    execution = Mock()

    execution.success = True

    execution.to_dict.return_value = {
        "success": True,
        "tool": "read_file",
        "result": "README content",
    }

    runtime.recovery_executor.execute.return_value = execution

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
            "heading": "Features",
        },
        tool_result="找不到指定的 Markdown Section。",
    )

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------

    assert result["attempted"] is True
    assert result["recovered"] is True

    assert result["original_tool"] == "read_section"

    assert result["selection"]["selected_tool"] == "read_file"

    assert runtime.task_state["recovery_attempt_count"] == 1

    assert runtime.task_state["last_recovery_tool"] == "read_file"

    assert runtime.task_state["last_recovery_result"] == execution.to_dict.return_value

    assert runtime.task_state["last_recovery_category"] == "not_found"


def test_attempt_tool_recovery_no_failure():
    """
    Tool Result 沒有 Failure 時，
    不應該啟動 Recovery。
    """

    runtime = create_runtime()

    runtime.recovery_policy = Mock()

    result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
            "heading": "Features",
        },
        tool_result="成功讀取 Section。",
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    runtime.recovery_policy.decide.assert_not_called()

    assert runtime.task_state["recovery_attempt_count"] == 0


def test_attempt_tool_recovery_policy_rejects():
    """
    Failure 存在，但 RecoveryPolicy
    判定不允許 Recovery。
    """

    runtime = create_runtime()

    runtime.recovery_policy = Mock()
    runtime.recovery_attempt_policy = Mock()

    decision = Mock()

    decision.should_recover = False
    decision.reason = "No alternative tool"

    decision.to_dict.return_value = {
        "should_recover": False,
    }

    runtime.recovery_policy.decide.return_value = decision

    result = runtime.attempt_tool_recovery(
        original_tool="write_file",
        arguments={
            "path": "test.txt",
        },
        tool_result="Permission denied。",
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    assert result["recovery"]["should_recover"] is False

    runtime.recovery_attempt_policy.can_recover.assert_not_called()

    assert runtime.task_state["recovery_attempt_count"] == 0


def test_attempt_tool_recovery_attempt_limit():
    """
    Recovery Attempt 已達上限時，
    不應該執行 Alternative Tool。
    """

    runtime = create_runtime()

    runtime.task_state["recovery_attempt_count"] = 1

    runtime.recovery_policy = Mock()
    runtime.recovery_attempt_policy = Mock()

    decision = Mock()

    decision.should_recover = True
    decision.alternatives = [
        "read_file",
    ]

    decision.to_dict.return_value = {
        "should_recover": True,
    }

    runtime.recovery_policy.decide.return_value = decision

    attempt_decision = Mock()

    attempt_decision.should_recover = False
    attempt_decision.reason = "Maximum recovery attempts reached"

    attempt_decision.to_dict.return_value = {
        "should_recover": False,
    }

    runtime.recovery_attempt_policy.can_recover.return_value = attempt_decision

    result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
        },
        tool_result="找不到檔案。",
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    assert result["attempt"]["should_recover"] is False

    assert runtime.task_state["recovery_attempt_count"] == 1


def test_attempt_tool_recovery_no_selected_tool():
    """
    RecoveryPolicy 有候選 Tool，
    但 RecoverySelector 沒有選出 Tool。
    """

    runtime = create_runtime()

    runtime.recovery_policy = Mock()
    runtime.recovery_attempt_policy = Mock()
    runtime.recovery_selector = Mock()

    decision = Mock()

    decision.should_recover = True
    decision.alternatives = [
        "read_file",
    ]

    decision.to_dict.return_value = {
        "should_recover": True,
    }

    runtime.recovery_policy.decide.return_value = decision

    attempt_decision = Mock()

    attempt_decision.should_recover = True

    attempt_decision.to_dict.return_value = {
        "should_recover": True,
    }

    runtime.recovery_attempt_policy.can_recover.return_value = attempt_decision

    selection = Mock()

    selection.selected = False
    selection.selected_tool = None
    selection.reason = "No valid alternative"

    selection.to_dict.return_value = {
        "selected_tool": None,
    }

    runtime.recovery_selector.select.return_value = selection

    result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
        },
        tool_result="找不到 Section。",
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    assert result["selection"]["selected_tool"] is None
