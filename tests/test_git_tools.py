import subprocess

import pytest

import tools.git_tools as git_tools


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """
    建立一個獨立的暫存 Git Repository。
    """

    monkeypatch.setattr(
        git_tools,
        "get_project_path",
        lambda: tmp_path,
    )

    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    return tmp_path


def test_git_status_empty_repository(git_repo):
    result = git_tools.git_status()

    assert result["success"] is True
    assert result["tool"] == "git_status"


def test_git_status_detects_modified_file(git_repo):
    file_path = git_repo / "test.txt"

    file_path.write_text(
        "hello",
        encoding="utf-8",
    )

    result = git_tools.git_status()

    assert result["success"] is True
    assert "test.txt" in result["status"]


def test_git_diff_detects_changes(git_repo):
    file_path = git_repo / "test.txt"

    file_path.write_text(
        "hello",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "add", "test.txt"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    file_path.write_text(
        "hello world",
        encoding="utf-8",
    )

    result = git_tools.git_diff()

    assert result["success"] is True
    assert "hello world" in result["diff"]


def test_git_log(git_repo):
    file_path = git_repo / "test.txt"

    file_path.write_text(
        "hello",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "add", "test.txt"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    result = git_tools.git_log(limit=10)

    assert result["success"] is True
    assert "initial commit" in result["log"]


def test_git_log_limit(git_repo):
    for index in range(3):
        file_path = git_repo / f"file{index}.txt"

        file_path.write_text(
            f"content {index}",
            encoding="utf-8",
        )

        subprocess.run(
            ["git", "add", "."],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            ["git", "commit", "-m", f"commit {index}"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True,
        )

    result = git_tools.git_log(limit=2)

    assert result["success"] is True

    lines = result["log"].splitlines()

    assert len(lines) == 2


def test_git_commit(git_repo):
    file_path = git_repo / "test.txt"

    file_path.write_text(
        "hello",
        encoding="utf-8",
    )

    result = git_tools.git_commit("add test file")

    assert result["success"] is True
    assert result["message"] == "add test file"

    log_result = git_tools.git_log()

    assert log_result["success"] is True
    assert "add test file" in log_result["log"]


def test_git_commit_empty_message(git_repo):
    result = git_tools.git_commit("")

    assert result["success"] is False
    assert result["error"] == "empty_commit_message"


def test_git_commit_invalid_message(git_repo):
    result = git_tools.git_commit(None)

    assert result["success"] is False
    assert result["error"] == "invalid_commit_message"


def test_git_tools_reject_non_git_repository(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        git_tools,
        "get_project_path",
        lambda: tmp_path,
    )

    result = git_tools.git_status()

    assert result["success"] is False
    assert result["error"] == "not_git_repository"
