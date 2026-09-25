from agent.tool_runner import ToolRunner


def test_normalize_tool_call():
    runner = ToolRunner({})

    tool_call = {
        "function": {
            "name": "read_file",
            "arguments": {
                "path": "README.md",
            },
        }
    }

    result = runner.normalize_tool_call(tool_call)

    assert result["success"] is True
    assert result["tool"] == "read_file"
    assert result["arguments"] == {
        "path": "README.md",
    }


def test_normalize_empty_tool_call():
    runner = ToolRunner({})

    result = runner.normalize_tool_call({})

    assert result["success"] is False
    assert result["error"] == "invalid_tool_call"


def test_tool_constraint():
    def checker(tool_name):
        if tool_name == "read_file":
            return True, ""

        return False, f"Tool '{tool_name}' 不允許。"

    runner = ToolRunner(
        {},
        constraint_checker=checker,
    )

    allowed, message = runner.check_tool_constraint(
        "read_file",
    )

    assert allowed is True
    assert message == ""


def test_forbidden_tool_constraint():
    def checker(tool_name):
        if tool_name == "delete_file":
            return False, "Tool 'delete_file' 被禁止。"

        return True, ""

    runner = ToolRunner(
        {},
        constraint_checker=checker,
    )

    allowed, message = runner.check_tool_constraint(
        "delete_file",
    )

    assert allowed is False
    assert "被禁止" in message


def test_dispatch():
    def fake_tool(path):
        return f"read: {path}"

    runner = ToolRunner(
        {
            "read_file": fake_tool,
        }
    )

    result = runner.dispatch(
        "read_file",
        {
            "path": "README.md",
        },
    )

    assert result == "read: README.md"


def test_unknown_tool():
    runner = ToolRunner({})

    result = runner.dispatch(
        "unknown_tool",
        {},
    )

    assert result["success"] is False
    assert result["error"] == "unknown_tool"
    assert "未知 Tool" in result["message"]


def test_dispatch_exception():
    def broken_tool():
        raise RuntimeError("test error")

    runner = ToolRunner(
        {
            "broken_tool": broken_tool,
        }
    )

    result = runner.dispatch(
        "broken_tool",
        {},
    )

    assert result["success"] is False
    assert result["error"] == "tool_execution_failed"
    assert "Tool 執行失敗" in result["message"]
