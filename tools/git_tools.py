import subprocess
from pathlib import Path

from tools.file_tools import get_project_path


def _run_git_command(args):
    """
    執行受控的 Git 指令。

    注意：
    這個函式不接受任意 command string，
    而是由上層傳入已經拆好的 Git arguments。

    例如：

        ["status", "--short"]

    而不是：

        "git status --short"

    這樣可以避免 Agent 直接注入任意 Shell 指令。
    """

    project_path = Path(get_project_path())

    if not project_path.exists():
        return {
            "success": False,
            "error": "project_path_not_found",
            "message": f"專案路徑不存在：{project_path}",
        }

    git_path = project_path / ".git"

    if not git_path.exists():
        return {
            "success": False,
            "error": "not_git_repository",
            "message": f"目前專案不是 Git Repository：{project_path}",
        }

    command = ["git"] + args

    try:
        result = subprocess.run(
            command,
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=30,
        )

    except FileNotFoundError:
        return {
            "success": False,
            "error": "git_not_installed",
            "message": "系統找不到 Git，請確認 Git 是否已安裝並加入 PATH。",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "git_timeout",
            "message": "Git 指令執行超過 30 秒，已停止執行。",
        }

    except Exception as exc:
        return {
            "success": False,
            "error": "git_execution_error",
            "message": str(exc),
        }

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        return {
            "success": False,
            "error": "git_command_failed",
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "message": stderr or stdout or "Git 指令執行失敗。",
        }

    return {
        "success": True,
        "returncode": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def git_status():
    """
    查看目前 Git Repository 狀態。
    """

    result = _run_git_command(
        [
            "status",
            "--short",
            "--branch",
        ]
    )

    if not result["success"]:
        return result

    output = result["stdout"]

    return {
        "success": True,
        "tool": "git_status",
        "status": output,
        "message": output if output else "目前 Git Repository 沒有任何變更。",
    }


def git_diff():
    """
    查看目前尚未 commit 的 Git 修改。
    """

    result = _run_git_command(
        [
            "diff",
        ]
    )

    if not result["success"]:
        return result

    output = result["stdout"]

    return {
        "success": True,
        "tool": "git_diff",
        "diff": output,
        "message": output if output else "目前沒有未提交的差異。",
    }


def git_log(limit=10):
    """
    查看最近的 Git Commit 歷史。

    limit:
        最多顯示幾筆 Commit。
    """

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return {
            "success": False,
            "error": "invalid_limit",
            "message": "limit 必須是整數。",
        }

    if limit < 1:
        return {
            "success": False,
            "error": "invalid_limit",
            "message": "limit 必須大於 0。",
        }

    if limit > 50:
        limit = 50

    result = _run_git_command(
        [
            "log",
            f"-{limit}",
            "--oneline",
            "--decorate",
        ]
    )

    if not result["success"]:
        return result

    output = result["stdout"]

    return {
        "success": True,
        "tool": "git_log",
        "log": output,
        "message": output if output else "目前沒有 Git Commit 歷史。",
    }


def git_commit(message):
    """
    建立 Git Commit。

    注意：
    這是會修改 Repository 狀態的高風險操作。

    PermissionManager 應該在 Runtime 層先確認權限，
    然後才允許呼叫這個 function。
    """

    if not isinstance(message, str):
        return {
            "success": False,
            "error": "invalid_commit_message",
            "message": "Commit message 必須是字串。",
        }

    message = message.strip()

    if not message:
        return {
            "success": False,
            "error": "empty_commit_message",
            "message": "Commit message 不可以是空字串。",
        }

    if len(message) > 200:
        return {
            "success": False,
            "error": "commit_message_too_long",
            "message": "Commit message 最多 200 個字元。",
        }

    result = _run_git_command(
        [
            "add",
            "-A",
        ]
    )

    if not result["success"]:
        return {
            **result,
            "tool": "git_commit",
            "step": "git_add",
        }

    result = _run_git_command(
        [
            "commit",
            "-m",
            message,
        ]
    )

    if not result["success"]:
        return {
            **result,
            "tool": "git_commit",
            "step": "git_commit",
        }

    return {
        "success": True,
        "tool": "git_commit",
        "message": message,
        "output": result["stdout"],
        "stderr": result["stderr"],
    }
