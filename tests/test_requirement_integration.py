from agent.runtime import AgentRuntime
from requirements.verifier import verify_requirements


def test_runtime_requirement_state(monkeypatch):
    """
    確認 Runtime 可以保存結構化 Requirements。
    """

    agent = AgentRuntime()

    requirements = [
        {
            "type": "file_exists",
            "path": "test/hello.py",
        },
        {
            "type": "contains",
            "path": "test/hello.py",
            "text": "Hello",
        },
    ]

    agent.start_task("建立 test/hello.py")

    agent.set_structured_requirements(requirements)

    assert agent.task_state["requirements"] == requirements


def test_runtime_deterministic_requirement_pass(
    monkeypatch,
    tmp_path,
):
    """
    Requirement 全部符合時，應該得到 passed=True。
    """

    agent = AgentRuntime()

    monkeypatch.setattr(
        "requirements.verifier.get_project_path",
        lambda: tmp_path,
    )

    test_file = tmp_path / "hello.py"

    test_file.write_text(
        'message = "Hello Agent"\n',
        encoding="utf-8",
    )

    requirements = [
        {
            "type": "file_exists",
            "path": "hello.py",
        },
        {
            "type": "contains",
            "path": "hello.py",
            "text": "Hello Agent",
        },
    ]

    agent.start_task("確認 hello.py")

    agent.set_structured_requirements(requirements)

    result = agent.verify_current_requirements()

    assert result["passed"] is True


def test_runtime_deterministic_requirement_fail(
    monkeypatch,
    tmp_path,
):
    """
    Requirement 不符合時，應該得到 passed=False。
    """

    agent = AgentRuntime()

    monkeypatch.setattr(
        "requirements.verifier.get_project_path",
        lambda: tmp_path,
    )

    test_file = tmp_path / "hello.py"

    test_file.write_text(
        'message = "Hello"\n',
        encoding="utf-8",
    )

    requirements = [
        {
            "type": "file_exists",
            "path": "hello.py",
        },
        {
            "type": "contains",
            "path": "hello.py",
            "text": "Hello Agent",
        },
    ]

    agent.start_task("確認 hello.py")

    agent.set_structured_requirements(requirements)

    result = agent.verify_current_requirements()

    assert result["passed"] is False


def test_empty_requirements_do_not_pass():
    """
    沒有 Requirements 時，不應該把它當成 Requirement PASS。
    """

    agent = AgentRuntime()

    agent.start_task("沒有明確可驗證條件的需求")

    agent.set_structured_requirements([])

    result = agent.verify_current_requirements()

    assert result["status"] == "skipped"
    assert result["passed"] is False


def test_requirement_verifier_multiple_conditions(
    monkeypatch,
    tmp_path,
):
    """
    測試多個 Requirement 同時驗證。
    """

    monkeypatch.setattr(
        "requirements.verifier.get_project_path",
        lambda: tmp_path,
    )

    test_file = tmp_path / "demo.py"

    test_file.write_text(
        """
def hello():
    return "Hello Agent"
""",
        encoding="utf-8",
    )

    requirements = [
        {
            "type": "file_exists",
            "path": "demo.py",
        },
        {
            "type": "contains",
            "path": "demo.py",
            "text": 'return "Hello Agent"',
        },
        {
            "type": "not_contains",
            "path": "demo.py",
            "text": 'return "Goodbye"',
        },
    ]

    result = verify_requirements(requirements)

    assert result["passed"] == 3
    assert result["failed"] == 0
    assert result["all_passed"] is True
