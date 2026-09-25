from agent.recovery_executor import (
    RecoveryExecutor,
)


class FakeToolRunner:

    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(
        self,
        tool_name,
        arguments,
    ):

        self.calls.append(
            (
                tool_name,
                arguments,
            )
        )

        return self.result


def test_execute_alternative_tool():

    runner = FakeToolRunner("README content")

    executor = RecoveryExecutor(
        runner,
    )

    result = executor.execute(
        "read_file",
        {
            "path": "README.md",
        },
    )

    assert result.success is True

    assert result.tool == "read_file"

    assert result.arguments == {
        "path": "README.md",
    }

    assert result.result == "README content"

    assert result.recovery is True

    assert runner.calls == [
        (
            "read_file",
            {
                "path": "README.md",
            },
        )
    ]


def test_execute_without_arguments():

    runner = FakeToolRunner("result")

    executor = RecoveryExecutor(
        runner,
    )

    result = executor.execute(
        "read_file",
    )

    assert result.success is True

    assert result.arguments == {}

    assert runner.calls == [
        (
            "read_file",
            {},
        )
    ]


def test_invalid_tool_name():

    runner = FakeToolRunner("result")

    executor = RecoveryExecutor(
        runner,
    )

    result = executor.execute(
        "",
        {},
    )

    assert result.success is False

    assert result.tool is None

    assert result.recovery is True

    assert runner.calls == []


def test_none_tool_name():

    runner = FakeToolRunner("result")

    executor = RecoveryExecutor(
        runner,
    )

    result = executor.execute(
        None,
        {},
    )

    assert result.success is False

    assert result.tool is None

    assert runner.calls == []


def test_failed_recovery():

    runner = FakeToolRunner(
        {
            "success": False,
            "error": "not_found",
            "message": "檔案不存在。",
        }
    )

    executor = RecoveryExecutor(
        runner,
    )

    result = executor.execute(
        "read_file",
        {
            "path": "missing.md",
        },
    )

    assert result.success is False

    assert result.tool == "read_file"

    assert result.recovery is True

    assert result.result["error"] == "not_found"


def test_execute_result_to_dict():

    runner = FakeToolRunner("content")

    executor = RecoveryExecutor(
        runner,
    )

    result = executor.execute(
        "read_file",
        {
            "path": "README.md",
        },
    )

    data = result.to_dict()

    assert data["success"] is True

    assert data["tool"] == "read_file"

    assert data["arguments"] == {
        "path": "README.md",
    }

    assert data["result"] == "content"

    assert data["recovery"] is True

    assert "message" in data
