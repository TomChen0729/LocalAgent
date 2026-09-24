import json
import re
from typing import Any

from ollama import chat

from requirements.specification import (
    Objective,
    OutputConstraints,
    StateRequirement,
    TaskSpecification,
    ToolConstraints,
)

REQUIREMENT_PARSER_PROMPT = """
你是一個 Task Requirement Parser。

你的唯一工作，是把使用者的自然語言任務，
轉換成結構化 JSON。

你不是 Coding Agent。
你不能執行任何 Tool。
你不能修改任何檔案。
你不能回答使用者的原始問題。

你只能分析使用者的需求，
並輸出符合指定格式的 JSON。

==================================================
重要規則
==================================================

1. 只能輸出 JSON。

2. 不要輸出 Markdown。

3. 不要使用 ```json。

4. 不要輸出 JSON 以外的任何文字。

5. 不可以捏造使用者沒有提出的需求。

6. 使用者沒有明確要求的 constraint，
   不要自行加入。

7. tool_constraints 是「使用者明確提出的 Tool 限制」。

8. state_requirements 是可以透過實際檔案系統
   驗證的 Requirement。

9. output_constraints 是使用者對最終回答
   提出的格式或內容限制。

==================================================
JSON 格式
==================================================

{
  "objective": {
    "type": "inspect",
    "target": null,
    "focus": null
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

==================================================
objective.type
==================================================

只能使用以下值：

"inspect"
"create"
"modify"
"delete"
"execute"
"git"
"general"

例如：

使用者：
「讀取 main.py」

應該：

{
  "type": "inspect",
  "target": "main.py",
  "focus": null
}

使用者：
「讀取 tools/file_tools.py，看看 search_files」

應該：

{
  "type": "inspect",
  "target": "tools/file_tools.py",
  "focus": "search_files"
}

==================================================
tool_constraints
==================================================

只有使用者明確指定 Tool 限制時才填入。

例如：

「只能使用 read_file」

應該：

{
  "allowed_tools": ["read_file"],
  "forbidden_tools": []
}

例如：

「不要使用其他 Tool」

如果使用者同時指定：

「只能使用 read_file，不要使用其他 Tool」

則：

{
  "allowed_tools": ["read_file"],
  "forbidden_tools": []
}

不要自行列出所有其他 Tool。

==================================================
state_requirements
==================================================

只有可以透過實際檔案狀態驗證的要求才放入。

目前只允許：

"file_exists"
"contains"
"not_contains"

例如：

「建立 hello.py」

應該：

{
  "type": "file_exists",
  "path": "hello.py"
}

例如：

「main.py 必須包含 return message」

應該：

{
  "type": "contains",
  "path": "main.py",
  "text": "return message"
}

例如：

「移除 main.py 裡面的 debug」

應該：

{
  "type": "not_contains",
  "path": "main.py",
  "text": "debug"
}

==================================================
output_constraints
==================================================

只有使用者明確提出時才設定為 true。

例如：

「只回答參數名稱」

應該：

"parameter_names_only": true

例如：

「不要分析」

應該：

"no_analysis": true

例如：

「不要提供建議」

應該：

"no_suggestions": true

例如：

「不要提供範例」

應該：

"no_examples": true

如果使用者沒有要求，
這些欄位必須保持 false。

language 預設：

"zh-TW"

==================================================
重要
==================================================

不要把 Agent 自己認為合理的事情加入 JSON。

只解析使用者真正提出的需求。

現在只輸出 JSON。
"""


class RequirementParserError(Exception):
    """
    Requirement Parser 發生錯誤時使用的例外。
    """

    pass


class RequirementParser:
    """
    使用 LLM 將自然語言 User Query
    解析成 TaskSpecification。
    """

    def __init__(
        self,
        model: str = "qwen3:8b",
    ):
        self.model = model

    def parse(
        self,
        user_input: str,
    ) -> TaskSpecification:
        """
        將 User Query 解析成 TaskSpecification。
        """

        if not isinstance(user_input, str):
            raise RequirementParserError("user_input 必須是字串。")

        if not user_input.strip():
            raise RequirementParserError("user_input 不可以是空字串。")

        response = self._call_llm(user_input)

        data = self._parse_json(response)

        specification = self._build_specification(data)

        errors = specification.validate()

        if errors:
            raise RequirementParserError(
                "Task Specification 驗證失敗：" + "；".join(errors)
            )

        return specification

    def _call_llm(
        self,
        user_input: str,
    ) -> str:
        """
        呼叫 Ollama LLM。
        """

        try:
            response = chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": REQUIREMENT_PARSER_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_input,
                    },
                ],
            )

        except Exception as exc:
            raise RequirementParserError(f"LLM Parser 呼叫失敗：{exc}") from exc

        try:
            content = response.message.content
        except AttributeError as exc:
            raise RequirementParserError(
                "LLM Parser 沒有取得有效的 response content。"
            ) from exc

        if not isinstance(content, str):
            raise RequirementParserError("LLM Parser 回傳內容不是字串。")

        return content.strip()

    def _parse_json(
        self,
        content: str,
    ) -> dict[str, Any]:
        """
        將 LLM 回傳內容解析成 JSON。

        第一優先：
        直接 json.loads。

        如果模型意外加入 Markdown code fence，
        進行有限度的格式清理。

        不進行自然語言 Regex requirement extraction。
        """

        if not content:
            raise RequirementParserError("LLM Parser 回傳空內容。")

        # --------------------------------------------------
        # 第一層：直接解析
        # --------------------------------------------------

        try:
            data = json.loads(content)

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            pass

        # --------------------------------------------------
        # 第二層：處理意外產生的 code fence
        # --------------------------------------------------

        cleaned = content.strip()

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        try:
            data = json.loads(cleaned)

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            pass

        raise RequirementParserError("LLM Parser 回傳內容不是有效 JSON。")

    def _build_specification(
        self,
        data: dict[str, Any],
    ) -> TaskSpecification:
        """
        將 JSON dict 轉換成 TaskSpecification。
        """

        if not isinstance(data, dict):
            raise RequirementParserError("Parser 結果必須是 JSON object。")

        objective_data = data.get(
            "objective",
            {},
        )

        if not isinstance(
            objective_data,
            dict,
        ):
            raise RequirementParserError("objective 必須是 JSON object。")

        objective = Objective(
            type=objective_data.get(
                "type",
                "general",
            ),
            target=objective_data.get("target"),
            focus=objective_data.get("focus"),
        )

        # --------------------------------------------------
        # Tool Constraints
        # --------------------------------------------------

        tool_data = data.get(
            "tool_constraints",
            {},
        )

        if not isinstance(
            tool_data,
            dict,
        ):
            raise RequirementParserError("tool_constraints 必須是 JSON object。")

        allowed_tools = tool_data.get(
            "allowed_tools",
            [],
        )

        forbidden_tools = tool_data.get(
            "forbidden_tools",
            [],
        )

        if not isinstance(
            allowed_tools,
            list,
        ):
            raise RequirementParserError("allowed_tools 必須是 list。")

        if not isinstance(
            forbidden_tools,
            list,
        ):
            raise RequirementParserError("forbidden_tools 必須是 list。")

        tool_constraints = ToolConstraints(
            allowed_tools=allowed_tools,
            forbidden_tools=forbidden_tools,
        )

        # --------------------------------------------------
        # State Requirements
        # --------------------------------------------------

        state_data = data.get(
            "state_requirements",
            [],
        )

        if not isinstance(
            state_data,
            list,
        ):
            raise RequirementParserError("state_requirements 必須是 list。")

        state_requirements = []

        for index, item in enumerate(state_data):
            if not isinstance(item, dict):
                raise RequirementParserError(
                    "state_requirements[" f"{index}] 必須是 JSON object。"
                )

            state_requirements.append(
                StateRequirement(
                    type=item.get("type"),
                    path=item.get("path"),
                    text=item.get("text"),
                )
            )

        # --------------------------------------------------
        # Output Constraints
        # --------------------------------------------------

        output_data = data.get(
            "output_constraints",
            {},
        )

        if not isinstance(
            output_data,
            dict,
        ):
            raise RequirementParserError("output_constraints 必須是 JSON object。")

        output_constraints = OutputConstraints(
            parameter_names_only=output_data.get(
                "parameter_names_only",
                False,
            ),
            no_analysis=output_data.get(
                "no_analysis",
                False,
            ),
            no_suggestions=output_data.get(
                "no_suggestions",
                False,
            ),
            no_examples=output_data.get(
                "no_examples",
                False,
            ),
            max_words=output_data.get("max_words"),
            language=output_data.get(
                "language",
                "zh-TW",
            ),
        )

        return TaskSpecification(
            objective=objective,
            tool_constraints=tool_constraints,
            state_requirements=state_requirements,
            output_constraints=output_constraints,
        )
