tools = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "列出指定目錄中的檔案與資料夾。"
                "要探索不熟悉的專案結構時，使用 recursive=true 一次看到所有層級。"
                "預設只列出第一層（recursive=false）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要列出的目錄路徑。留空或使用 '.' 代表專案根目錄。",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": (
                            "是否遞迴列出所有子目錄內容。"
                            "探索未知專案結構時設為 true；"
                            "只需要看某個資料夾的直接內容時設為 false（預設）。"
                        ),
                    },
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
            "description": (
                "讀取指定檔案內容。"
                "如果只需要檔案的特定區域，"
                "可以使用 start_line 與 end_line。"
                "當使用者指定明確的 Section 時，"
                "優先使用 read_section。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要讀取的檔案路徑。",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": ("開始讀取的行號，從 1 開始。"),
                        "minimum": 1,
                    },
                    "end_line": {
                        "type": "integer",
                        "description": ("結束讀取的行號。"),
                        "minimum": 1,
                    },
                    "max_size": {
                        "type": "integer",
                        "description": ("允許讀取的最大檔案大小，" "預設為 2 MB。"),
                        "minimum": 1,
                        "maximum": 20971520,
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_section",
            "description": (
                "讀取 Markdown 檔案中的指定 Section。"
                "當使用者明確指定某個章節、標題或 Heading 時，"
                "優先使用此工具，而不是讀取整份檔案。"
                "工具會自動找到指定 Heading，"
                "並讀取到下一個同層級或更高層級 Heading 之前。"
                "例如：# 28. Development Roadmap。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": ("Markdown 檔案路徑，" "例如 README.md。"),
                    },
                    "heading": {
                        "type": "string",
                        "description": (
                            "要讀取的 Markdown Heading。"
                            "例如 # 28. Development Roadmap。"
                        ),
                    },
                    "max_size": {
                        "type": "integer",
                        "description": ("允許讀取的最大檔案大小，" "預設為 2 MB。"),
                        "minimum": 1,
                        "maximum": 20971520,
                    },
                },
                "required": [
                    "path",
                    "heading",
                ],
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
            "description": (
                "搜尋專案檔案中的文字內容。"
                "可以指定搜尋文字、搜尋路徑、檔案類型以及最大結果數量。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "要搜尋的文字內容。"
                            "例如 PermissionManager、SYSTEM_PROMPT、def search_files。"
                        ),
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "要搜尋的專案目錄路徑。" "預設為目前專案根目錄。"
                        ),
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": (
                            "限制搜尋的檔案類型。" "例如 *.py、*.txt。預設為 *。"
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": ("最多回傳幾筆搜尋結果。" "預設為 200。"),
                        "minimum": 1,
                        "maximum": 200,
                    },
                },
                "required": ["query"],
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
            "name": "git_run",
            "description": (
                "執行任意 Git 子命令。"
                "當 git_status、git_log、git_diff、git_commit 無法滿足需求時，"
                "使用此工具執行其他 Git 操作。"
                "例如：push、pull、branch、checkout、stash、merge、"
                "rebase、tag、reset、fetch、remote、cherry-pick 等。"
                "subcommand 只填 git 子命令名稱（如 push），"
                "其餘參數放入 args 清單（如 [\"origin\", \"main\"]）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subcommand": {
                        "type": "string",
                        "description": (
                            "Git 子命令名稱，例如 push、pull、branch、"
                            "checkout、stash、merge、rebase、tag、reset、"
                            "fetch、remote、cherry-pick、clean、worktree。"
                            "只填單一子命令，不可包含空白或旗標。"
                        ),
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Git 子命令的參數，必須是 string list。"
                            "例如 [\"origin\", \"main\"]、[\"-b\", \"feature/xyz\"]、"
                            "[\"--oneline\", \"-10\"]。"
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "最大執行秒數。"
                            "網路操作（pull/push/fetch）預設 120 秒，"
                            "其他操作預設 30 秒。"
                            "最大 600 秒。"
                        ),
                        "minimum": 1,
                        "maximum": 600,
                    },
                },
                "required": ["subcommand"],
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
                "Allowed programs: "
                "python, python3, pytest, "
                "pip, pip3, uv, "
                "ruff, flake8, pylint, "
                "mypy, pyright, "
                "black, isort, "
                "make, "
                "npm, node, npx, yarn, pnpm, "
                "php, composer, "
                "cargo, go, ruby, bundle, "
                "docker, docker-compose."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "program": {
                        "type": "string",
                        "description": (
                            "The executable program to run. "
                            "Python tools: python, pytest, pip, pip3, uv, "
                            "ruff, flake8, pylint, mypy, pyright, black, isort. "
                            "Node tools: npm, node, npx, yarn, pnpm. "
                            "Other: php, composer, cargo, go, ruby, bundle, "
                            "docker, docker-compose, make."
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
