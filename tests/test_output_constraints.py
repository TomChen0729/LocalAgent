import pytest

from agent.runtime import AgentRuntime


def create_agent():
    return AgentRuntime(model="qwen3:8b")


def set_output_constraints(
    agent,
    constraints,
):
    agent.task_state["task_specification"] = {
        "objective": {
            "type": "general",
            "target": None,
            "focus": None,
        },
        "tool_constraints": {
            "allowed_tools": [],
            "forbidden_tools": [],
        },
        "state_requirements": [],
        "output_constraints": constraints,
    }


# ============================================================
# Word Count
# ============================================================


def test_count_output_words_english():
    agent = create_agent()

    result = agent.count_output_words("Hello LocalAgent")

    assert result == 2


def test_count_output_words_chinese():
    agent = create_agent()

    result = agent.count_output_words("你好世界")

    assert result == 4


def test_count_output_words_mixed():
    agent = create_agent()

    result = agent.count_output_words("你好 LocalAgent")

    assert result == 3


# ============================================================
# Language Detection
# ============================================================


def test_detect_output_language_chinese():
    agent = create_agent()

    assert agent.detect_output_language("這是一段中文") == "zh-TW"


def test_detect_output_language_english():
    agent = create_agent()

    assert agent.detect_output_language("This is English") == "en"


def test_detect_output_language_mixed():
    agent = create_agent()

    assert agent.detect_output_language("這是 LocalAgent") == "mixed"


# ============================================================
# Deterministic Output Verification
# ============================================================


def test_output_constraint_empty_answer_fails():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    )

    result = agent.verify_output_constraints_deterministic("")

    assert result["passed"] is False
    assert result["violations"]


def test_output_constraint_max_words_passes():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": 10,
            "language": "zh-TW",
        },
    )

    result = agent.verify_output_constraints_deterministic("你好")

    assert result["passed"] is True


def test_output_constraint_max_words_fails():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": 2,
            "language": "zh-TW",
        },
    )

    result = agent.verify_output_constraints_deterministic("這是一段超過限制的中文")

    assert result["passed"] is False
    assert any("max_words" in violation for violation in result["violations"])


def test_output_constraint_english_language_fails_for_chinese():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "en",
        },
    )

    result = agent.verify_output_constraints_deterministic("這是一段中文")

    assert result["passed"] is False


def test_output_constraint_zh_tw_accepts_chinese():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    )

    result = agent.verify_output_constraints_deterministic("這是一段中文")

    assert result["passed"] is True


# ============================================================
# Active Output Constraints
# ============================================================


def test_no_active_output_constraints():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    )

    assert agent.has_active_output_constraints() is False


def test_max_words_is_active_constraint():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": 100,
            "language": "zh-TW",
        },
    )

    assert agent.has_active_output_constraints() is True


def test_parameter_names_only_is_active_constraint():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": True,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    )

    assert agent.has_active_output_constraints() is True


# ============================================================
# Failure Control
# ============================================================


def test_output_failure_counter_increases():
    agent = create_agent()

    agent.start_task("測試 Output Constraint")

    result = {
        "passed": False,
        "status": "failed",
        "deterministic": {
            "passed": False,
            "violations": ["超過字數限制"],
        },
        "semantic": None,
        "violations": ["超過字數限制"],
    }

    should_continue = agent.handle_output_verification_failure(result)

    assert should_continue is True
    assert agent.task_state["output_verification_failure_count"] == 1


def test_output_failure_stops_after_limit():
    agent = create_agent()

    agent.start_task("測試 Output Constraint")

    result = {
        "passed": False,
        "status": "failed",
        "deterministic": {
            "passed": False,
            "violations": ["超過字數限制"],
        },
        "semantic": None,
        "violations": ["超過字數限制"],
    }

    assert agent.handle_output_verification_failure(result) is True

    assert agent.handle_output_verification_failure(result) is True

    assert agent.handle_output_verification_failure(result) is False

    assert agent.task_state["status"] == "stopped"


def test_output_failure_counter_can_be_reset():
    agent = create_agent()

    agent.start_task("測試 Output Constraint")

    agent.task_state["output_verification_failure_count"] = 2

    agent.reset_output_verification_failure_state()

    assert agent.task_state["output_verification_failure_count"] == 0


# ============================================================
# Semantic Verification
# ============================================================


def test_semantic_verification_skips_when_no_semantic_constraints():
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": False,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": 100,
            "language": "zh-TW",
        },
    )

    result = agent.verify_output_constraints_semantic("你好")

    assert result["passed"] is True


def test_semantic_verification_can_be_mocked(
    monkeypatch,
):
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": True,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    )

    class FakeMessage:
        content = (
            '{"passed": true, '
            '"violations": [], '
            '"reason": "符合所有 Output Constraints"}'
        )

    class FakeResponse:
        message = FakeMessage()

    monkeypatch.setattr(
        "agent.runtime.chat",
        lambda **kwargs: FakeResponse(),
    )

    result = agent.verify_output_constraints_semantic("name")

    assert result["passed"] is True
    assert result["violations"] == []


def test_semantic_verification_failed_result(
    monkeypatch,
):
    agent = create_agent()

    set_output_constraints(
        agent,
        {
            "parameter_names_only": True,
            "no_analysis": False,
            "no_suggestions": False,
            "no_examples": False,
            "max_words": None,
            "language": "zh-TW",
        },
    )

    class FakeMessage:
        content = (
            '{"passed": false, '
            '"violations": ["包含分析內容"], '
            '"reason": "回答不只包含參數名稱"}'
        )

    class FakeResponse:
        message = FakeMessage()

    monkeypatch.setattr(
        "agent.runtime.chat",
        lambda **kwargs: FakeResponse(),
    )

    result = agent.verify_output_constraints_semantic("name 是使用者名稱")

    assert result["passed"] is False
    assert "包含分析內容" in result["violations"]
