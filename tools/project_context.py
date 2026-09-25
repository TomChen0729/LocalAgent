from contextvars import ContextVar
from pathlib import Path

_DEFAULT_PROJECT_PATH = Path(__file__).resolve().parents[1]


_project_path_context = ContextVar(
    "localagent_project_path",
    default=_DEFAULT_PROJECT_PATH,
)


def get_project_path() -> Path:
    """
    取得目前 Agent 執行環境的 Project Root。

    如果 Runtime 沒有指定 Project Root，
    預設使用 LocalAgent 專案根目錄。
    """

    return _project_path_context.get()


def set_project_path(
    project_path,
) -> Path:
    """
    設定目前執行 Context 的 Project Root。

    回傳設定後的絕對路徑。
    """

    path = Path(
        project_path,
    ).resolve()

    _project_path_context.set(
        path,
    )

    return path


def reset_project_path(
    token,
) -> None:
    """
    還原先前的 Project Root Context。
    """

    _project_path_context.reset(
        token,
    )


def push_project_path(
    project_path,
):
    """
    暫時切換 Project Root。

    回傳 Context Token，
    可以交給 reset_project_path() 還原。
    """

    path = Path(
        project_path,
    ).resolve()

    return _project_path_context.set(
        path,
    )


__all__ = [
    "get_project_path",
    "set_project_path",
    "reset_project_path",
    "push_project_path",
]
