from pathlib import Path

from agent.command_executor import CommandExecutor


def get_project_path():
    """
    取得目前 LocalAgent 的專案根目錄。

    command_tools.py 位於：

        LocalAgent/
        └── tools/
            └── command_tools.py

    因此：

        Path(__file__).resolve().parent
            → LocalAgent/tools

        parent.parent
            → LocalAgent
    """

    return Path(__file__).resolve().parent.parent


def execute_command(
    program: str,
    arguments=None,
    timeout: int = 60,
):
    """
    執行受控開發工具命令。

    Parameters
    ----------
    program:
        要執行的程式。

        例如：

            python
            pytest
            php
            composer
            npm
            node
            docker

    arguments:
        命令參數。

        例如：

            ["--version"]

            ["-q"]

            ["-m", "pytest", "-q"]

    timeout:
        最大執行秒數。
    """

    executor = CommandExecutor(project_path=get_project_path())

    return executor.execute(
        program=program,
        arguments=arguments,
        timeout=timeout,
    )
