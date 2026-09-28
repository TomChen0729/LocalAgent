import subprocess

# ============================================================
# Git Read-only Subcommands
#
# 這些 subcommand 不會修改 repository 狀態，
# Permission Layer 可以自動允許。
# ============================================================

GIT_READ_SUBCOMMANDS = {
    "status",
    "log",
    "diff",
    "show",
    "branch",
    "tag",
    "remote",
    "stash",
    "config",
    "shortlog",
    "describe",
    "rev-parse",
    "ls-files",
    "ls-tree",
    "grep",
    "blame",
    "reflog",
    "cat-file",
    "name-rev",
    "symbolic-ref",
    "rev-list",
    "for-each-ref",
}
from pathlib import Path

from tools.file_tools import get_project_path


def _run_git_command(args, timeout: int = 30):
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
            timeout=timeout,
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


def git_run(
    subcommand: str,
    args: list = None,
    timeout: int = None,
) -> dict:
    """
    執行任意 Git 子命令。

    這是通用的 Git CLI 介面，
    允許 Agent 執行目前 git_status / git_commit
    等個別工具未涵蓋的 Git 操作。

    例如：

        git_run("push", ["origin", "main"])
        git_run("branch", ["-a"])
        git_run("checkout", ["-b", "feature/new-feature"])
        git_run("stash", ["push", "-m", "WIP"])
        git_run("pull", ["origin", "main"])
        git_run("tag", ["-a", "v1.0.0", "-m", "Release 1.0.0"])
        git_run("reset", ["--soft", "HEAD~1"])
        git_run("merge", ["feature/branch"])

    安全設計：

        - 使用 _run_git_command，args 為 list，不使用 shell=True
        - subcommand 與 args 嚴格分離，避免 Shell Injection
        - 必須在含 .git/ 資料夾的 project_path 下執行
        - Permission Layer 會根據 subcommand 決定是否需要確認

    Parameters
    ----------
    subcommand:
        Git 子命令，例如 push、branch、checkout、pull。

    args:
        Git 子命令的參數，必須是 string list。
        例如 ["origin", "main"] 或 ["-b", "feature/xyz"]。

    timeout:
        最大執行秒數。
        預設：網路操作（pull/push/fetch/clone）為 120 秒，
              其他操作為 30 秒。
        最大值：600 秒。
    """

    # --------------------------------------------------------
    # 網路操作預設使用較長 timeout
    # --------------------------------------------------------

    NETWORK_SUBCOMMANDS = {
        "pull",
        "push",
        "fetch",
        "clone",
        "ls-remote",
        "remote",
    }

    DEFAULT_TIMEOUT = 30
    NETWORK_TIMEOUT = 120
    MAX_TIMEOUT = 600

    if not isinstance(subcommand, str):
        return {
            "success": False,
            "error": "invalid_subcommand",
            "message": "subcommand 必須是字串。",
        }

    subcommand = subcommand.strip()

    if not subcommand:
        return {
            "success": False,
            "error": "invalid_subcommand",
            "message": "subcommand 不可以是空字串。",
        }

    # 不允許 subcommand 中含空白（防止注入多個命令）
    if " " in subcommand:
        return {
            "success": False,
            "error": "invalid_subcommand",
            "message": (
                "subcommand 不可以包含空白字元。"
                "請將額外參數放入 args 清單。"
            ),
        }

    if args is None:
        args = []

    if not isinstance(args, list):
        return {
            "success": False,
            "error": "invalid_args",
            "message": "args 必須是 list。",
        }

    # 所有 args 必須是字串
    for index, arg in enumerate(args):
        if not isinstance(arg, str):
            return {
                "success": False,
                "error": "invalid_args",
                "message": (
                    f"args[{index}] 必須是字串，"
                    f"實際收到：{type(arg).__name__}"
                ),
            }

    git_args = [subcommand] + args

    # --------------------------------------------------------
    # 決定 timeout
    # --------------------------------------------------------

    if timeout is None:
        effective_timeout = (
            NETWORK_TIMEOUT
            if subcommand.lower() in NETWORK_SUBCOMMANDS
            else DEFAULT_TIMEOUT
        )
    else:
        try:
            effective_timeout = int(timeout)
        except (TypeError, ValueError):
            effective_timeout = DEFAULT_TIMEOUT

    effective_timeout = max(1, min(effective_timeout, MAX_TIMEOUT))

    result = _run_git_command(git_args, timeout=effective_timeout)

    if not result["success"]:
        return {
            **result,
            "tool": "git_run",
            "subcommand": subcommand,
            "args": args,
        }

    return {
        "success": True,
        "tool": "git_run",
        "subcommand": subcommand,
        "args": args,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "message": result["stdout"] or f"git {subcommand} 執行成功。",
    }
