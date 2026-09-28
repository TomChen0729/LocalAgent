from tools.project_context import get_project_path

from agent.command_executor import CommandExecutor


def execute_command(
    program: str,
    arguments=None,
    timeout: int = 60,
):
    """
    執行受控開發工具命令。

    工作目錄（cwd）會自動跟隨目前的 project_context：
    - 若使用 --workdir 指定了專案目錄，命令在那個目錄執行。
    - 否則預設在 LocalAgent 自身目錄執行。

    Parameters
    ----------
    program:
        要執行的程式名稱（必須在白名單內）。

        例如：python、pytest、pip、npm、node

    arguments:
        命令參數列表。

        例如：

            ["--version"]
            ["-m", "pytest", "-q"]
            ["install", "-r", "requirements.txt"]

    timeout:
        最大執行秒數（預設 60 秒）。
    """

    executor = CommandExecutor(project_path=get_project_path())

    return executor.execute(
        program=program,
        arguments=arguments,
        timeout=timeout,
    )
