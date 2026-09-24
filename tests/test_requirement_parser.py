import pytest

from requirements.parser import (
    RequirementParser,
    RequirementParserError,
)
from requirements.specification import (
    TaskSpecification,
)


@pytest.fixture
def parser():
    return RequirementParser(model="qwen3:8b")


def test_parse_json_directly(parser):
    content = """
    {
      "objective": {
        "type": "inspect",
        "target": "main.py",
        "focus": null
      },
      "tool_constraints": {
        "allowed_tools": ["read_file"],
        "forbidden_tools": []
      },
      "state_requirements": [],
      "output_constraints": {
        "parameter_names_only": false,
        "no_analysis": false,
        "no_suggestions": false,
        "no_examples": false,
        "max_words": null,
        "language": "zh-TW"
      }
    }
    """

    data = parser._parse_json(content)

    assert data["objective"]["type"] == "inspect"
    assert data["objective"]["target"] == "main.py"


def test_parse_json_with_code_fence(parser):
    content = """
    ```json
    {
      "objective": {
        "type": "inspect",
        "target": "main.py",
        "focus": "foo"
      },
      "tool_constraints": {
        "allowed_tools": [],
        "forbidden_tools": []
      },
      "state_requirements": [],
      "output_constraints": {
        "parameter_names_only": false,
        "no_analysis": false,
        "no_suggestions": false,
        "no_examples": false,
        "max_words": null,
        "language": "zh-TW"
      }
    }
    ```
    """

    data = parser._parse_json(content)

    assert data["objective"]["focus"] == "foo"


def test_parse_json_invalid(parser):
    content = "這不是 JSON"

    with pytest.raises(RequirementParserError):
        parser._parse_json(content)


def test_build_specification(parser):
    data = {
        "objective": {
            "type": "inspect",
            "target": "tools/file_tools.py",
            "focus": "search_files",
        },
        "tool_constraints": {
            "allowed_tools": ["read_file"],
            "forbidden_tools": [],
        },
        "state_requirements": [],
        "output_constraints": {
            "parameter_names_only": True,
            "no_analysis": True,
            "no_suggestions": True,
            "no_examples": True,
            "max_words": None,
            "language": "zh-TW",
        },
    }

    specification = parser._build_specification(data)

    assert isinstance(
        specification,
        TaskSpecification,
    )

    assert specification.objective.type == "inspect"

    assert specification.objective.target == "tools/file_tools.py"

    assert specification.objective.focus == "search_files"

    assert specification.tool_constraints.allowed_tools == ["read_file"]

    assert specification.output_constraints.parameter_names_only is True

    assert specification.output_constraints.no_analysis is True

    assert specification.output_constraints.no_suggestions is True

    assert specification.output_constraints.no_examples is True


def test_build_state_requirements(parser):
    data = {
        "objective": {
            "type": "modify",
            "target": "main.py",
            "focus": None,
        },
        "tool_constraints": {
            "allowed_tools": [],
            "forbidden_tools": [],
        },
        "state_requirements": [
            {
                "type": "contains",
                "path": "main.py",
                "text": "return message",
            }
        ],
        "output_constraints": {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    }

    specification = parser._build_specification(data)

    requirements = specification.get_verifier_requirements()

    assert requirements == [
        {
            "type": "contains",
            "path": "main.py",
            "text": "return message",
        }
    ]


def test_invalid_objective_type(parser):
    data = {
        "objective": {
            "type": "unknown",
            "target": None,
            "focus": None,
        },
        "tool_constraints": {
            "allowed_tools": [],
            "forbidden_tools": [],
        },
        "state_requirements": [],
        "output_constraints": {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    }

    specification = parser._build_specification(data)

    errors = specification.validate()

    assert errors
    assert any("objective type" in error for error in errors)


def test_conflicting_tool_constraints(parser):
    data = {
        "objective": {
            "type": "inspect",
            "target": "main.py",
            "focus": None,
        },
        "tool_constraints": {
            "allowed_tools": ["read_file"],
            "forbidden_tools": ["read_file"],
        },
        "state_requirements": [],
        "output_constraints": {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    }

    specification = parser._build_specification(data)

    errors = specification.validate()

    assert any("同時出現在" in error for error in errors)
