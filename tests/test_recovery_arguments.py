from agent.recovery_arguments import (
    RecoveryArgumentAdapter,
)


def test_read_section_to_read_file():

    adapter = RecoveryArgumentAdapter()

    result = adapter.transform(
        "read_section",
        "read_file",
        {
            "path": "README.md",
            "heading": "Features",
        },
    )

    assert result.changed is True

    assert result.original_arguments == {
        "path": "README.md",
        "heading": "Features",
    }

    assert result.transformed_arguments == {
        "path": "README.md",
    }


def test_read_section_without_path():

    adapter = RecoveryArgumentAdapter()

    result = adapter.transform(
        "read_section",
        "read_file",
        {
            "heading": "Features",
        },
    )

    assert result.changed is True

    assert result.transformed_arguments == {}


def test_same_tool_arguments_are_preserved():

    adapter = RecoveryArgumentAdapter()

    result = adapter.transform(
        "read_file",
        "read_file",
        {
            "path": "README.md",
        },
    )

    assert result.changed is False

    assert result.transformed_arguments == {
        "path": "README.md",
    }


def test_unknown_tool_mapping_preserves_arguments():

    adapter = RecoveryArgumentAdapter()

    result = adapter.transform(
        "tool_a",
        "tool_b",
        {
            "path": "test.txt",
            "value": "hello",
        },
    )

    assert result.changed is False

    assert result.transformed_arguments == {
        "path": "test.txt",
        "value": "hello",
    }


def test_invalid_arguments():

    adapter = RecoveryArgumentAdapter()

    result = adapter.transform(
        "read_section",
        "read_file",
        None,
    )

    assert result.changed is False

    assert result.original_arguments == {}

    assert result.transformed_arguments == {}


def test_arguments_are_copied():

    adapter = RecoveryArgumentAdapter()

    original = {
        "path": "README.md",
    }

    result = adapter.transform(
        "read_file",
        "read_file",
        original,
    )

    original["path"] = "changed.md"

    assert result.transformed_arguments == {
        "path": "README.md",
    }


def test_to_dict():

    adapter = RecoveryArgumentAdapter()

    result = adapter.transform(
        "read_section",
        "read_file",
        {
            "path": "README.md",
            "heading": "Features",
        },
    )

    data = result.to_dict()

    assert data["changed"] is True

    assert data["transformed_arguments"] == {
        "path": "README.md",
    }

    assert "reason" in data
