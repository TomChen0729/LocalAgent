from pathlib import Path
import shutil
import subprocess
from typing import Optional


class CommandExecutor:
    """
    LocalAgent Command Executor。

    負責執行受控的開發工具命令。

    設計原則：

    1. 不使用 shell=True
    2. 只允許白名單中的 executable
    3. command 與 arguments 分開
    4. 限制 timeout
    5. 回傳 stdout / stderr / exit_code
    6. 所有命令都在 project_path 執行
    """

    ALLOWED_PROGRAMS = {
        # -------------------------------------------------------
        # Python
        # -------------------------------------------------------
        "python",
        "python3",
        "pytest",

        # -------------------------------------------------------
        # Package Management
        # -------------------------------------------------------
        "pip",
        "pip3",
        "uv",           # 高速 Python package manager

        # -------------------------------------------------------
        # Linter
        # -------------------------------------------------------
        "ruff",         # 快速 linter + formatter
        "flake8",
        "pylint",

        # -------------------------------------------------------
        # Type Checker
        # -------------------------------------------------------
        "mypy",
        "pyright",

        # -------------------------------------------------------
        # Formatter
        # -------------------------------------------------------
        "black",
        "isort",

        # -------------------------------------------------------
        # Build / Task Runner
        # -------------------------------------------------------
        "make",

        # -------------------------------------------------------
        # JavaScript / Node
        # -------------------------------------------------------
        "npm",
        "node",
        "npx",
        "yarn",
        "pnpm",

        # -------------------------------------------------------
        # PHP
        # -------------------------------------------------------
        "php",
        "composer",

        # -------------------------------------------------------
        # Other Languages
        # -------------------------------------------------------
        "cargo",        # Rust
        "go",           # Go
        "ruby",
        "bundle",       # Ruby Bundler

        # -------------------------------------------------------
        # Container
        # -------------------------------------------------------
        "docker",
        "docker-compose",
    }

    DEFAULT_TIMEOUT = 300   # pip/npm/docker 類操作預設 5 分鐘

    MAX_TIMEOUT = 600

    def __init__(
        self,
        project_path: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        project_path:
            命令執行的工作目錄。
        """

        if project_path is None:
            project_path = Path.cwd()

        self.project_path = Path(project_path).resolve()

    # ====================================================
    # Program Policy
    # ====================================================

    def is_allowed_program(
        self,
        program: str,
    ) -> bool:
        """
        檢查 executable 是否在允許清單中。
        """

        if not isinstance(program, str):
            return False

        program = program.strip()

        if not program:
            return False

        # 不允許帶路徑的 executable。
        #
        # 例如：
        #
        # C:\\Windows\\System32\\cmd.exe
        #
        # ./malicious.exe
        #
        # 都不允許。
        if "/" in program or "\\" in program:
            return False

        return program.lower() in {item.lower() for item in self.ALLOWED_PROGRAMS}

    # ====================================================
    # Program Resolution
    # ====================================================

    def resolve_program(
        self,
        program: str,
    ):
        """
        尋找系統 PATH 中的 executable。
        """

        if not self.is_allowed_program(program):
            return None

        return shutil.which(program)

    # ====================================================
    # Execute
    # ====================================================

    def execute(
        self,
        program: str,
        arguments=None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        執行受控命令。

        Parameters
        ----------
        program:
            例如：

                pytest
                python
                php
                npm
                composer
                docker

        arguments:
            list，例如：

                ["-q"]
                ["--version"]
                ["-m", "pytest", "-q"]

        timeout:
            最長執行秒數。

        Returns
        -------
        dict
            Structured command result。
        """

        # ====================================================
        # Validate Program
        # ====================================================

        if not isinstance(
            program,
            str,
        ):
            return {
                "success": False,
                "error": "invalid_program",
                "message": "program 必須是字串。",
                "program": program,
            }

        program = program.strip()

        if not program:
            return {
                "success": False,
                "error": "invalid_program",
                "message": "program 不可以是空字串。",
                "program": program,
            }

        if not self.is_allowed_program(program):
            return {
                "success": False,
                "error": "program_not_allowed",
                "message": (f"不允許執行程式：{program}"),
                "program": program,
                "allowed_programs": sorted(self.ALLOWED_PROGRAMS),
            }

        # ====================================================
        # Validate Arguments
        # ====================================================

        if arguments is None:
            arguments = []

        if not isinstance(
            arguments,
            list,
        ):
            return {
                "success": False,
                "error": "invalid_arguments",
                "message": "arguments 必須是 list。",
                "program": program,
            }

        # 所有 arguments 都必須是 primitive string。
        normalized_arguments = []

        for argument in arguments:

            if not isinstance(
                argument,
                str,
            ):
                return {
                    "success": False,
                    "error": "invalid_arguments",
                    "message": ("command arguments " "中的每個項目都必須是字串。"),
                    "program": program,
                }

            normalized_arguments.append(argument)

        # ====================================================
        # Validate Timeout
        # ====================================================

        if isinstance(timeout, bool):
            return {
                "success": False,
                "error": "invalid_timeout",
                "message": "timeout 必須是整數。",
                "program": program,
            }

        if not isinstance(
            timeout,
            int,
        ):
            return {
                "success": False,
                "error": "invalid_timeout",
                "message": "timeout 必須是整數。",
                "program": program,
            }

        if timeout <= 0:
            return {
                "success": False,
                "error": "invalid_timeout",
                "message": "timeout 必須大於 0。",
                "program": program,
            }

        if timeout > self.MAX_TIMEOUT:
            return {
                "success": False,
                "error": "timeout_too_large",
                "message": (f"timeout 不可以超過 " f"{self.MAX_TIMEOUT} 秒。"),
                "program": program,
            }

        # ====================================================
        # Validate Project Path
        # ====================================================

        if not self.project_path.exists():
            return {
                "success": False,
                "error": "project_not_found",
                "message": (f"Project path 不存在：" f"{self.project_path}"),
                "program": program,
            }

        if not self.project_path.is_dir():
            return {
                "success": False,
                "error": "project_not_directory",
                "message": (f"Project path 不是資料夾：" f"{self.project_path}"),
                "program": program,
            }

        # ====================================================
        # Resolve Executable
        # ====================================================

        executable = self.resolve_program(program)

        if executable is None:
            return {
                "success": False,
                "error": "program_not_found",
                "message": (f"系統 PATH 找不到程式：" f"{program}"),
                "program": program,
            }

        # ====================================================
        # Build Command
        # ====================================================

        command = [
            executable,
            *normalized_arguments,
        ]

        # ====================================================
        # Execute
        # ====================================================

        try:

            completed = subprocess.run(
                command,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                timeout=timeout,
            )

            return {
                "success": completed.returncode == 0,
                "error": (None if completed.returncode == 0 else "command_failed"),
                "message": (
                    "Command 執行成功。"
                    if completed.returncode == 0
                    else "Command 執行失敗。"
                ),
                "program": program,
                "arguments": normalized_arguments,
                "command": [
                    program,
                    *normalized_arguments,
                ],
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "timed_out": False,
                "working_directory": str(self.project_path),
            }

        except subprocess.TimeoutExpired as exc:

            stdout = exc.stdout or ""
            stderr = exc.stderr or ""

            if isinstance(stdout, bytes):
                stdout = stdout.decode(
                    "utf-8",
                    errors="replace",
                )

            if isinstance(stderr, bytes):
                stderr = stderr.decode(
                    "utf-8",
                    errors="replace",
                )

            return {
                "success": False,
                "error": "command_timeout",
                "message": (f"Command 執行超過 " f"{timeout} 秒，已終止。"),
                "program": program,
                "arguments": normalized_arguments,
                "command": [
                    program,
                    *normalized_arguments,
                ],
                "exit_code": None,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": True,
                "working_directory": str(self.project_path),
            }

        except FileNotFoundError:

            return {
                "success": False,
                "error": "program_not_found",
                "message": (f"無法啟動程式：{program}"),
                "program": program,
                "arguments": normalized_arguments,
            }

        except Exception as exc:

            return {
                "success": False,
                "error": "execution_error",
                "message": (f"Command 執行發生例外：{exc}"),
                "program": program,
                "arguments": normalized_arguments,
                "command": [
                    program,
                    *normalized_arguments,
                ],
                "exit_code": None,
                "stdout": "",
                "stderr": str(exc),
                "timed_out": False,
                "working_directory": str(self.project_path),
            }
