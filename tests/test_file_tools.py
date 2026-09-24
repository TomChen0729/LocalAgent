import pytest

from tools.file_tools import (
    list_files,
    file_exists,
    read_file,
    write_file,
    create_directory,
    search_files,
    edit_file,
    delete_file,
)

# ============================================================
# 1. 建立測試環境
# ============================================================


@pytest.fixture
def test_directory(tmp_path, monkeypatch):
    """
    建立 pytest 專用的暫存目錄。

    每一次測試都會取得一個新的暫存目錄，
    避免測試互相污染。
    """

    monkeypatch.setattr("tools.file_tools.get_project_path", lambda: tmp_path)

    return tmp_path


# ============================================================
# 2. create_directory
# ============================================================


def test_create_directory(test_directory):

    result = create_directory("test_folder")

    assert "成功" in result

    assert (test_directory / "test_folder").exists()

    assert (test_directory / "test_folder").is_dir()


# ============================================================
# 3. file_exists
# ============================================================


def test_file_exists(test_directory):

    file_path = test_directory / "hello.txt"

    file_path.write_text("Hello Agent", encoding="utf-8")

    result = file_exists("hello.txt")

    assert "存在" in result


# ============================================================
# 4. write_file
# ============================================================


def test_write_file(test_directory):

    result = write_file("hello.txt", "Hello Agent")

    assert "成功" in result

    file_path = test_directory / "hello.txt"

    assert file_path.exists()

    assert file_path.read_text(encoding="utf-8") == "Hello Agent"


# ============================================================
# 5. write_file 禁止覆寫
# ============================================================


def test_write_file_without_overwrite(test_directory):

    file_path = test_directory / "hello.txt"

    file_path.write_text("Original", encoding="utf-8")

    result = write_file("hello.txt", "Modified")

    assert "已存在" in result

    assert file_path.read_text(encoding="utf-8") == "Original"


# ============================================================
# 6. write_file overwrite=True
# ============================================================


def test_write_file_with_overwrite(test_directory):

    file_path = test_directory / "hello.txt"

    file_path.write_text("Original", encoding="utf-8")

    result = write_file("hello.txt", "Modified", overwrite=True)

    assert "成功" in result

    assert file_path.read_text(encoding="utf-8") == "Modified"


# ============================================================
# 7. read_file
# ============================================================


def test_read_file(test_directory):

    file_path = test_directory / "hello.py"

    file_path.write_text("def hello():\n" '    return "Hello"\n', encoding="utf-8")

    result = read_file("hello.py")

    assert "1: def hello():" in result
    assert '2:     return "Hello"' in result


# ============================================================
# 8. read_file 行號範圍
# ============================================================


def test_read_file_line_range(test_directory):

    file_path = test_directory / "hello.py"

    file_path.write_text("line1\n" "line2\n" "line3\n" "line4\n", encoding="utf-8")

    result = read_file("hello.py", start_line=2, end_line=3)

    assert "2: line2" in result
    assert "3: line3" in result

    assert "1: line1" not in result
    assert "4: line4" not in result


# ============================================================
# 9. edit_file 正常修改
# ============================================================


def test_edit_file(test_directory):

    file_path = test_directory / "hello.py"

    file_path.write_text("def hello():\n" '    return "Hello"\n', encoding="utf-8")

    result = edit_file("hello.py", 'return "Hello"', 'return "Hi"')

    assert "成功" in result

    content = file_path.read_text(encoding="utf-8")

    assert 'return "Hi"' in content
    assert 'return "Hello"' not in content


# ============================================================
# 10. edit_file：old_text 不存在
# ============================================================


def test_edit_file_missing_text(test_directory):

    file_path = test_directory / "hello.py"

    file_path.write_text("def hello():\n" '    return "Hello"\n', encoding="utf-8")

    result = edit_file("hello.py", 'return "Goodbye"', 'return "Hi"')

    assert "找不到 old_text" in result

    content = file_path.read_text(encoding="utf-8")

    assert 'return "Hello"' in content


# ============================================================
# 11. edit_file：old_text 重複
# ============================================================


def test_edit_file_duplicate_text(test_directory):

    file_path = test_directory / "hello.py"

    file_path.write_text('print("Hello")\n' 'print("Hello")\n', encoding="utf-8")

    result = edit_file("hello.py", 'print("Hello")', 'print("Hi")')

    assert "出現 2 次" in result

    content = file_path.read_text(encoding="utf-8")

    assert content.count('print("Hello")') == 2


# ============================================================
# 12. search_files
# ============================================================


def test_search_files(test_directory):

    (test_directory / "a.py").write_text(
        "def hello():\n" '    return "Hello"\n', encoding="utf-8"
    )

    (test_directory / "b.py").write_text(
        "def goodbye():\n" '    return "Bye"\n', encoding="utf-8"
    )

    result = search_files("hello")

    assert "a.py" in result
    assert "hello" in result


# ============================================================
# 13. Sandbox Path Traversal
# ============================================================


def test_path_traversal_is_blocked(test_directory):

    result = read_file("../outside.txt")

    assert "錯誤" in result


# ============================================================
# 14. delete_file 沒有 confirm
# ============================================================


def test_delete_file_requires_confirmation(test_directory):

    file_path = test_directory / "delete_me.txt"

    file_path.write_text("Delete me", encoding="utf-8")

    result = delete_file("delete_me.txt", confirm=False)

    assert "confirm" in result

    assert file_path.exists()


# ============================================================
# 15. delete_file confirm=True
# ============================================================


def test_delete_file(test_directory):

    file_path = test_directory / "delete_me.txt"

    file_path.write_text("Delete me", encoding="utf-8")

    result = delete_file("delete_me.txt", confirm=True)

    assert "成功" in result

    assert not file_path.exists()


# ============================================================
# 16. list_files
# ============================================================


def test_list_files(test_directory):

    (test_directory / "hello.py").write_text("print('Hello')", encoding="utf-8")

    (test_directory / "folder").mkdir()

    result = list_files()

    assert "hello.py" in result
    assert "folder" in result
