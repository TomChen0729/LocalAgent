from pathlib import Path

from agent.runtime import AgentRuntime


def create_e2e_runtime(tmp_path):
    return AgentRuntime(
        project_path=Path(tmp_path),
    )


def test_read_section_failure_recovers_to_read_file(
    tmp_path,
):
    """
    E2E：

        read_section
            ↓
        Failure
            ↓
        Failure Classification
            ↓
        Recovery Policy
            ↓
        Recovery Selection
            ↓
        Argument Transformation
            ↓
        Recovery Executor
            ↓
        ToolRunner
            ↓
        read_file
            ↓
        Recovery Success
    """

    # --------------------------------------------------
    # 1. 建立測試檔案
    # --------------------------------------------------

    readme = tmp_path / "README.md"

    readme.write_text(
        "# Test Project\n\n" "## Features\n\n" "LocalAgent supports recovery.\n",
        encoding="utf-8",
    )

    # --------------------------------------------------
    # 2. 建立真正的 AgentRuntime
    # --------------------------------------------------

    runtime = create_e2e_runtime(
        tmp_path,
    )

    # --------------------------------------------------
    # 3. 直接使用真正的 read_section Tool
    #
    # 故意指定不存在的 Section，
    # 讓原始 Tool 發生 Failure。
    # --------------------------------------------------

    original_result = runtime.execute_tool(
        "read_section",
        {
            "path": "README.md",
            "heading": "Missing Section",
        },
    )

    # --------------------------------------------------
    # 4. 確認原始 Tool 確實失敗
    # --------------------------------------------------

    assert isinstance(
        original_result,
        str,
    )

    assert (
        "找不到" in original_result
        or "不存在" in original_result
        or "not found" in original_result.lower()
    )

    # --------------------------------------------------
    # 5. 啟動真正的 Recovery Pipeline
    #
    # 不 Mock RecoveryManager
    # --------------------------------------------------

    recovery_result = runtime.attempt_tool_recovery(
        original_tool="read_section",
        arguments={
            "path": "README.md",
            "heading": "Missing Section",
        },
        tool_result=original_result,
    )

    # --------------------------------------------------
    # 6. Recovery 必須真的被執行
    # --------------------------------------------------

    assert recovery_result["attempted"] is True

    # --------------------------------------------------
    # 7. Recovery 必須成功
    # --------------------------------------------------

    assert recovery_result["recovered"] is True

    # --------------------------------------------------
    # 8. Failure Classification
    #
    # 原始 read_section 的失敗
    # 應該被分類成 NOT_FOUND
    # --------------------------------------------------

    assert recovery_result["failure"]["category"] == "not_found"

    # --------------------------------------------------
    # 9. Recovery Policy
    #
    # read_section 的替代 Tool
    # 應該是 read_file
    # --------------------------------------------------

    assert recovery_result["selection"]["selected_tool"] == "read_file"

    # --------------------------------------------------
    # 10. Argument Transformation
    #
    # read_section:
    #
    # {
    #     path,
    #     heading
    # }
    #
    # ↓
    #
    # read_file:
    #
    # {
    #     path
    # }
    # --------------------------------------------------

    transformed_arguments = recovery_result["arguments"]["transformed_arguments"]

    assert transformed_arguments == {
        "path": "README.md",
    }

    # --------------------------------------------------
    # 11. Recovery Executor / ToolRunner
    #
    # 最終真的執行 read_file
    # --------------------------------------------------

    assert recovery_result["execution"]["tool"] == "read_file"

    assert recovery_result["execution"]["success"] is True

    # --------------------------------------------------
    # 12. 確認真的讀到了檔案
    # --------------------------------------------------

    recovered_content = recovery_result["execution"]["result"]

    assert isinstance(
        recovered_content,
        str,
    )

    assert "LocalAgent supports recovery." in recovered_content

    # --------------------------------------------------
    # 13. Runtime State
    #
    # Recovery Attempt 應該被記錄
    # --------------------------------------------------

    assert runtime.task_state["recovery_attempt_count"] == 1

    assert runtime.task_state["last_recovery_tool"] == "read_file"

    assert runtime.task_state["last_recovery_category"] == "not_found"

    # --------------------------------------------------
    # 14. Recovery Result 應該被記錄
    # --------------------------------------------------

    assert runtime.task_state["last_recovery_result"]["tool"] == "read_file"
