from agent.failure_classifier import FailureCategory
from agent.retry_policy import should_retry


class FakeRetryRuntime:
    """
    最小化的 Runtime 測試替身。

    這裡先不直接修改 AgentRuntime，
    只測試 Retry Orchestration 所需要的基本行為。
    """

    def __init__(self):
        self.retry_calls = []

    def retry_tool(
        self,
        tool_name,
        arguments,
        retry_count,
    ):
        self.retry_calls.append(
            {
                "tool": tool_name,
                "arguments": arguments,
                "retry_count": retry_count,
            }
        )

        return {
            "success": True,
            "result": "retry success",
        }


def test_retryable_failure_allows_retry():
    """
    Retryable Failure 應該允許 Retry。
    """

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=0,
    )

    assert decision.should_retry is True


def test_permission_denied_does_not_retry():
    """
    Permission Denied 不應該 Retry。
    """

    decision = should_retry(
        FailureCategory.PERMISSION_DENIED,
        retry_count=0,
    )

    assert decision.should_retry is False


def test_retry_limit_prevents_additional_retry():
    """
    達到 Retry Limit 後，不應該再 Retry。
    """

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=2,
    )

    assert decision.should_retry is False


def test_retry_keeps_original_tool_and_arguments():
    """
    Retry 必須重新執行原本的 Tool，
    不應該像 Recovery 一樣更換 Tool。
    """

    runtime = FakeRetryRuntime()

    tool_name = "read_file"

    arguments = {
        "path": "README.md",
    }

    result = runtime.retry_tool(
        tool_name=tool_name,
        arguments=arguments,
        retry_count=0,
    )

    assert result["success"] is True

    assert len(runtime.retry_calls) == 1

    retry_call = runtime.retry_calls[0]

    assert retry_call["tool"] == "read_file"

    assert retry_call["arguments"] == {
        "path": "README.md",
    }

    assert retry_call["retry_count"] == 0


class FakeToolRunner:
    """
    模擬 ToolRunner。

    第一次執行失敗，
    第二次執行成功。

    用來驗證 Runtime 是否真的會重新執行
    同一個 Tool。
    """

    def __init__(self):
        self.calls = []

    def run(
        self,
        tool_name,
        arguments,
    ):
        self.calls.append(
            {
                "tool": tool_name,
                "arguments": arguments,
            }
        )

        if len(self.calls) == 1:
            return {
                "success": False,
                "error": "找不到指定的檔案。",
            }

        return {
            "success": True,
            "result": "README content",
        }


def test_runtime_retry_reexecutes_same_tool():
    """
    Runtime Retry 應該重新執行原本的 Tool。

    第一次：
        read_file -> failure

    Retry：
        read_file -> success
    """

    tool_runner = FakeToolRunner()

    tool_name = "read_file"

    arguments = {
        "path": "README.md",
    }

    first_result = tool_runner.run(
        tool_name,
        arguments,
    )

    assert first_result["success"] is False

    failure_category = FailureCategory.NOT_FOUND

    decision = should_retry(
        failure_category,
        retry_count=0,
    )

    assert decision.should_retry is True

    second_result = tool_runner.run(
        tool_name,
        arguments,
    )

    assert second_result["success"] is True

    assert len(tool_runner.calls) == 2

    assert tool_runner.calls[0]["tool"] == "read_file"
    assert tool_runner.calls[1]["tool"] == "read_file"

    assert tool_runner.calls[0]["arguments"] == arguments
    assert tool_runner.calls[1]["arguments"] == arguments


def test_runtime_retry_does_not_change_tool_like_recovery():
    """
    Retry 與 Recovery 必須保持不同。

    Retry：
        read_section -> read_section

    Recovery：
        read_section -> read_file

    這個測試只驗證 Retry 不應該自行更換 Tool。
    """

    tool_runner = FakeToolRunner()

    original_tool = "read_section"

    arguments = {
        "path": "README.md",
        "heading": "Features",
    }

    first_result = tool_runner.run(
        original_tool,
        arguments,
    )

    assert first_result["success"] is False

    decision = should_retry(
        FailureCategory.NOT_FOUND,
        retry_count=0,
    )

    assert decision.should_retry is True

    tool_runner.run(
        original_tool,
        arguments,
    )

    assert len(tool_runner.calls) == 2

    assert tool_runner.calls[0]["tool"] == "read_section"
    assert tool_runner.calls[1]["tool"] == "read_section"
