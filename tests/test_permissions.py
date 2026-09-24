from agent.permissions import PermissionManager


def test_read_permission_is_allowed():
    manager = PermissionManager()

    result = manager.check_permission(
        "read_file",
        {
            "path": "hello.py",
        },
    )

    assert result.allowed is True
    assert result.action == "read"


def test_list_files_permission_is_allowed():
    manager = PermissionManager()

    result = manager.check_permission(
        "list_files",
        {
            "path": ".",
        },
    )

    assert result.allowed is True
    assert result.action == "read"


def test_write_without_callback_is_denied():
    manager = PermissionManager()

    result = manager.check_permission(
        "write_file",
        {
            "path": "hello.py",
            "content": "Hello",
        },
    )

    assert result.allowed is False
    assert result.action == "write"


def test_edit_without_callback_is_denied():
    manager = PermissionManager()

    result = manager.check_permission(
        "edit_file",
        {
            "path": "hello.py",
            "old_text": "Hello",
            "new_text": "Hello Agent",
        },
    )

    assert result.allowed is False
    assert result.action == "edit"


def test_delete_without_callback_is_denied():
    manager = PermissionManager()

    result = manager.check_permission(
        "delete_file",
        {
            "path": "hello.py",
            "confirm": True,
        },
    )

    assert result.allowed is False
    assert result.action == "delete"


def test_write_can_be_allowed():
    manager = PermissionManager(
        permission_callback=lambda tool, action, args: True,
    )

    result = manager.check_permission(
        "write_file",
        {
            "path": "hello.py",
            "content": "Hello",
        },
    )

    assert result.allowed is True
    assert result.action == "write"


def test_edit_can_be_allowed():
    manager = PermissionManager(
        permission_callback=lambda tool, action, args: True,
    )

    result = manager.check_permission(
        "edit_file",
        {
            "path": "hello.py",
            "old_text": "Hello",
            "new_text": "Hello Agent",
        },
    )

    assert result.allowed is True
    assert result.action == "edit"


def test_delete_requires_explicit_confirmation():
    manager = PermissionManager(
        permission_callback=lambda tool, action, args: False,
    )

    result = manager.check_permission(
        "delete_file",
        {
            "path": "hello.py",
            "confirm": True,
        },
    )

    assert result.allowed is False
    assert result.action == "delete"


def test_delete_can_be_confirmed():
    manager = PermissionManager(
        permission_callback=lambda tool, action, args: True,
    )

    result = manager.check_permission(
        "delete_file",
        {
            "path": "hello.py",
            "confirm": True,
        },
    )

    assert result.allowed is True
    assert result.action == "delete"


def test_unknown_tool_is_denied():
    manager = PermissionManager()

    result = manager.check_permission(
        "unknown_tool",
        {},
    )

    assert result.allowed is False
    assert result.action == "unknown"


def test_permission_history():
    manager = PermissionManager()

    manager.check_permission(
        "read_file",
        {
            "path": "hello.py",
        },
    )

    history = manager.get_history()

    assert len(history) == 1
    assert history[0]["tool"] == "read_file"
    assert history[0]["action"] == "read"
    assert history[0]["allowed"] is True


def test_permission_history_records_denied_operation():
    manager = PermissionManager()

    manager.check_permission(
        "delete_file",
        {
            "path": "hello.py",
            "confirm": True,
        },
    )

    history = manager.get_history()

    assert len(history) == 1
    assert history[0]["tool"] == "delete_file"
    assert history[0]["action"] == "delete"
    assert history[0]["allowed"] is False


def test_auto_approve_mode():
    manager = PermissionManager(
        auto_approve=True,
    )

    write_result = manager.check_permission(
        "write_file",
        {
            "path": "hello.py",
            "content": "Hello",
        },
    )

    edit_result = manager.check_permission(
        "edit_file",
        {
            "path": "hello.py",
            "old_text": "Hello",
            "new_text": "Hello Agent",
        },
    )

    delete_result = manager.check_permission(
        "delete_file",
        {
            "path": "hello.py",
            "confirm": True,
        },
    )

    assert write_result.allowed is True
    assert edit_result.allowed is True
    assert delete_result.allowed is True