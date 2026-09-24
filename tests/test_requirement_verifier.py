from requirements.verifier import (
    verify_requirement,
    verify_requirements,
)


def test_file_exists_requirement(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.file_exists",
        lambda path: True,
    )

    result = verify_requirement(
        {
            "type": "file_exists",
            "path": "hello.py",
        }
    )

    assert result["status"] == "passed"


def test_file_exists_requirement_failed(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.file_exists",
        lambda path: False,
    )

    result = verify_requirement(
        {
            "type": "file_exists",
            "path": "hello.py",
        }
    )

    assert result["status"] == "failed"


def test_contains_requirement(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.read_file",
        lambda path: '1: print("Hello World")',
    )

    result = verify_requirement(
        {
            "type": "contains",
            "path": "hello.py",
            "text": "Hello World",
        }
    )

    assert result["status"] == "passed"


def test_contains_requirement_failed(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.read_file",
        lambda path: '1: print("Hello")',
    )

    result = verify_requirement(
        {
            "type": "contains",
            "path": "hello.py",
            "text": "Hello World",
        }
    )

    assert result["status"] == "failed"


def test_not_contains_requirement(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.read_file",
        lambda path: '1: print("Hello World")',
    )

    result = verify_requirement(
        {
            "type": "not_contains",
            "path": "hello.py",
            "text": "Goodbye",
        }
    )

    assert result["status"] == "passed"


def test_not_contains_requirement_failed(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.read_file",
        lambda path: '1: print("Goodbye")',
    )

    result = verify_requirement(
        {
            "type": "not_contains",
            "path": "hello.py",
            "text": "Goodbye",
        }
    )

    assert result["status"] == "failed"


def test_unsupported_requirement_type():

    result = verify_requirement(
        {
            "type": "magic_check",
            "path": "hello.py",
        }
    )

    assert result["status"] == "failed"


def test_missing_requirement_path():

    result = verify_requirement(
        {
            "type": "file_exists",
        }
    )

    assert result["status"] == "failed"


def test_contains_missing_text():

    result = verify_requirement(
        {
            "type": "contains",
            "path": "hello.py",
        }
    )

    assert result["status"] == "failed"


def test_invalid_requirement_input():

    result = verify_requirement("not a dict")

    assert result["status"] == "failed"


def test_verify_multiple_requirements(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.file_exists",
        lambda path: True,
    )

    monkeypatch.setattr(
        "requirements.verifier.read_file",
        lambda path: '1: print("Hello World")',
    )

    result = verify_requirements(
        [
            {
                "type": "file_exists",
                "path": "hello.py",
            },
            {
                "type": "contains",
                "path": "hello.py",
                "text": "Hello World",
            },
        ]
    )

    assert result["status"] == "passed"

    assert result["total"] == 2

    assert result["passed"] == 2

    assert result["failed"] == 0


def test_verify_multiple_requirements_with_failure(
    monkeypatch,
):

    monkeypatch.setattr(
        "requirements.verifier.file_exists",
        lambda path: True,
    )

    monkeypatch.setattr(
        "requirements.verifier.read_file",
        lambda path: '1: print("Hello")',
    )

    result = verify_requirements(
        [
            {
                "type": "file_exists",
                "path": "hello.py",
            },
            {
                "type": "contains",
                "path": "hello.py",
                "text": "Hello World",
            },
        ]
    )

    assert result["status"] == "failed"

    assert result["total"] == 2

    assert result["passed"] == 1

    assert result["failed"] == 1


def test_empty_requirements():

    result = verify_requirements([])

    assert result["status"] == "failed"


def test_invalid_requirements():

    result = verify_requirements("invalid")

    assert result["status"] == "failed"
