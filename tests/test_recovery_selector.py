from agent.recovery_selector import (
    RecoverySelector,
)


def test_select_first_candidate():

    selector = RecoverySelector()

    result = selector.select(
        [
            "read_file",
            "search_files",
        ]
    )

    assert result.selected_tool == "read_file"

    assert result.candidates == [
        "read_file",
        "search_files",
    ]


def test_select_single_candidate():

    selector = RecoverySelector()

    result = selector.select(
        [
            "read_file",
        ]
    )

    assert result.selected_tool == "read_file"


def test_empty_candidates():

    selector = RecoverySelector()

    result = selector.select([])

    assert result.selected_tool is None

    assert result.candidates == []


def test_invalid_candidates_type():

    selector = RecoverySelector()

    result = selector.select(
        "read_file",
    )

    assert result.selected_tool is None

    assert result.candidates == []


def test_remove_empty_candidates():

    selector = RecoverySelector()

    result = selector.select(
        [
            "",
            "   ",
            "read_file",
        ]
    )

    assert result.selected_tool == "read_file"

    assert result.candidates == [
        "read_file",
    ]


def test_remove_invalid_candidates():

    selector = RecoverySelector()

    result = selector.select(
        [
            None,
            123,
            "read_file",
        ]
    )

    assert result.selected_tool == "read_file"

    assert result.candidates == [
        "read_file",
    ]


def test_remove_duplicate_candidates():

    selector = RecoverySelector()

    result = selector.select(
        [
            "read_file",
            "read_file",
            "search_files",
        ]
    )

    assert result.selected_tool == "read_file"

    assert result.candidates == [
        "read_file",
        "search_files",
    ]


def test_selection_to_dict():

    selector = RecoverySelector()

    result = selector.select(
        [
            "read_file",
            "search_files",
        ]
    )

    data = result.to_dict()

    assert data["selected_tool"] == "read_file"

    assert data["candidates"] == [
        "read_file",
        "search_files",
    ]

    assert "reason" in data
