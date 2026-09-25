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
        RecoveryManager
            ↓
        read_file recovery
            ↓
        success
    """

    runtime = create_runtime()

    runtime.recovery_manager = Mock()

    runtime.recovery_manager.handle.return_value = {
        "recovered": True,
        "attempted": True,
        "original_tool": "read_section",
        "failure": {
            "category": "not_found",
        },
        "arguments": {
            "changed": True,
            "transformed_arguments": {
                "path": "README.md",
            },
        },
        "execution": {
            "success": True,
            "tool": "read_file",
            "result": "README content",
        },
    }

    result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
            "heading": "Features",
        },
        tool_result="找不到指定的 Markdown Section。",
    )

    assert result["attempted"] is True
    assert result["recovered"] is True

    assert result["execution"]["tool"] == "read_file"

    runtime.recovery_manager.handle.assert_called_once()


def test_attempt_tool_recovery_no_failure():
    """
    Tool Result 沒有 Failure 時，
    不應該啟動 Recovery。
    """

    runtime = create_runtime()

    runtime.recovery_manager = Mock()

    runtime.recovery_manager.handle.return_value = {
        "recovered": False,
        "attempted": False,
        "original_tool": "read_section",
        "failure": {
            "failed": False,
            "category": "none",
        },
        "reason": ("Tool Result 沒有被判定為 Failure。"),
    }

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

    runtime.recovery_manager.handle.assert_called_once()


def test_attempt_tool_recovery_policy_rejects():
    """
    Failure 存在，但 RecoveryManager
    判定不允許 Recovery。
    """

    runtime = create_runtime()

    runtime.recovery_manager = Mock()

    runtime.recovery_manager.handle.return_value = {
        "recovered": False,
        "attempted": False,
        "original_tool": "write_file",
        "failure": {
            "failed": True,
            "category": "permission_denied",
        },
        "recovery": {
            "should_recover": False,
        },
        "reason": "No alternative tool",
    }

    result = runtime.attempt_tool_recovery(
        original_tool="write_file",
        arguments={
            "path": "test.txt",
        },
        tool_result="Permission denied。",
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    runtime.recovery_manager.handle.assert_called_once()


def test_attempt_tool_recovery_attempt_limit():
    """
    Recovery Attempt 已達上限時，
    不應該執行 Alternative Tool。
    """

    runtime = create_runtime()

    runtime.task_state["recovery_attempt_count"] = 1

    runtime.recovery_manager = Mock()

    runtime.recovery_manager.handle.return_value = {
        "recovered": False,
        "attempted": False,
        "original_tool": "read_section",
        "failure": {
            "failed": True,
            "category": "not_found",
        },
        "attempt": {
            "should_recover": False,
        },
        "reason": ("Maximum recovery attempts reached"),
    }

    result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
        },
        tool_result="找不到檔案。",
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    runtime.recovery_manager.handle.assert_called_once()


def test_attempt_tool_recovery_no_selected_tool():
    """
    RecoveryManager 有候選 Tool，
    但最後沒有選出 Tool。
    """

    runtime = create_runtime()

    runtime.recovery_manager = Mock()

    runtime.recovery_manager.handle.return_value = {
        "recovered": False,
        "attempted": False,
        "original_tool": "read_section",
        "failure": {
            "failed": True,
            "category": "not_found",
        },
        "recovery": {
            "should_recover": True,
        },
        "selection": {
            "selected_tool": None,
        },
        "reason": "No valid alternative",
    }

    result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
        },
        tool_result="找不到 Section。",
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    runtime.recovery_manager.handle.assert_called_once()
