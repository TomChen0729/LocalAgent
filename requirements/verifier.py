from pathlib import Path

from tools.file_tools import get_project_path


def _get_requirement_path(requirement):
    """
    取得 Requirement 的 path。
    """

    if not isinstance(requirement, dict):
        return None

    path = requirement.get("path")

    if not isinstance(path, str) or not path.strip():
        return None

    return path


def _resolve_project_path(path):
    """
    將 Requirement 路徑解析到目前專案目錄。

    保留 get_project_path() 在 module 層級，
    讓 pytest 可以 monkeypatch：
    requirements.verifier.get_project_path
    """

    project_path = Path(get_project_path()).resolve()
    target_path = (project_path / path).resolve()

    try:
        target_path.relative_to(project_path)
    except ValueError:
        return None

    return target_path


def _is_glob_pattern(path: str) -> bool:
    """判斷路徑是否為 glob pattern（含 * ? [ 字元）。"""
    return any(c in path for c in ("*", "?", "["))


def _glob_find_files(pattern: str) -> list:
    """
    在專案根目錄下找出符合 glob pattern 的所有檔案。

    安全設計：
    - 只在 project_path 內搜尋，不允許跳出
    - 回傳空 list 表示沒有符合的檔案

    Parameters
    ----------
    pattern : str
        glob pattern，例如 **/*.py、**/requirements.txt

    Returns
    -------
    list[Path] : 符合的路徑列表
    """
    project_path = Path(get_project_path()).resolve()

    try:
        matches = list(project_path.glob(pattern))
    except Exception:
        return []

    # 確保所有結果都在 project_path 內（安全防護）
    safe_matches = []
    for m in matches:
        try:
            m.resolve().relative_to(project_path)
            safe_matches.append(m)
        except ValueError:
            continue

    return safe_matches


def file_exists(path):
    """
    Requirement Verifier 專用的檔案存在檢查。

    支援兩種模式：

    1. 精確路徑：path = "src/main.py"
       → 直接解析並確認檔案或資料夾是否存在

    2. Glob 模式：path = "**/main.py" 或 "**/*.py"
       → 在整個專案目錄下搜尋，找到任一符合的檔案即通過

    注意：
    這裡刻意使用 verifier 自己的 get_project_path()，
    讓測試可以透過 monkeypatch 替換專案根目錄。
    """

    if _is_glob_pattern(path):
        return bool(_glob_find_files(path))

    resolved_path = _resolve_project_path(path)

    if resolved_path is None:
        return False

    if resolved_path.exists():
        return True

    # 沒有副檔名時，自動嘗試常見副檔名
    # 解決 parser 把 "README" → file_exists: "README"
    # 但實際建立 "README.md" 的情況
    if not resolved_path.suffix:
        for ext in (".md", ".txt", ".rst", ".html",
                    ".json", ".yaml", ".yml", ".toml"):
            if resolved_path.with_suffix(ext).exists():
                return True

    return False


def read_file(path):
    """
    Requirement Verifier 專用的檔案讀取。

    使用 verifier 自己的 project path，
    同時保留 sandbox path 檢查。
    """

    resolved_path = _resolve_project_path(path)

    if resolved_path is None:
        return "錯誤：檔案路徑超出專案範圍。"

    if not resolved_path.is_file():
        return f"錯誤：檔案不存在：{path}"

    try:
        return resolved_path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        return f"錯誤：無法以 UTF-8 讀取檔案：{path}"

    except OSError as exc:
        return f"錯誤：讀取檔案失敗：{exc}"


def verify_requirement(requirement):
    """
    驗證單一 Requirement。

    支援：

    - file_exists
    - contains
    - not_contains
    """

    if not isinstance(requirement, dict):
        return {
            "status": "failed",
            "type": None,
            "path": None,
            "message": "Requirement 必須是 dict。",
        }

    requirement_type = requirement.get("type")
    path = requirement.get("path")

    supported_types = {
        "file_exists",
        "contains",
        "not_contains",
    }

    if requirement_type not in supported_types:
        return {
            "status": "failed",
            "type": requirement_type,
            "path": path,
            "message": (f"不支援的 Requirement type：" f"{requirement_type}"),
        }

    if not isinstance(path, str) or not path.strip():
        return {
            "status": "failed",
            "type": requirement_type,
            "path": path,
            "message": "Requirement 缺少有效的 path。",
        }

    # --------------------------------------------------
    # Glob Pattern：跳過嚴格路徑解析，直接走 glob 分支
    # --------------------------------------------------

    is_glob = _is_glob_pattern(path)

    if not is_glob:
        resolved_path = _resolve_project_path(path)

        if resolved_path is None:
            return {
                "status": "failed",
                "type": requirement_type,
                "path": path,
                "message": "Requirement 路徑超出專案範圍。",
            }

    # --------------------------------------------------
    # file_exists
    # --------------------------------------------------

    if requirement_type == "file_exists":

        exists = file_exists(path)

        if exists:
            return {
                "status": "passed",
                "type": "file_exists",
                "path": path,
                "message": f"檔案存在：{path}",
            }

        return {
            "status": "failed",
            "type": "file_exists",
            "path": path,
            "message": f"檔案不存在：{path}",
        }

    # --------------------------------------------------
    # contains / not_contains
    # --------------------------------------------------

    if requirement_type in {
        "contains",
        "not_contains",
    }:

        text = requirement.get("text")

        if not isinstance(text, str):
            return {
                "status": "failed",
                "type": requirement_type,
                "path": path,
                "message": ("contains / not_contains " "Requirement 缺少有效的 text。"),
            }

        # --------------------------------------------------
        # Glob 模式：搜尋所有符合的檔案
        # --------------------------------------------------

        if is_glob:
            matches = _glob_find_files(path)

            if not matches:
                return {
                    "status": "failed",
                    "type": requirement_type,
                    "path": path,
                    "message": f"Glob 模式找不到符合的檔案：{path}",
                }

            # contains：任一個檔案包含 text 即通過
            # not_contains：所有找到的檔案都不包含 text 才通過
            found_in = None
            for match in matches:
                try:
                    file_content = match.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                    if text in file_content:
                        found_in = str(match)
                        break
                except Exception:
                    continue

            if requirement_type == "contains":
                if found_in:
                    return {
                        "status": "passed",
                        "type": "contains",
                        "path": path,
                        "message": f"找到包含 '{text}' 的檔案：{found_in}",
                    }
                return {
                    "status": "failed",
                    "type": "contains",
                    "path": path,
                    "message": f"Glob {path} 符合的所有檔案均不包含：{text}",
                }

            # not_contains
            if found_in:
                return {
                    "status": "failed",
                    "type": "not_contains",
                    "path": path,
                    "message": f"找到包含 '{text}' 的檔案（不應存在）：{found_in}",
                }
            return {
                "status": "passed",
                "type": "not_contains",
                "path": path,
                "message": f"Glob {path} 符合的所有檔案均不包含：{text}",
            }

        # --------------------------------------------------
        # 精確路徑：原本邏輯
        # --------------------------------------------------

        content = read_file(path)

        if isinstance(content, str) and content.startswith("錯誤："):
            return {
                "status": "failed",
                "type": requirement_type,
                "path": path,
                "message": content,
            }

        # --------------------------------------------------
        # contains
        # --------------------------------------------------

        if requirement_type == "contains":

            if text in content:
                return {
                    "status": "passed",
                    "type": "contains",
                    "path": path,
                    "message": (f"檔案 {path} " f"包含指定文字：{text}"),
                }

            return {
                "status": "failed",
                "type": "contains",
                "path": path,
                "message": (f"檔案 {path} " f"不包含指定文字：{text}"),
            }

        # --------------------------------------------------
        # not_contains
        # --------------------------------------------------

        if requirement_type == "not_contains":

            if text not in content:
                return {
                    "status": "passed",
                    "type": "not_contains",
                    "path": path,
                    "message": (f"檔案 {path} " f"不包含指定文字：{text}"),
                }

            return {
                "status": "failed",
                "type": "not_contains",
                "path": path,
                "message": (f"檔案 {path} " f"仍包含不應存在的文字：{text}"),
            }

    return {
        "status": "failed",
        "type": requirement_type,
        "path": path,
        "message": "Requirement 驗證失敗。",
    }


def verify_requirements(requirements):
    """
    驗證多個 Structured Requirements。

    回傳格式：

    {
        "status": "passed" / "failed",
        "passed": int,
        "failed": int,
        "total": int,
        "passed_count": int,
        "failed_count": int,
        "all_passed": bool,
        "results": list,
        "message": str,
    }
    """

    if not isinstance(requirements, list):
        return {
            "status": "failed",
            "passed": 0,
            "failed": 0,
            "total": 0,
            "passed_count": 0,
            "failed_count": 0,
            "all_passed": False,
            "results": [],
            "message": "Requirements 必須是 list。",
        }

    if not requirements:
        return {
            "status": "failed",
            "passed": 0,
            "failed": 0,
            "total": 0,
            "passed_count": 0,
            "failed_count": 0,
            "all_passed": False,
            "results": [],
            "message": "沒有可驗證的 Requirement。",
        }

    results = []

    passed_count = 0
    failed_count = 0

    for requirement in requirements:

        result = verify_requirement(requirement)

        results.append(result)

        if result["status"] == "passed":
            passed_count += 1
        else:
            failed_count += 1

    all_passed = failed_count == 0

    return {
        "status": ("passed" if all_passed else "failed"),
        # 舊測試契約：
        # passed = 通過數量
        "passed": passed_count,
        # 舊測試契約：
        # failed = 失敗數量
        "failed": failed_count,
        "total": len(requirements),
        # 語意更明確的新欄位
        "passed_count": passed_count,
        "failed_count": failed_count,
        # Phase 4.8 新增：
        # 是否全部通過
        "all_passed": all_passed,
        "results": results,
        "message": (
            "所有 Requirements 驗證通過。"
            if all_passed
            else ("Requirements 驗證失敗：" f"{failed_count} 個未通過。")
        ),
    }
