"""
Output Constraint Verification

負責驗證 Agent 最終回答是否符合
TaskSpecification 中定義的 OutputConstraints。

注意：
- 這裡只負責「驗證」
- 不負責修改回答
- 不負責重新呼叫 LLM
- 不負責決定 Recovery 策略

State Verification 與 Output Verification 分離：

    requirements/verifier.py
        → 驗證專案實際狀態

    requirements/output_verifier.py
        → 驗證 Agent 最終輸出

Phase 8.5：

Deterministic Verification
    ├── answer type
    ├── empty answer
    ├── max_words
    ├── no_suggestions
    ├── no_examples
    └── basic language constraint

Semantic Verification
    ├── parameter_names_only
    └── no_analysis

Semantic Verification 的實際 LLM 呼叫
由 Agent Runtime 負責。
本檔案不呼叫 LLM。
"""

from __future__ import annotations

import re
from typing import Any

from requirements.specification import OutputConstraints

# ============================================================
# Regular Expression
# ============================================================

CJK_PATTERN = (
    r"[\u3400-\u4dbf"
    r"\u4e00-\u9fff"
    r"\uf900-\ufaff"
    r"\u3040-\u30ff"
    r"\uac00-\ud7af]"
)


LATIN_TOKEN_PATTERN = r"[A-Za-z0-9]+(?:['_-][A-Za-z0-9]+)*"


# ============================================================
# Word Count
# ============================================================


def _count_words(text: str) -> int:
    """
    計算回答的字數。

    第一版採取簡單且 deterministic 的工程性計數方式：

    1. 中文 / 日文 / 韓文等 CJK 字元：
       每個字元計為 1 word。

    2. 英文 / 數字：
       以連續 token 計算。

    例如：

        "你好世界"
        → 4

        "Hello world"
        → 2

        "你好 Hello"
        → 3

        "foo_bar"
        → 1

    注意：
    這不是自然語言學上的「單字數」，
    而是 Runtime 用來限制輸出長度的工程性指標。
    """

    if not isinstance(text, str):
        return 0

    # --------------------------------------------------------
    # CJK Characters
    # --------------------------------------------------------

    cjk_characters = re.findall(
        CJK_PATTERN,
        text,
    )

    # --------------------------------------------------------
    # Remove CJK Characters
    #
    # 再計算英文 / 數字 token。
    # --------------------------------------------------------

    remaining_text = re.sub(
        CJK_PATTERN,
        " ",
        text,
    )

    # --------------------------------------------------------
    # Latin / Number Tokens
    #
    # 注意：
    # 這裡最後的 * 是 regex quantifier。
    #
    # 正確：
    #     ( ... )*
    #
    # 不可以寫成：
    #     ( ... )\*
    #
    # 否則會要求文字中真的出現 "*"。
    # --------------------------------------------------------

    latin_tokens = re.findall(
        LATIN_TOKEN_PATTERN,
        remaining_text,
    )

    return len(cjk_characters) + len(latin_tokens)


# ============================================================
# Public Compatibility Wrapper
# ============================================================


def count_words(text: str) -> int:
    """
    Public API。

    提供給其他模組使用，
    實際計算交由 _count_words()。
    """

    return _count_words(text)


# ============================================================
# Language Detection
# ============================================================


def detect_output_language(text: str) -> str:
    """
    簡單 deterministic language detection。

    回傳：

        zh-TW
        en
        mixed
        unknown

    注意：

    這不是完整 NLP language detector。

    目的只是提供 Runtime 基本
    Output Constraint Enforcement。

    如果中文回答中包含：

        main.py
        Python
        API
        Docker

    之類英文技術詞，
    可能被判定為 mixed。

    Runtime 對 zh-TW 會接受 mixed，
    因為技術回答本身很常混合英文術語。
    """

    if not isinstance(text, str):
        return "unknown"

    if not text.strip():
        return "unknown"

    # --------------------------------------------------------
    # CJK
    # --------------------------------------------------------

    cjk_count = len(
        re.findall(
            r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]",
            text,
        )
    )

    # --------------------------------------------------------
    # Latin
    # --------------------------------------------------------

    latin_count = len(
        re.findall(
            r"[A-Za-z]",
            text,
        )
    )

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    if cjk_count > 0 and latin_count == 0:
        return "zh-TW"

    if latin_count > 0 and cjk_count == 0:
        return "en"

    if cjk_count > 0 and latin_count > 0:
        return "mixed"

    return "unknown"


# ============================================================
# Suggestion Detection
# ============================================================


def _contains_suggestion_language(text: str) -> bool:
    """
    嘗試偵測回答中是否包含明顯的建議語句。

    這不是語意級 AI 判斷，
    而是 deterministic heuristic。

    因此只會處理非常明確的建議表達。
    """

    if not isinstance(text, str):
        return False

    patterns = [
        r"建議",
        r"推薦",
        r"可以考慮",
        r"你可以",
        r"不妨",
        r"建議你",
        r"我建議",
        r"\brecommend\b",
        r"\bsuggest\b",
        r"\byou should\b",
        r"\byou could\b",
    ]

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


# ============================================================
# Example Detection
# ============================================================


def _contains_example_language(text: str) -> bool:
    """
    嘗試偵測回答中是否包含明顯的範例表達。

    同樣採 deterministic heuristic，
    不宣稱可以理解所有語意上的「範例」。
    """

    if not isinstance(text, str):
        return False

    patterns = [
        r"例如",
        r"比如",
        r"舉例",
        r"範例",
        r"\bexample\b",
        r"\bfor example\b",
        r"\be\.g\.\b",
    ]

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


# ============================================================
# Main Output Verification
# ============================================================


def verify_output(
    answer: str,
    constraints: OutputConstraints,
) -> dict[str, Any]:
    """
    驗證 Agent 最終回答是否符合 OutputConstraints。

    第一版支援 deterministic：

    - answer type
    - empty answer
    - max_words
    - no_suggestions
    - no_examples

    Language：

    - zh-TW 為預設語言，因此目前不作為
      standalone deterministic failure condition。
    - 非預設語言可以進行基本 heuristic。
    - 不支援的語言則 skipped。

    以下限制保留給 Semantic Verification：

    - parameter_names_only
    - no_analysis

    回傳：

    {
        "status": "passed" | "failed",
        "passed": int,
        "failed": int,
        "total": int,
        "all_passed": bool,
        "results": [...],
        "message": str,
    }

    注意：

    skipped 不會被計入 passed / failed。
    """

    # ========================================================
    # 1. Input Type Validation
    # ========================================================

    if not isinstance(answer, str):

        return {
            "status": "failed",
            "passed": 0,
            "failed": 1,
            "total": 1,
            "all_passed": False,
            "results": [
                {
                    "constraint": "answer_type",
                    "status": "failed",
                    "message": "Agent 最終回答必須是字串。",
                }
            ],
            "message": "Output Verification 失敗：answer 必須是字串。",
        }

    if not isinstance(
        constraints,
        OutputConstraints,
    ):

        return {
            "status": "failed",
            "passed": 0,
            "failed": 1,
            "total": 1,
            "all_passed": False,
            "results": [
                {
                    "constraint": "constraints_type",
                    "status": "failed",
                    "message": "constraints 必須是 OutputConstraints。",
                }
            ],
            "message": "Output Verification 失敗：constraints 型別錯誤。",
        }

    results: list[dict[str, Any]] = []

    # ========================================================
    # 2. Empty Answer
    # ========================================================

    if answer.strip():

        results.append(
            {
                "constraint": "answer_not_empty",
                "status": "passed",
                "message": "Final Answer 不是空回答。",
            }
        )

    else:

        results.append(
            {
                "constraint": "answer_not_empty",
                "status": "failed",
                "message": "Final Answer 不可以是空回答。",
            }
        )

    # ========================================================
    # 3. max_words
    # ========================================================

    if constraints.max_words is not None:

        word_count = _count_words(answer)

        if word_count <= constraints.max_words:

            results.append(
                {
                    "constraint": "max_words",
                    "status": "passed",
                    "actual": word_count,
                    "expected": constraints.max_words,
                    "message": (
                        f"回答長度 {word_count} "
                        f"未超過限制 {constraints.max_words}。"
                    ),
                }
            )

        else:

            results.append(
                {
                    "constraint": "max_words",
                    "status": "failed",
                    "actual": word_count,
                    "expected": constraints.max_words,
                    "message": (
                        f"max_words：回答長度 {word_count} "
                        f"超過限制 {constraints.max_words}。"
                    ),
                }
            )

    # ========================================================
    # 4. no_suggestions
    # ========================================================

    if constraints.no_suggestions:

        contains_suggestion = _contains_suggestion_language(answer)

        if not contains_suggestion:

            results.append(
                {
                    "constraint": "no_suggestions",
                    "status": "passed",
                    "message": "未偵測到明顯的建議語句。",
                }
            )

        else:

            results.append(
                {
                    "constraint": "no_suggestions",
                    "status": "failed",
                    "message": "no_suggestions：偵測到可能的建議語句。",
                }
            )

    # ========================================================
    # 5. no_examples
    # ========================================================

    if constraints.no_examples:

        contains_example = _contains_example_language(answer)

        if not contains_example:

            results.append(
                {
                    "constraint": "no_examples",
                    "status": "passed",
                    "message": "未偵測到明顯的範例語句。",
                }
            )

        else:

            results.append(
                {
                    "constraint": "no_examples",
                    "status": "failed",
                    "message": "no_examples：偵測到可能的範例語句。",
                }
            )

    # ========================================================
    # 6. Language
    # ========================================================

    if constraints.language:

        detected_language = detect_output_language(answer)

        # ----------------------------------------------------
        # zh-TW
        #
        # zh-TW 是 LocalAgent 預設語言。
        #
        # 目前不把它當成 standalone deterministic
        # failure condition。
        #
        # 原因：
        #
        # 中文技術回答很容易包含：
        #
        # Python / API / Docker / main.py
        #
        # 因此簡單 heuristic 很容易把合法答案判成 mixed。
        #
        # 更嚴格的語言驗證留給後續 semantic verifier。
        # ----------------------------------------------------

        if constraints.language == "zh-TW":

            results.append(
                {
                    "constraint": "language",
                    "status": "skipped",
                    "actual": detected_language,
                    "expected": "zh-TW",
                    "message": (
                        "zh-TW 為 LocalAgent 預設語言，"
                        "目前不進行 deterministic language failure 判斷。"
                    ),
                }
            )

        # ----------------------------------------------------
        # English
        # ----------------------------------------------------

        elif constraints.language == "en":

            if detected_language in {
                "zh-TW",
                "mixed",
            }:

                results.append(
                    {
                        "constraint": "language",
                        "status": "failed",
                        "actual": detected_language,
                        "expected": "en",
                        "message": (
                            "language：Output language " "不符合 English 要求。"
                        ),
                    }
                )

            else:

                results.append(
                    {
                        "constraint": "language",
                        "status": "passed",
                        "actual": detected_language,
                        "expected": "en",
                        "message": "Output language 符合 English 要求。",
                    }
                )

        # ----------------------------------------------------
        # Other Languages
        # ----------------------------------------------------

        else:

            results.append(
                {
                    "constraint": "language",
                    "status": "skipped",
                    "actual": detected_language,
                    "expected": constraints.language,
                    "message": (
                        "目前版本尚未支援此語言的 " "deterministic verification。"
                    ),
                }
            )

    # ========================================================
    # 7. Semantic Constraints
    # ========================================================

    if constraints.parameter_names_only:

        results.append(
            {
                "constraint": "parameter_names_only",
                "status": "skipped",
                "message": ("目前版本尚未進行語意級 " "Parameter Name Verification。"),
            }
        )

    if constraints.no_analysis:

        results.append(
            {
                "constraint": "no_analysis",
                "status": "skipped",
                "message": ("目前版本尚未進行語意級 " "Analysis Verification。"),
            }
        )

    # ========================================================
    # Statistics
    # ========================================================

    checked_results = [
        result
        for result in results
        if result["status"]
        in {
            "passed",
            "failed",
        }
    ]

    passed_count = sum(1 for result in checked_results if result["status"] == "passed")

    failed_count = sum(1 for result in checked_results if result["status"] == "failed")

    checked_count = len(checked_results)

    all_passed = failed_count == 0

    status = "passed" if all_passed else "failed"

    if status == "passed":

        message = "Output Verification：PASS。"

    else:

        message = "Output Verification：FAIL。"

    return {
        "status": status,
        "passed": passed_count,
        "failed": failed_count,
        "total": checked_count,
        "all_passed": all_passed,
        "results": results,
        "message": message,
    }
