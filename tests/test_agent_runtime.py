from unittest.mock import MagicMock

import agent.runtime as runtime_module

from agent.runtime import (
    AgentRuntime,
)


def make_tool_call(
    tool_name,
    arguments,
):
    tool_call = MagicMock()

    tool_call.function.name = tool_name
    tool_call.function.arguments = arguments

    return tool_call


def make_response(
    content="",
    tool_calls=None,
):
    response = MagicMock()

    response.message.content = content
    response.message.tool_calls = tool_calls or []

    return response


# ==================================================
# Basic Runtime Tests
# ==================================================


def test_max_tool_calls(monkeypatch):

    agent = AgentRuntime()

    responses = []

    for i in range(25):

        responses.append(
            make_response(
                content="SUMMARY: 執行 Tool",
                tool_calls=[
                    make_tool_call(
                        "file_exists",
                        {"path": f"file_{i}.txt"},
                    )
                ],
            )
        )

    responses.append(make_response(content="完成"))

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: False,
    )

    result = agent.run("測試最大 Tool 次數")

    assert "最大 Tool 呼叫次數限制" in result

    assert agent.tool_call_count == runtime_module.MAX_TOOL_CALLS

    assert agent.task_state["status"] == "stopped"


def test_tool_error_result_is_preserved(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [
        make_response(
            content="SUMMARY: 嘗試讀取",
            tool_calls=[
                make_tool_call(
                    "read_file",
                    {"path": "missing.py"},
                )
            ],
        ),
        make_response(content="找不到檔案"),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    monkeypatch.setattr(
        runtime_module,
        "read_file",
        lambda *args, **kwargs: "錯誤：檔案不存在。",
    )

    result = agent.run("讀取不存在的檔案")

    assert "找不到檔案" in result

    assert agent.tool_history[0]["result"] == "錯誤：檔案不存在。"


def test_tool_error_recovery_loop(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [
        make_response(
            content="SUMMARY: 先讀取檔案",
            tool_calls=[
                make_tool_call(
                    "read_file",
                    {"path": "test.py"},
                )
            ],
        ),
        make_response(
            content="SUMMARY: 改用正確路徑",
            tool_calls=[
                make_tool_call(
                    "read_file",
                    {"path": "test/main.py"},
                )
            ],
        ),
        make_response(content="已完成"),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    def fake_read_file(
        path,
        start_line=None,
        end_line=None,
    ):

        if path == "test.py":

            return "錯誤：檔案不存在。"

        return "1: print('hello')"

    monkeypatch.setattr(
        runtime_module,
        "read_file",
        fake_read_file,
    )

    result = agent.run("讀取 main.py")

    assert result == "已完成"

    assert agent.tool_call_count == 2

    assert agent.task_state["status"] == "completed"


# ==================================================
# Tool History
# ==================================================


def test_tool_history_records_execution(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [
        make_response(
            content="SUMMARY: 確認檔案",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "hello.py"},
                )
            ],
        ),
        make_response(content="完成"),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: True,
    )

    agent.run("確認 hello.py")

    assert len(agent.tool_history) == 1

    assert agent.tool_history[0]["tool_name"] == "file_exists"

    assert agent.tool_history[0]["arguments"] == {"path": "hello.py"}


# ==================================================
# Repeated Tool Detection
# ==================================================


def test_repeated_tool_detection(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [
        make_response(
            content="SUMMARY: 讀取檔案",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "same.py"},
                )
            ],
        ),
        make_response(
            content="SUMMARY: 再次讀取",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "same.py"},
                )
            ],
        ),
        make_response(
            content="SUMMARY: 再次讀取",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "same.py"},
                )
            ],
        ),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: True,
    )

    result = agent.run("測試重複 Tool")

    assert "重複的 Tool 呼叫" in result

    assert agent.task_state["status"] == "stopped"


def test_different_tool_is_not_repeated(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [
        make_response(
            content="SUMMARY: 確認檔案",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "hello.py"},
                )
            ],
        ),
        make_response(
            content="SUMMARY: 讀取檔案",
            tool_calls=[
                make_tool_call(
                    "read_file",
                    {"path": "hello.py"},
                )
            ],
        ),
        make_response(content="完成"),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: True,
    )

    monkeypatch.setattr(
        runtime_module,
        "read_file",
        lambda *args, **kwargs: "1: hello",
    )

    result = agent.run("確認 hello.py")

    assert result == "完成"

    assert agent.task_state["status"] == "completed"


def test_different_arguments_are_not_repeated(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [
        make_response(
            content="SUMMARY: 確認第一個檔案",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "a.py"},
                )
            ],
        ),
        make_response(
            content="SUMMARY: 確認第二個檔案",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "b.py"},
                )
            ],
        ),
        make_response(content="完成"),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: True,
    )

    result = agent.run("確認兩個檔案")

    assert result == "完成"

    assert len(agent.tool_history) == 2


def test_repeated_tool_count():

    agent = AgentRuntime()

    agent.tool_history = [
        {
            "tool_name": "file_exists",
            "arguments": {"path": "a.py"},
            "result": True,
        },
        {
            "tool_name": "file_exists",
            "arguments": {"path": "a.py"},
            "result": True,
        },
        {
            "tool_name": "file_exists",
            "arguments": {"path": "a.py"},
            "result": True,
        },
    ]

    count = agent.get_repeated_tool_count(
        "file_exists",
        {"path": "a.py"},
    )

    assert count == 3


def test_repeated_tool_count_resets_after_different_tool():

    agent = AgentRuntime()

    agent.tool_history = [
        {
            "tool_name": "file_exists",
            "arguments": {"path": "a.py"},
            "result": True,
        },
        {
            "tool_name": "read_file",
            "arguments": {"path": "a.py"},
            "result": "hello",
        },
        {
            "tool_name": "file_exists",
            "arguments": {"path": "a.py"},
            "result": True,
        },
    ]

    count = agent.get_repeated_tool_count(
        "file_exists",
        {"path": "a.py"},
    )

    assert count == 1


# ==================================================
# Task State
# ==================================================


def test_task_state_starts_correctly(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [make_response(content="完成")]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    agent.run("測試 Task State")

    assert agent.task_state["user_input"] == "測試 Task State"

    assert agent.task_state["started_at"] is not None


def test_task_state_updates_after_tool(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [
        make_response(
            content="SUMMARY: 確認檔案",
            tool_calls=[
                make_tool_call(
                    "file_exists",
                    {"path": "hello.py"},
                )
            ],
        ),
        make_response(content="完成"),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: True,
    )

    agent.run("確認檔案")

    assert agent.task_state["tool_calls"] == 1

    assert agent.task_state["last_tool"] == "file_exists"

    assert agent.task_state["last_result"] is True


def test_task_state_finishes_correctly(
    monkeypatch,
):

    agent = AgentRuntime()

    responses = [make_response(content="完成")]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    result = agent.run("測試完成狀態")

    assert result == "完成"

    assert agent.task_state["status"] == "completed"

    assert agent.task_state["finished_at"] is not None


# ==================================================
# Phase 4.6
# Verification
# ==================================================


def test_needs_verification():

    agent = AgentRuntime()

    assert agent.needs_verification("write_file") is True

    assert agent.needs_verification("edit_file") is True

    assert agent.needs_verification("create_directory") is True

    assert agent.needs_verification("delete_file") is True

    assert agent.needs_verification("read_file") is False


def test_edit_file_verification(
    monkeypatch,
):

    agent = AgentRuntime()

    actual_content = '1: print("Hello World")'

    monkeypatch.setattr(
        runtime_module,
        "read_file",
        lambda *args, **kwargs: actual_content,
    )

    verification = agent.verify_tool_result(
        "edit_file",
        {
            "path": "hello.py",
            "old_text": "Hello",
            "new_text": "Hello World",
        },
        "檔案修改成功。",
    )

    assert verification["status"] == "verified"

    assert verification["verification_tool"] == "read_file"

    assert verification["result"] == actual_content


def test_write_file_verification_failure(
    monkeypatch,
):

    monkeypatch.setattr(
        runtime_module,
        "read_file",
        lambda *args, **kwargs: "錯誤：檔案不存在。",
    )

    agent = AgentRuntime()

    verification = agent.verify_tool_result(
        "write_file",
        {
            "path": "missing.py",
            "content": "hello",
        },
        "寫入成功。",
    )

    assert verification["status"] == "failed"

    assert verification["verification_tool"] == "read_file"


def test_create_directory_verification(
    monkeypatch,
):

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: True,
    )

    agent = AgentRuntime()

    verification = agent.verify_tool_result(
        "create_directory",
        {"path": "test"},
        "資料夾建立成功。",
    )

    assert verification["status"] == "verified"

    assert verification["verification_tool"] == "file_exists"


def test_create_directory_verification_failure(
    monkeypatch,
):

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: False,
    )

    agent = AgentRuntime()

    verification = agent.verify_tool_result(
        "create_directory",
        {"path": "test"},
        "資料夾建立成功。",
    )

    assert verification["status"] == "failed"


def test_delete_file_verification(
    monkeypatch,
):

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: False,
    )

    agent = AgentRuntime()

    verification = agent.verify_tool_result(
        "delete_file",
        {
            "path": "test.py",
            "confirm": True,
        },
        "刪除成功。",
    )

    assert verification["status"] == "verified"

    assert verification["verification_tool"] == "file_exists"


def test_delete_file_verification_failure(
    monkeypatch,
):

    monkeypatch.setattr(
        runtime_module,
        "file_exists",
        lambda path: True,
    )

    agent = AgentRuntime()

    verification = agent.verify_tool_result(
        "delete_file",
        {
            "path": "test.py",
            "confirm": True,
        },
        "刪除成功。",
    )

    assert verification["status"] == "failed"


def test_verification_state_updates():

    agent = AgentRuntime()

    verification = {
        "status": "verified",
        "verification_tool": "read_file",
        "result": ('1: print("Hello World")'),
    }

    agent.update_verification_state(verification)

    assert agent.task_state["verification_required"] is True

    assert agent.task_state["verification_status"] == "verified"

    assert agent.task_state["verification_tool"] == "read_file"

    assert agent.task_state["verification_result"] == '1: print("Hello World")'


def test_verification_context_is_added():

    agent = AgentRuntime()

    verification = {
        "status": "verified",
        "verification_tool": "read_file",
        "result": ('1: print("Hello World")'),
    }

    agent.add_verification_context(
        "edit_file",
        verification,
    )

    last_message = agent.messages[-1]

    assert last_message["role"] == "system"

    assert "VERIFICATION RESULT" in last_message["content"]

    assert "Hello World" in last_message["content"]


# ==================================================
# Phase 4.7
# Requirement Verification
# ==================================================


def test_requirement_state_updates():

    agent = AgentRuntime()

    agent.update_requirement_state(
        "passed",
        "需求已完成。",
    )

    assert agent.task_state["requirement_status"] == "passed"

    assert agent.task_state["requirement_result"] == "需求已完成。"


def test_requirement_state_can_be_failed():

    agent = AgentRuntime()

    agent.update_requirement_state(
        "failed",
        "缺少 message 宣告。",
    )

    assert agent.task_state["requirement_status"] == "failed"

    assert agent.task_state["requirement_result"] == "缺少 message 宣告。"


def test_requirement_state_can_be_pending():

    agent = AgentRuntime()

    agent.update_requirement_state(
        "pending",
        'return "Hello World"',
    )

    assert agent.task_state["requirement_status"] == "pending"


def test_requirement_verification_context():

    agent = AgentRuntime()

    agent.start_task("把 hello.py 修改成 Hello World")

    agent.add_requirement_verification_context('1: return "Hello World"')

    last_message = agent.messages[-1]

    assert last_message["role"] == "system"

    assert "REQUIREMENT VERIFICATION" in last_message["content"]

    assert "Hello World" in last_message["content"]


def test_requirement_verification_after_edit(
    monkeypatch,
    tmp_path,
):

    agent = AgentRuntime()

    # Phase 4.8：
    # Requirement Verifier 使用測試專用目錄
    monkeypatch.setattr(
        "requirements.verifier.get_project_path",
        lambda: tmp_path,
    )

    # 建立真實 hello.py
    test_file = tmp_path / "hello.py"

    test_file.write_text(
        'print("Hello")\n',
        encoding="utf-8",
    )

    responses = [
        make_response(
            content="SUMMARY: 修改檔案",
            tool_calls=[
                make_tool_call(
                    "edit_file",
                    {
                        "path": "hello.py",
                        "old_text": "Hello",
                        "new_text": "Hello World",
                    },
                )
            ],
        ),
        make_response(
            content=("已完成修改，" "並確認需求符合。"),
        ),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    def fake_edit_file(
        *args,
        **kwargs,
    ):

        # 同步更新真實測試檔案
        test_file.write_text(
            'print("Hello World")\n',
            encoding="utf-8",
        )

        return "檔案修改成功。"

    monkeypatch.setattr(
        runtime_module,
        "edit_file",
        fake_edit_file,
    )

    # Phase 4.6：
    # Tool Verification 仍然使用 Mock read_file
    monkeypatch.setattr(
        runtime_module,
        "read_file",
        lambda *args, **kwargs: '1: print("Hello World")',
    )

    result = agent.run("把 hello.py 的 Hello 改成 Hello World")

    assert "已完成修改" in result

    assert agent.task_state["verification_status"] == "verified"

    assert agent.task_state["requirement_status"] == "passed"

    assert agent.task_state["requirement_result"] == result


def test_requirement_recovery_loop(
    monkeypatch,
    tmp_path,
):

    agent = AgentRuntime()

    # Phase 4.8：
    # Requirement Verifier 使用測試專用目錄
    monkeypatch.setattr(
        "requirements.verifier.get_project_path",
        lambda: tmp_path,
    )

    # 建立真實 hello.py
    test_file = tmp_path / "hello.py"

    test_file.write_text(
        "return message\n",
        encoding="utf-8",
    )

    responses = [
        # 第一輪：只做部分修改
        make_response(
            content="SUMMARY: 修改檔案",
            tool_calls=[
                make_tool_call(
                    "edit_file",
                    {
                        "path": "hello.py",
                        "old_text": "return message",
                        "new_text": "return message",
                    },
                )
            ],
        ),
        # 第二輪：Recovery
        make_response(
            content="SUMMARY: 補上缺少的內容",
            tool_calls=[
                make_tool_call(
                    "edit_file",
                    {
                        "path": "hello.py",
                        "old_text": "return message",
                        "new_text": ('message = "Hello Agent"\n' "return message"),
                    },
                )
            ],
        ),
        # 最終回答
        make_response(
            content=("已完成所有要求，" "並確認實際內容。"),
        ),
    ]

    iterator = iter(responses)

    monkeypatch.setattr(
        runtime_module,
        "chat",
        lambda **kwargs: next(iterator),
    )

    call_count = {"value": 0}

    def fake_edit_file(
        *args,
        **kwargs,
    ):

        call_count["value"] += 1

        # 第一次修改：
        # 故意維持不完整狀態
        if call_count["value"] == 1:

            test_file.write_text(
                "return message\n",
                encoding="utf-8",
            )

        # 第二次修改：
        # Recovery 後完成需求
        else:

            test_file.write_text(
                'message = "Hello Agent"\n' "return message\n",
                encoding="utf-8",
            )

        return "檔案修改成功。"

    monkeypatch.setattr(
        runtime_module,
        "edit_file",
        fake_edit_file,
    )

    # Phase 4.6 Tool Verification：
    # 仍然使用 Mock read_file。
    def fake_read_file(
        *args,
        **kwargs,
    ):

        if call_count["value"] == 1:

            return "1: return message"

        return '1: message = "Hello Agent"\n' "2: return message"

    monkeypatch.setattr(
        runtime_module,
        "read_file",
        fake_read_file,
    )

    result = agent.run(
        "在 hello.py 新增 " 'message = "Hello Agent"，' "並讓 return 使用 message"
    )

    assert "已完成所有要求" in result

    assert agent.tool_call_count == 2

    assert agent.task_state["verification_status"] == "verified"

    assert agent.task_state["requirement_status"] == "passed"
