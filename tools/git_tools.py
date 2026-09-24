import subprocess
from pathlib import Path

# ============================================================

# 取得 LocalAgent 專案根目錄

# ============================================================

def get_project_path():
"""
取得 LocalAgent 專案根目錄。
"""


return Path(__file__).parent.parent.resolve()


# ============================================================

# 執行 Git 指令

# ============================================================

def run_git_command(arguments):
"""
在 LocalAgent 專案目錄中執行 Git 指令。

```
例如：

    run_git_command(["status"])

等同於：

    git status
"""

project_path = get_project_path()

try:

    result = subprocess.run(
        ["git"] + arguments,
        cwd=project_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output = result.stdout.strip()
    error = result.stderr.strip()

    if result.returncode != 0:

        return (
            f"Git 指令執行失敗。\n"
            f"指令：git {' '.join(arguments)}\n"
            f"錯誤：{error}"
        )

    if output:

        return output

    return "Git 指令執行成功，但沒有輸出。"

except FileNotFoundError:

    return (
        "錯誤：找不到 Git。\n"
        "請確認 Git 是否已安裝並加入 PATH。"
    )

except Exception as e:

    return f"執行 Git 指令時發生錯誤：{e}"
```

# ============================================================

# Tool：Git Status

# ============================================================

def git_status():
"""
查看目前 Git Repository 的狀態。

```
等同於：

    git status
"""

return run_git_command(
    ["status", "--short", "--branch"]
)
