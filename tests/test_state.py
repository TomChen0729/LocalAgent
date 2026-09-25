from agent.state import (
    create_task_state,
    start_task,
    finish_task,
    update_task_state,
)


def test_create_task_state():

    state = create_task_state()

    assert state["status"] == "idle"
    assert state["user_input"] is None
    assert state["started_at"] is None
    assert state["finished_at"] is None

    assert state["tool_calls"] == 0
    assert state["last_tool"] is None
    assert state["last_result"] is None

    assert state["requirements"] == []

    assert state["requirement_failure_count"] == 0
    assert state["requirement_progress_since_failure"] is False

    assert state["output_verification_failure_count"] == 0


def test_start_task():

    state = create_task_state()

    start_task(
        state,
        "建立 test.txt",
    )

    assert state["status"] == "running"
    assert state["user_input"] == "建立 test.txt"
    assert state["started_at"] is not None


def test_finish_task():

    state = create_task_state()

    start_task(
        state,
        "建立 test.txt",
    )

    finish_task(
        state,
        "completed",
    )

    assert state["status"] == "completed"
    assert state["finished_at"] is not None


def test_update_task_state():

    state = create_task_state()

    update_task_state(
        state,
        3,
        "write_file",
        "寫入成功",
    )

    assert state["tool_calls"] == 3
    assert state["last_tool"] == "write_file"
    assert state["last_result"] == "寫入成功"


def test_start_task_resets_previous_state():

    state = create_task_state()

    state["tool_calls"] = 10
    state["requirements"] = [
        {
            "type": "file_exists",
            "path": "test.txt",
        }
    ]

    start_task(
        state,
        "新的 Task",
    )

    assert state["status"] == "running"
    assert state["user_input"] == "新的 Task"

    assert state["tool_calls"] == 0
    assert state["requirements"] == []

    assert state["last_tool"] is None
    assert state["last_result"] is None
