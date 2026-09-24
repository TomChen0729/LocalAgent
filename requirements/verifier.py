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


def file_exists(path):
    """
    Requirement Verifier 專用的檔案存在檢查。

    注意：
    這裡刻意使用 verifier 自己的 get_project_path()，
    讓測試可以透過 monkeypatch 替換專案根目錄。
    """

    resolved_path = _resolve_project_path(path)

    if resolved_path is None:
        return False

    return resolved_path.is_file()


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
