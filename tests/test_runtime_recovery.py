from unittest.mock import Mock

from agent.runtime import AgentRuntime
from tools.project_context import get_project_path

def create_runtime():
    """
    建立 AgentRuntime 測試實例。

    這裡不實際呼叫 Ollama，
    只測試 Recovery Orchestration。
    """

    runtime = AgentRuntime.__new__(
        AgentRuntime,
    )

    runtime.project_path = get_project_path()

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


def test_recovery_result_goes_through_verification():
    """
    Recovery 成功後，
    如果 Alternative Tool 需要 Verification，
    Runtime 必須執行 Verification。
    """

    runtime = create_runtime()

    runtime.recovery_manager = Mock()

    runtime.recovery_manager.handle.return_value = {
        "recovered": True,
        "attempted": True,
        "original_tool": "write_file",
        "failure": {
            "failed": True,
            "category": "execution_error",
        },
        "arguments": {
            "changed": False,
            "original_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "transformed_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
        },
        "execution": {
            "success": True,
            "tool": "write_file",
            "arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "result": "File written successfully.",
        },
    }

    runtime.needs_verification = Mock(
        return_value=True,
    )

    runtime.verify_tool_result = Mock(
        return_value={
            "status": "verified",
            "verification_tool": "read_file",
            "result": "hello",
        },
    )

    runtime.update_verification_state = Mock()

    runtime.add_verification_context = Mock()

    result = runtime.attempt_tool_recovery(
        original_tool="write_file",
        arguments={
            "path": "test.txt",
            "content": "hello",
        },
        tool_result="Execution failed.",
    )

    assert result["attempted"] is True
    assert result["recovered"] is True

    runtime.needs_verification.assert_called_once_with(
        "write_file",
    )

    runtime.verify_tool_result.assert_called_once_with(
        "write_file",
        {
            "path": "test.txt",
            "content": "hello",
        },
        "File written successfully.",
    )

    runtime.update_verification_state.assert_called_once()

    runtime.add_verification_context.assert_called_once()


def test_recovery_verification_failure_is_recorded():
    """
    Recovery Tool 執行成功，
    但 Verification 失敗時，
    Runtime 必須保留 Verification Failure。

    Recovery Execution Success
        ≠
    Verification Success
    """

    runtime = create_runtime()

    runtime.recovery_manager = Mock()

    runtime.recovery_manager.handle.return_value = {
        "recovered": True,
        "attempted": True,
        "original_tool": "write_file",
        "failure": {
            "failed": True,
            "category": "execution_error",
        },
        "arguments": {
            "changed": False,
            "original_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "transformed_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
        },
        "execution": {
            "success": True,
            "tool": "write_file",
            "arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "result": "File written successfully.",
        },
    }

    runtime.needs_verification = Mock(
        return_value=True,
    )

    runtime.verify_tool_result = Mock(
        return_value={
            "status": "failed",
            "verification_tool": "read_file",
            "result": "檔案內容與預期不一致。",
        },
    )

    runtime.update_verification_state = Mock()

    runtime.add_verification_context = Mock()

    result = runtime.attempt_tool_recovery(
        original_tool="write_file",
        arguments={
            "path": "test.txt",
            "content": "hello",
        },
        tool_result="Execution failed.",
    )

    assert result["attempted"] is True

    # Recovery Tool 本身執行成功
    assert result["recovered"] is True

    # 但 Verification 必須明確記錄失敗
    assert "verification" in result

    assert result["verification"]["status"] == "failed"

    runtime.update_verification_state.assert_called_once_with(
        result["verification"],
    )

    runtime.add_verification_context.assert_called_once_with(
        "write_file",
        result["verification"],
    )


def test_recovery_result_goes_through_requirement_verification(
    monkeypatch,
):
    runtime = AgentRuntime()

    runtime.task_state["requirements"] = [
        {
            "type": "file_exists",
            "path": "test.txt",
        }
    ]

    recovery_result = {
        "recovered": True,
        "attempted": True,
        "original_tool": "write_file",
        "failure": {
            "failed": True,
            "category": "execution_error",
        },
        "arguments": {
            "changed": False,
            "original_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "transformed_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
        },
        "execution": {
            "success": True,
            "tool": "write_file",
            "arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "result": "File written successfully.",
        },
    }

    monkeypatch.setattr(
        runtime.recovery_manager,
        "handle",
        lambda **kwargs: recovery_result,
    )

    monkeypatch.setattr(
        runtime,
        "needs_verification",
        lambda tool_name: True,
    )

    monkeypatch.setattr(
        runtime,
        "verify_tool_result",
        lambda tool_name, arguments, tool_result: {
            "status": "verified",
            "verification_tool": "read_file",
            "result": "hello",
        },
    )

    monkeypatch.setattr(
        runtime,
        "update_verification_state",
        lambda verification: None,
    )

    monkeypatch.setattr(
        runtime,
        "add_verification_context",
        lambda tool_name, verification: None,
    )

    monkeypatch.setattr(
        runtime,
        "verify_current_requirements",
        lambda: {
            "status": "passed",
            "passed": True,
            "all_passed": True,
            "total": 1,
            "passed_count": 1,
            "failed_count": 0,
            "results": [
                {
                    "type": "file_exists",
                    "path": "test.txt",
                    "passed": True,
                }
            ],
        },
    )

    result = runtime.attempt_tool_recovery(
        original_tool="write_file",
        arguments={
            "path": "test.txt",
            "content": "hello",
        },
        tool_result={
            "success": False,
            "error": "Execution failed.",
        },
    )

    assert result["attempted"] is True
    assert result["recovered"] is True

    assert result["verification"]["status"] == "verified"

    assert result["requirement_verification"]["status"] == "passed"

    assert result["requirement_verification"]["all_passed"] is True


def test_recovery_requirement_verification_failure_is_recorded(
    monkeypatch,
):
    runtime = AgentRuntime()

    runtime.task_state["requirements"] = [
        {
            "type": "contains",
            "path": "test.txt",
            "text": "expected",
        }
    ]

    recovery_result = {
        "recovered": True,
        "attempted": True,
        "original_tool": "write_file",
        "failure": {
            "failed": True,
            "category": "execution_error",
        },
        "arguments": {
            "changed": False,
            "original_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "transformed_arguments": {
                "path": "test.txt",
                "content": "hello",
            },
        },
        "execution": {
            "success": True,
            "tool": "write_file",
            "arguments": {
                "path": "test.txt",
                "content": "hello",
            },
            "result": "File written successfully.",
        },
    }

    monkeypatch.setattr(
        runtime.recovery_manager,
        "handle",
        lambda **kwargs: recovery_result,
    )

    monkeypatch.setattr(
        runtime,
        "needs_verification",
        lambda tool_name: True,
    )

    monkeypatch.setattr(
        runtime,
        "verify_tool_result",
        lambda tool_name, arguments, tool_result: {
            "status": "verified",
            "verification_tool": "read_file",
            "result": "hello",
        },
    )

    monkeypatch.setattr(
        runtime,
        "update_verification_state",
        lambda verification: None,
    )

    monkeypatch.setattr(
        runtime,
        "add_verification_context",
        lambda tool_name, verification: None,
    )

    monkeypatch.setattr(
        runtime,
        "verify_current_requirements",
        lambda: {
            "status": "failed",
            "passed": False,
            "all_passed": False,
            "total": 1,
            "passed_count": 0,
            "failed_count": 1,
            "results": [
                {
                    "type": "contains",
                    "path": "test.txt",
                    "text": "expected",
                    "passed": False,
                }
            ],
        },
    )

    result = runtime.attempt_tool_recovery(
        original_tool="write_file",
        arguments={
            "path": "test.txt",
            "content": "hello",
        },
        tool_result={
            "success": False,
            "error": "Execution failed.",
        },
    )

    assert result["attempted"] is True

    # Recovery Tool 本身執行成功
    assert result["recovered"] is True

    # Tool Verification 成功
    assert (
        result["verification"]["status"]
        == "verified"
    )

    # 但 Task Requirement 不符合
    assert (
        result["requirement_verification"]["status"]
        == "failed"
    )

    assert (
        result["requirement_verification"]["all_passed"]
        is False
    )

    assert (
        result["requirement_verification"]["failed_count"]
        == 1
    )