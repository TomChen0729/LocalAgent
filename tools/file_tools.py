from pathlib import Path
from typing import Optional
import os
import shutil
import tempfile

from tools.parsers.markdown_parser import extract_section
from tools.project_context import get_project_path
# ============================================================
# Project Sandbox
# ============================================================



# ============================================================
# Security
# ============================================================

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}


DEFAULT_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
DEFAULT_MAX_SEARCH_RESULTS = 200
DEFAULT_MAX_SEARCH_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def resolve_safe_path(path: str) -> tuple[Optional[Path], Optional[str]]:
    """
    將使用者提供的路徑轉換成安全的絕對路徑。

    所有 File Tools 都必須經過這個函式。

    防止：

        ../secret.txt
        ../../Windows/System32
        C:\\Users\\...
        D:\\...
        symlink escape

    Returns:
        (safe_path, None)
        或
        (None, error_message)
    """

    if not isinstance(path, str):
        return None, "錯誤：path 必須是字串。"

    path = path.strip()

    if not path:
        return None, "錯誤：path 不可以是空字串。"

    project_path = get_project_path()

    try:
        target_path = (project_path / path).resolve()

        target_path.relative_to(project_path)

    except ValueError:
        return None, "錯誤：禁止存取專案目錄以外的路徑。"

    except OSError as e:
        return None, f"錯誤：無法解析路徑：{e}"

    return target_path, None


def is_ignored_path(path: Path) -> bool:
    """
    判斷路徑是否位於不應被 Agent 操作的資料夾。
    """

    project_path = get_project_path()

    try:
        relative_path = path.relative_to(project_path)
    except ValueError:
        return True

    return any(part in IGNORED_DIRECTORIES for part in relative_path.parts)


def get_relative_path(path: Path) -> str:
    """
    將絕對路徑轉換成 Agent 可以理解的專案相對路徑。
    """

    project_path = get_project_path()

    return str(path.relative_to(project_path)).replace("\\", "/")


# ============================================================
# File Information
# ============================================================


def file_exists(path: str) -> str:
    """
    確認指定路徑是否存在。

    不修改任何檔案。
    """

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if not safe_path.exists():
        return f"不存在：{path}"

    if safe_path.is_file():
        return f"存在：{path}\n" f"類型：檔案"

    if safe_path.is_dir():
        return f"存在：{path}\n" f"類型：資料夾"

    return f"存在：{path}\n" f"類型：其他檔案系統物件"


# ============================================================
# List Files
# ============================================================


def list_files(
    path: str = ".",
    recursive: bool = False,
    include_hidden: bool = False,
) -> str:
    """
    列出指定資料夾內容。

    預設只列一層。
    recursive=True 才會遞迴。

    不會列出：
        .git
        .venv
        __pycache__
        node_modules
    """

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if not safe_path.exists():
        return f"錯誤：找不到路徑 {path}"

    if not safe_path.is_dir():
        return f"錯誤：{path} 不是資料夾。"

    if is_ignored_path(safe_path):
        return f"錯誤：禁止存取系統保護資料夾 {path}"

    results = []

    try:

        if recursive:
            iterator = safe_path.rglob("*")
        else:
            iterator = safe_path.iterdir()

        for item in sorted(
            iterator,
            key=lambda p: str(p).lower(),
        ):

            if is_ignored_path(item):
                continue

            if not include_hidden:

                if any(
                    part.startswith(".")
                    for part in item.relative_to(get_project_path()).parts
                ):
                    continue

            relative = get_relative_path(item)

            if item.is_dir():
                results.append(f"[DIR]  {relative}")

            elif item.is_file():
                results.append(f"[FILE] {relative}")

        if not results:
            return "資料夾是空的。"

        return "\n".join(results)

    except PermissionError:
        return f"錯誤：沒有權限讀取 {path}"

    except OSError as e:
        return f"錯誤：列出檔案時發生問題：{e}"


# ============================================================
# Read File
# ============================================================


def read_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_size: int = DEFAULT_MAX_FILE_SIZE,
) -> str:
    """
    讀取文字檔案。

    支援：

        read_file("main.py")

        read_file(
            "main.py",
            start_line=10,
            end_line=30
        )

    行號從 1 開始。

    預設限制檔案大小 2 MB。
    """

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if not safe_path.exists():
        return f"錯誤：找不到檔案 {path}"

    if not safe_path.is_file():
        return f"錯誤：{path} 不是檔案。"

    if is_ignored_path(safe_path):
        return f"錯誤：禁止讀取 {path}"

    try:

        file_size = safe_path.stat().st_size

        if file_size > max_size:
            return (
                f"錯誤：檔案過大，無法一次讀取。\n"
                f"檔案大小：{file_size:,} bytes\n"
                f"限制大小：{max_size:,} bytes\n"
                f"請使用 start_line / end_line 分段讀取。"
            )

        content = safe_path.read_text(encoding="utf-8")

        lines = content.splitlines()

        total_lines = len(lines)

        if start_line is None:
            start_line = 1

        if end_line is None:
            end_line = total_lines

        if start_line < 1:
            return "錯誤：start_line 必須大於等於 1。"

        if end_line < start_line:
            return "錯誤：end_line 不可以小於 start_line。"

        selected_lines = lines[start_line - 1 : end_line]

        if not selected_lines:
            return f"檔案共有 {total_lines} 行，" f"指定的範圍沒有內容。"

        numbered_lines = []

        for index, line in enumerate(
            selected_lines,
            start=start_line,
        ):
            numbered_lines.append(f"{index}: {line}")

        return "\n".join(numbered_lines)

    except UnicodeDecodeError:
        return f"錯誤：{path} 不是 UTF-8 " f"文字檔案，目前 File Tool 不支援此編碼。"

    except PermissionError:
        return f"錯誤：沒有權限讀取 {path}"

    except OSError as e:
        return f"錯誤：讀取檔案時發生問題：{e}"


# ============================================================
# Read Markdown Section
# ============================================================


def read_section(
    path: str,
    heading: str,
    max_size: int = DEFAULT_MAX_FILE_SIZE,
) -> str:
    """
    讀取 Markdown 檔案中的指定 Section。

    File Tool 負責：

        - Safe Path
        - File existence
        - File type
        - Ignored path
        - File size
        - UTF-8 reading

    Markdown Parser 負責：

        - Markdown Heading parsing
        - Heading normalization
        - Section boundary detection
        - Section extraction

    例如：

        read_section(
            "README.md",
            "Project Structure"
        )

    也可以使用：

        read_section(
            "README.md",
            "3. Project Structure"
        )

    或：

        read_section(
            "README.md",
            "## 3. Project Structure"
        )

    實際的 Markdown heading 會交給：

        tools/parsers/markdown_parser.py

    處理。
    """

    # --------------------------------------------------------
    # 1. Resolve safe path
    # --------------------------------------------------------

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    # --------------------------------------------------------
    # 2. Check file existence
    # --------------------------------------------------------

    if not safe_path.exists():
        return f"錯誤：找不到檔案 {path}"

    # --------------------------------------------------------
    # 3. Check whether path is a file
    # --------------------------------------------------------

    if not safe_path.is_file():
        return f"錯誤：{path} 不是檔案。"

    # --------------------------------------------------------
    # 4. Check ignored path
    # --------------------------------------------------------

    if is_ignored_path(safe_path):
        return f"錯誤：禁止讀取 {path}"

    # --------------------------------------------------------
    # 5. Validate heading
    # --------------------------------------------------------

    if not isinstance(heading, str):
        return "錯誤：heading 必須是字串。"

    heading = heading.strip()

    if not heading:
        return "錯誤：heading 不可以是空字串。"

    # --------------------------------------------------------
    # 6. Read file
    # --------------------------------------------------------

    try:

        file_size = safe_path.stat().st_size

        if file_size > max_size:
            return (
                "錯誤：檔案過大，無法讀取 Section。\n"
                f"檔案大小：{file_size:,} bytes\n"
                f"限制大小：{max_size:,} bytes"
            )

        content = safe_path.read_text(encoding="utf-8")

        # ----------------------------------------------------
        # 7. Delegate Markdown parsing
        # ----------------------------------------------------

        result = extract_section(
            content=content,
            heading=heading,
        )

        # ----------------------------------------------------
        # 8. Parser result
        # ----------------------------------------------------

        if result.startswith("錯誤："):
            return f"{result}\n" f"檔案：{path}"

        return result

    except UnicodeDecodeError:
        return f"錯誤：{path} 不是 UTF-8 " f"文字檔案，目前 File Tool 不支援此編碼。"

    except PermissionError:
        return f"錯誤：沒有權限讀取 {path}"

    except OSError as e:
        return f"錯誤：讀取 Section 時發生問題：{e}"


# ============================================================
# Write File
# ============================================================


def write_file(
    path: str,
    content: str,
    overwrite: bool = False,
) -> str:
    """
    建立文字檔案。

    預設禁止覆寫既有檔案。

    如果要覆寫：

        overwrite=True

    注意：
        父資料夾必須已經存在。
    """

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if is_ignored_path(safe_path):
        return f"錯誤：禁止寫入 {path}"

    existed_before = safe_path.exists()

    if existed_before:

        if not overwrite:
            return (
                f"錯誤：檔案 {path} 已存在。\n"
                f"write_file 預設禁止覆寫既有檔案。\n"
                f"如果確定要完整覆寫，"
                f"必須指定 overwrite=True。"
            )

        if not safe_path.is_file():
            return f"錯誤：{path} 不是檔案。"

    parent = safe_path.parent

    if not parent.exists():
        return f"錯誤：父資料夾不存在：" f"{get_relative_path(parent)}"

    if not isinstance(content, str):
        return "錯誤：content 必須是字串。"

    try:

        # ----------------------------------------------------
        # Atomic Write
        # ----------------------------------------------------
        #
        # 不直接：
        #
        # open(file, "w")
        #
        # 避免寫入過程中程式中斷造成檔案損壞。
        #
        # 先建立暫存檔，再 replace。
        # ----------------------------------------------------

        fd, temp_path = tempfile.mkstemp(
            dir=str(parent),
            prefix=".localagent_",
            suffix=".tmp",
            text=True,
        )

        try:

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
                newline="",
            ) as temp_file:

                temp_file.write(content)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(
                temp_path,
                safe_path,
            )

        finally:

            if os.path.exists(temp_path):

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        action = "覆寫" if existed_before else "建立"

        return (
            f"成功：已{action}檔案 {path}\n"
            f"大小："
            f"{len(content.encode('utf-8')):,} bytes"
        )

    except PermissionError:
        return f"錯誤：沒有權限寫入 {path}"

    except OSError as e:
        return f"錯誤：寫入檔案時發生問題：{e}"


# ============================================================
# Create Directory
# ============================================================


def create_directory(path: str) -> str:
    """
    建立資料夾。

    如果資料夾已存在，不視為錯誤。
    """

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if is_ignored_path(safe_path):
        return f"錯誤：禁止建立資料夾 {path}"

    try:

        if safe_path.exists():

            if safe_path.is_dir():
                return f"資料夾已存在：{path}"

            return f"錯誤：{path} 已存在，" f"但不是資料夾。"

        safe_path.mkdir(
            parents=True,
            exist_ok=False,
        )

        return f"成功：已建立資料夾 {path}"

    except PermissionError:
        return f"錯誤：沒有權限建立資料夾 {path}"

    except OSError as e:
        return f"錯誤：建立資料夾時發生問題：{e}"


# ============================================================
# Search Files
# ============================================================


def search_files(
    query: str,
    path: str = ".",
    file_pattern: str = "*",
    max_results: int = DEFAULT_MAX_SEARCH_RESULTS,
) -> str:
    """
    搜尋專案文字檔案內容。

    例如：

        search_files("SYSTEM_PROMPT")

        search_files(
            "def hello",
            path="test",
            file_pattern="*.py"
        )

    搜尋會忽略：

        .git
        .venv
        __pycache__
        node_modules

    遇到非 UTF-8 檔案會跳過。
    """

    if not isinstance(query, str):
        return "錯誤：query 必須是字串。"

    query = query.strip()

    if not query:
        return "錯誤：query 不可以是空字串。"

    if max_results <= 0:
        return "錯誤：max_results 必須大於 0。"

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if not safe_path.exists():
        return f"錯誤：找不到搜尋路徑 {path}"

    if not safe_path.is_dir():
        return f"錯誤：{path} 不是資料夾。"

    if is_ignored_path(safe_path):
        return f"錯誤：禁止搜尋 {path}"

    project_path = get_project_path()

    results = []

    query_lower = query.lower()

    try:

        for file_path in safe_path.rglob(file_pattern):

            if not file_path.is_file():
                continue

            if is_ignored_path(file_path):
                continue

            try:

                file_size = file_path.stat().st_size

                if file_size > DEFAULT_MAX_SEARCH_FILE_SIZE:
                    continue

                content = file_path.read_text(encoding="utf-8")

            except (
                UnicodeDecodeError,
                PermissionError,
                OSError,
            ):
                continue

            for (
                line_number,
                line,
            ) in enumerate(
                content.splitlines(),
                start=1,
            ):

                if query_lower in line.lower():

                    relative_path = str(file_path.relative_to(project_path)).replace(
                        "\\",
                        "/",
                    )

                    results.append(
                        f"{relative_path}:" f"{line_number}: " f"{line.strip()}"
                    )

                    if len(results) >= max_results:

                        return (
                            f"搜尋結果已達上限 "
                            f"{max_results} 筆。\n\n" + "\n".join(results)
                        )

        if not results:
            return f"找不到包含「{query}」" f"的內容。"

        return "\n".join(results)

    except OSError as e:
        return f"錯誤：搜尋檔案時發生問題：{e}"


# ============================================================
# Edit File
# ============================================================


def edit_file(
    path: str,
    old_text: str,
    new_text: str,
) -> str:
    """
    精確修改檔案。

    old_text 必須：

        恰好出現 1 次

    否則拒絕修改。

    修改前會：

        1. 讀取檔案
        2. 確認 old_text 存在
        3. 確認只出現一次
        4. 建立修改後內容
        5. Atomic Write

    不會直接進行多重 replace。
    """

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if not safe_path.exists():
        return f"錯誤：找不到檔案 {path}"

    if not safe_path.is_file():
        return f"錯誤：{path} 不是檔案。"

    if is_ignored_path(safe_path):
        return f"錯誤：禁止修改 {path}"

    if not isinstance(old_text, str):
        return "錯誤：old_text 必須是字串。"

    if not isinstance(new_text, str):
        return "錯誤：new_text 必須是字串。"

    if old_text == "":
        return "錯誤：old_text 不可以是空字串。"

    try:

        file_size = safe_path.stat().st_size

        if file_size > DEFAULT_MAX_FILE_SIZE:
            return (
                f"錯誤：檔案過大，"
                f"無法使用 edit_file。\n"
                f"檔案大小：{file_size:,} bytes"
            )

        content = safe_path.read_text(encoding="utf-8")

        occurrence_count = content.count(old_text)

        if occurrence_count == 0:
            return f"錯誤：在 {path} 中找不到 " f"old_text，未進行任何修改。"

        if occurrence_count > 1:
            return (
                f"錯誤：old_text 在 {path} "
                f"中出現 {occurrence_count} 次。\n"
                f"為避免錯誤修改，"
                f"未進行任何修改。"
            )

        new_content = content.replace(
            old_text,
            new_text,
            1,
        )

        # ----------------------------------------------------
        # Atomic Write
        # ----------------------------------------------------

        parent = safe_path.parent

        fd, temp_path = tempfile.mkstemp(
            dir=str(parent),
            prefix=".localagent_",
            suffix=".tmp",
            text=True,
        )

        try:

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
                newline="",
            ) as temp_file:

                temp_file.write(new_content)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(
                temp_path,
                safe_path,
            )

        finally:

            if os.path.exists(temp_path):

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        return f"成功：已修改 {path}\n" f"old_text 僅匹配 1 次，" f"已完成精確替換。"

    except UnicodeDecodeError:
        return f"錯誤：{path} 不是 UTF-8 " f"文字檔案。"

    except PermissionError:
        return f"錯誤：沒有權限修改 {path}"

    except OSError as e:
        return f"錯誤：修改檔案時發生問題：{e}"


# ============================================================
# Delete File
# ============================================================


def delete_file(
    path: str,
    confirm: bool = False,
) -> str:
    """
    刪除檔案。

    必須：

        confirm=True

    才會執行。

    不允許刪除資料夾。
    """

    if confirm is not True:
        return (
            "錯誤：delete_file 是高風險操作。\n"
            "必須明確指定 confirm=True "
            "才能刪除檔案。"
        )

    safe_path, error = resolve_safe_path(path)

    if error:
        return error

    if not safe_path.exists():
        return f"錯誤：找不到檔案 {path}"

    if not safe_path.is_file():
        return "錯誤：delete_file 只允許刪除檔案，" "不允許刪除資料夾。"

    if is_ignored_path(safe_path):
        return f"錯誤：禁止刪除 {path}"

    try:

        safe_path.unlink()

        return f"成功：已刪除檔案 {path}"

    except PermissionError:
        return f"錯誤：沒有權限刪除 {path}"

    except OSError as e:
        return f"錯誤：刪除檔案時發生問題：{e}"
