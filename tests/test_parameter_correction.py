"""
Phase 9.4 - Parameter Correction Tests

測試目標：

1. 正確參數不需要 correction
2. 缺少必要參數可以被識別
3. 錯誤型別可以被識別
4. 可以安全修正的參數可以產生 correction
5. 無法安全修正的參數不應該被任意修改
"""

import pytest

from agent.parameter_correction import (
    ParameterCorrection,
    CorrectionResult,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def corrector():
    """
    建立 ParameterCorrection。
    """
    return ParameterCorrection()


# ============================================================
# 1. Valid Arguments
# ============================================================


def test_valid_arguments_require_no_correction(corrector):
    """
    正確的 Tool arguments 不需要修正。
    """

    result = corrector.correct(
        tool_name="read_file",
        arguments={
            "path": "README.md",
        },
        error=None,
    )

    assert isinstance(result, CorrectionResult)

    assert result.corrected is False
    assert result.arguments == {
        "path": "README.md",
    }


# ============================================================
# 2. Missing Required Argument
# ============================================================


def test_missing_required_argument_is_detected(corrector):
    """
    缺少必要參數時，應該能識別問題。
    """

    result = corrector.correct(
        tool_name="read_file",
        arguments={},
        error="missing required argument: path",
    )

    assert isinstance(result, CorrectionResult)

    assert result.corrected is False
    assert result.reason is not None


# ============================================================
# 3. Invalid Argument Type
# ============================================================


def test_invalid_argument_type_is_detected(corrector):
    """
    Tool argument 型別錯誤時，應該能識別問題。
    """

    result = corrector.correct(
        tool_name="read_file",
        arguments={
            "path": 123,
        },
        error="path must be a string",
    )

    assert isinstance(result, CorrectionResult)

    assert result.corrected is False
    assert result.reason is not None


# ============================================================
# 4. Correctable Argument
# ============================================================


def test_correctable_argument_returns_corrected_arguments(corrector):
    """
    對於可以安全修正的參數，
    應該產生 corrected arguments。
    """

    result = corrector.correct(
        tool_name="read_file",
        arguments={
            "path": "README.tx",
        },
        error="file not found",
    )

    assert isinstance(result, CorrectionResult)

    if result.corrected:
        assert result.arguments is not None
        assert "path" in result.arguments


# ============================================================
# 5. Uncorrectable Argument
# ============================================================


def test_uncorrectable_argument_returns_no_correction(corrector):
    """
    無法安全判斷如何修正的參數，
    不應該任意修改。
    """

    original_arguments = {
        "path": "unknown_file_123456.xyz",
    }

    result = corrector.correct(
        tool_name="read_file",
        arguments=original_arguments,
        error="file not found",
    )

    assert isinstance(result, CorrectionResult)

    if not result.corrected:
        assert result.arguments == original_arguments
