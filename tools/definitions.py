tools = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出指定目錄中的檔案與資料夾。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要列出的目錄路徑。",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_exists",
            "description": "確認指定檔案或資料夾是否存在。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "檔案或資料夾路徑。",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "讀取指定檔案內容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要讀取的檔案路徑。",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "建立或覆寫檔案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "檔案路徑。",
                    },
                    "content": {
                        "type": "string",
                        "description": "要寫入的內容。",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "建立資料夾。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "資料夾路徑。",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "搜尋符合條件的檔案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜尋模式。",
                    }
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "修改指定檔案中的內容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "檔案路徑。",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "要被取代的舊文字。",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "新的文字。",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "刪除指定檔案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要刪除的檔案路徑。",
                    }
                },
                "required": ["path"],
            },
        },
    },
    # ==========================================================
    # Phase 6 - Git Tools
    # ==========================================================
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": (
                "查看目前 Git Repository 的狀態，"
                "包含目前 branch 以及尚未提交的檔案修改。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": ("查看目前 Git Repository 尚未提交的程式碼差異。"),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": ("查看 Git Repository 最近的 Commit 歷史。"),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "最多顯示幾筆 Commit，預設 10。",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": (
                "建立 Git Commit。"
                "這是一個會修改 Git Repository 狀態的操作，"
                "執行前必須經過 Permission Layer。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Git Commit message。",
                    }
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": (
                "Execute an allowed development command "
                "inside the current project. "
                "Use this for running tests or development tools "
                "such as pytest, python, php, composer, npm, node, "
                "or docker."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "program": {
                        "type": "string",
                        "description": (
                            "The executable program to run. "
                            "Allowed programs include "
                            "python, pytest, php, composer, "
                            "npm, node, and docker."
                        ),
                    },
                    "arguments": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "description": ("Command arguments as a list of strings."),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "Maximum execution time in seconds. " "Default is 60."
                        ),
                        "minimum": 1,
                        "maximum": 600,
                    },
                },
                "required": [
                    "program",
                ],
            },
        },
    },
]
