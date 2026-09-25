from agent.recovery_manager import (
    RecoveryManager,
)


class FakeToolRunner:

    def __init__(self):
        self.calls = []

    def run(
        self,
        tool_name,
        arguments=None,
    ):
        self.calls.append(
            {
                "tool": tool_name,
                "arguments": arguments,
            }
        )

        return {
            "success": True,
            "result": "README content",
        }


def test_recovery_manager_no_failure():

    runner = FakeToolRunner()

    manager = RecoveryManager(
        runner,
    )

    result = manager.handle(
        original_tool="read_section",
        arguments={
            "path": "README.md",
            "heading": "Features",
        },
        tool_result={
            "success": True,
            "result": "content",
        },
        attempt_count=0,
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    assert runner.calls == []


def test_recovery_manager_read_section_to_read_file():

    runner = FakeToolRunner()

    manager = RecoveryManager(
        runner,
    )

    result = manager.handle(
        original_tool="read_section",
        arguments={
            "path": "README.md",
            "heading": "Features",
        },
        tool_result={
            "success": False,
            "error": "找不到指定的章節。",
        },
        attempt_count=0,
    )

    assert result["attempted"] is True
    assert result["recovered"] is True

    assert result["execution"]["tool"] == "read_file"

    assert runner.calls[0]["tool"] == "read_file"

    assert runner.calls[0]["arguments"] == {
        "path": "README.md",
    }


def test_recovery_manager_stops_after_limit():

    runner = FakeToolRunner()

    manager = RecoveryManager(
        runner,
    )

    result = manager.handle(
        original_tool="read_section",
        arguments={
            "path": "README.md",
            "heading": "Features",
        },
        tool_result={
            "success": False,
            "error": "找不到指定的章節。",
        },
        attempt_count=1,
    )

    assert result["attempted"] is False
    assert result["recovered"] is False

    assert runner.calls == []
