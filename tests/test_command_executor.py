from agent.command_executor import CommandExecutor


def test_allowed_program():
    executor = CommandExecutor()

    assert executor.is_allowed_program("python")

    assert executor.is_allowed_program("pytest")

    assert executor.is_allowed_program("php")


def test_disallowed_program():
    executor = CommandExecutor()

    assert not executor.is_allowed_program("powershell")

    assert not executor.is_allowed_program("cmd")

    assert not executor.is_allowed_program("bash")


def test_program_path_is_disallowed():
    executor = CommandExecutor()

    assert not executor.is_allowed_program("C:\\Windows\\System32\\cmd.exe")

    assert not executor.is_allowed_program("./malicious.exe")


def test_invalid_program():
    executor = CommandExecutor()

    result = executor.execute(
        program="",
    )

    assert result["success"] is False
    assert result["error"] == "invalid_program"


def test_disallowed_program_execution():
    executor = CommandExecutor()

    result = executor.execute(
        program="powershell",
    )

    assert result["success"] is False
    assert result["error"] == "program_not_allowed"


def test_invalid_arguments():
    executor = CommandExecutor()

    result = executor.execute(
        program="python",
        arguments="--version",
    )

    assert result["success"] is False
    assert result["error"] == "invalid_arguments"


def test_invalid_timeout():
    executor = CommandExecutor()

    result = executor.execute(
        program="python",
        timeout=0,
    )

    assert result["success"] is False
    assert result["error"] == "invalid_timeout"


def test_timeout_too_large():
    executor = CommandExecutor()

    result = executor.execute(
        program="python",
        timeout=601,
    )

    assert result["success"] is False
    assert result["error"] == "timeout_too_large"


def test_python_version():
    executor = CommandExecutor()

    result = executor.execute(
        program="python",
        arguments=["--version"],
    )

    assert result["success"] is True
    assert result["exit_code"] == 0
    assert result["timed_out"] is False
    assert "Python" in result["stdout"] or "Python" in result["stderr"]


def test_python_command_failure():
    executor = CommandExecutor()

    result = executor.execute(
        program="python",
        arguments=[
            "-c",
            "raise SystemExit(1)",
        ],
    )

    assert result["success"] is False
    assert result["error"] == "command_failed"
    assert result["exit_code"] == 1
    assert result["timed_out"] is False


def test_working_directory():
    executor = CommandExecutor()

    result = executor.execute(
        program="python",
        arguments=[
            "-c",
            "import os; print(os.getcwd())",
        ],
    )

    assert result["success"] is True

    output = result["stdout"].strip()

    assert output
    assert output.lower() == str(executor.project_path).lower()
