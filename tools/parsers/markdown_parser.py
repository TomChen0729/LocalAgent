"""
Markdown parser utilities for LocalAgent.

This module contains Markdown-specific parsing logic.

Responsibilities:
- Parse Markdown headings
- Normalize heading text
- Locate a specific Markdown section
- Extract the content belonging to that section

This module does NOT handle:
- File system permissions
- Safe path validation
- File existence checks
- File size checks
- Writing files
- Deleting files

Those responsibilities belong to file_tools.py.
"""

import re
from typing import Optional


def parse_markdown_heading(
    line: str,
) -> Optional[tuple[int, str]]:
    """
    Parse a Markdown heading.

    Supported examples:

        # Introduction
        ## Background
        ### Method
        #Introduction
        ## Introduction ##

    Returns:
        (heading_level, heading_text)

    Examples:

        "# Introduction"
            -> (1, "Introduction")

        "## Background"
            -> (2, "Background")

        "### Method ###"
            -> (3, "Method")

    Returns None when the line is not a valid Markdown heading.
    """

    if not isinstance(line, str):
        return None

    match = re.match(
        r"^\s*(#{1,6})\s*(.*?)\s*#*\s*$",
        line,
    )

    if not match:
        return None

    hashes = match.group(1)
    heading_text = match.group(2).strip()

    if not heading_text:
        return None

    level = len(hashes)

    return level, heading_text


def normalize_heading(heading: str) -> str:
    """
    Normalize a heading so that different representations
    can still be matched.

    Examples:

        "## Introduction"
            -> "introduction"

        "28. Development Roadmap"
            -> "development roadmap"

        "# 3. Project Structure"
            -> "project structure"

        "Project Structure"
            -> "project structure"

        "Project Structure #"
            -> "project structure"

    The purpose of normalization is to make the Agent less
    sensitive to formatting differences in Markdown headings.
    """

    if not isinstance(heading, str):
        return ""

    normalized = heading.strip()

    # Remove Markdown heading prefix.
    #
    # Examples:
    #   "# Introduction"
    #   "## Introduction"
    #   "### Introduction"
    normalized = re.sub(
        r"^#{1,6}\s*",
        "",
        normalized,
    )

    # Remove trailing Markdown heading markers.
    #
    # Example:
    #   "Introduction ###"
    #   -> "Introduction"
    normalized = re.sub(
        r"\s+#+\s*$",
        "",
        normalized,
    )

    # Remove section numbering.
    #
    # Examples:
    #   "28. Development Roadmap"
    #   "3.1 Background"
    #   "2) Introduction"
    #   "1. Introduction"
    #
    # Become:
    #   "Development Roadmap"
    #   "Background"
    #   "Introduction"
    normalized = re.sub(
        r"^\d+(?:\.\d+)*[.)]?\s+",
        "",
        normalized,
    )

    # Collapse multiple spaces.
    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    # Remove surrounding whitespace.
    normalized = normalized.strip()

    # Case-insensitive comparison.
    normalized = normalized.casefold()

    return normalized


def extract_section(
    content: str,
    heading: str,
) -> str:
    """
    Extract a Markdown section from text content.

    The function:

    1. Parses all Markdown headings.
    2. Finds the requested heading.
    3. Determines the heading level from the actual Markdown file.
    4. Returns everything belonging to that section.
    5. Stops when another heading of the same or higher level
       is encountered.

    Heading matching is normalized, so these can match:

        Project Structure
        # Project Structure
        ## Project Structure
        ## 3. Project Structure
        3. Project Structure

    The returned content preserves original line numbers.

    Example Markdown:

        # Introduction

        This is introduction.

        ## Background

        Background content.

        ## Method

        Method content.

        # Conclusion

        Conclusion content.

    Requesting:

        Background

    Returns:

        5: ## Background
        6:
        7: Background content.
    """

    if not isinstance(content, str):
        return "錯誤：content 必須是字串。"

    if not isinstance(heading, str):
        return "錯誤：heading 必須是字串。"

    heading = heading.strip()

    if not heading:
        return "錯誤：heading 不可以是空字串。"

    lines = content.splitlines()

    target_heading = normalize_heading(heading)

    if not target_heading:
        return "錯誤：無法解析指定的 Markdown Heading。"

    target_line = None
    target_level = None

    # ---------------------------------------------------------
    # Step 1:
    # 找到目標 Markdown Heading
    # ---------------------------------------------------------

    for index, line in enumerate(lines, start=1):

        parsed = parse_markdown_heading(line)

        if parsed is None:
            continue

        level, heading_text = parsed

        normalized_actual_heading = normalize_heading(heading_text)

        if normalized_actual_heading == target_heading:
            target_line = index
            target_level = level
            break

    if target_line is None:
        return "錯誤：在檔案中找不到指定 Section。\n" f"Heading：{heading}"

    # ---------------------------------------------------------
    # Step 2:
    # 找到 Section 結束位置
    #
    # Section 會持續到：
    #
    # - 下一個相同層級 Heading
    # - 下一個更高層級 Heading
    #
    # 例如：
    #
    # ## Background
    # content
    #
    # ### Dataset
    # content
    #
    # ### Model
    # content
    #
    # ## Method
    #
    # Background Section 就會包含 Dataset / Model。
    # ---------------------------------------------------------

    end_line = len(lines)

    for index in range(
        target_line + 1,
        len(lines) + 1,
    ):

        line = lines[index - 1]

        parsed = parse_markdown_heading(line)

        if parsed is None:
            continue

        current_level, _ = parsed

        if current_level <= target_level:
            end_line = index - 1
            break

    # ---------------------------------------------------------
    # Step 3:
    # 取出 Section
    # ---------------------------------------------------------

    selected_lines = lines[target_line - 1 : end_line]

    if not selected_lines:
        return f"錯誤：Section {heading} 沒有內容。"

    # ---------------------------------------------------------
    # Step 4:
    # 加入原始行號
    #
    # 保留行號可以讓 Agent 後續：
    #
    # - 理解內容位置
    # - 回報來源位置
    # - 進行 edit
    # - 進行 verification
    # ---------------------------------------------------------

    numbered_lines = []

    for index, line in enumerate(
        selected_lines,
        start=target_line,
    ):
        numbered_lines.append(f"{index}: {line}")

    return "\n".join(numbered_lines)


__all__ = [
    "parse_markdown_heading",
    "normalize_heading",
    "extract_section",
]
