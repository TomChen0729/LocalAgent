tools = [
    # ========================================================
    # list_files
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出 LocalAgent 專案中的檔案與資料夾。"
            "預設只列出指定資料夾的一層內容。"
            "如果需要遞迴列出子資料夾，將 recursive 設為 true。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要列出的資料夾路徑。"
                        "例如 '.'、'test'、'config'",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否遞迴列出所有子資料夾與檔案。"
                        "預設為 false。",
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "是否包含隱藏檔案與隱藏資料夾。"
                        "預設為 false。",
                    },
                },
                "required": [],
            },
        },
    },
    # ========================================================
    # file_exists
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "file_exists",
            "description": "確認指定路徑是否存在，並判斷它是檔案還是資料夾。"
            "不會修改任何檔案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要確認的專案內路徑。",
                    },
                },
                "required": ["path"],
            },
        },
    },
    # ========================================================
    # read_file
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "讀取 LocalAgent 專案中的 UTF-8 文字檔案。"
            "修改檔案前應先使用此工具取得目前實際內容。"
            "可以使用 start_line 與 end_line 讀取特定行範圍。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要讀取的檔案路徑。",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "開始讀取的行號，從 1 開始。",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "結束讀取的行號。",
                    },
                },
                "required": ["path"],
            },
        },
    },
    # ========================================================
    # write_file
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "建立新的 UTF-8 文字檔案。"
            "預設禁止覆寫已存在的檔案。"
            "只有在確定需要完整覆寫既有檔案時才使用 overwrite=true。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要建立或覆寫的檔案路徑。",
                    },
                    "content": {
                        "type": "string",
                        "description": "完整的檔案內容。",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "是否允許覆寫既有檔案。" "預設為 false。",
                    },
                },
                "required": [
                    "path",
                    "content",
                ],
            },
        },
    },
    # ========================================================
    # create_directory
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "在 LocalAgent 專案內建立資料夾。"
            "如果資料夾已經存在，不會重複建立。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要建立的資料夾路徑。",
                    },
                },
                "required": ["path"],
            },
        },
    },
    # ========================================================
    # search_files
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "搜尋 LocalAgent 專案中的文字檔案內容。"
            "可以指定搜尋路徑與檔案 pattern。"
            "例如搜尋 Python 函式時，可以使用 query='def hello' "
            "與 file_pattern='*.py'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要搜尋的文字。",
                    },
                    "path": {
                        "type": "string",
                        "description": "搜尋範圍。" "例如 '.' 或 'test'。",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "檔案 pattern。"
                        "例如 '*.py'、'*.php'、'*.js'。"
                        "預設為 '*'。",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最多回傳多少筆搜尋結果。" "預設為 200。",
                    },
                },
                "required": ["query"],
            },
        },
    },
    # ========================================================
    # edit_file
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "精確修改 LocalAgent 專案中的文字檔案。"
            "old_text 必須在檔案中恰好出現一次。"
            "如果不存在或出現多次，Tool 將拒絕修改。"
            "修改既有檔案前應先使用 read_file 取得實際內容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要修改的檔案路徑。",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "檔案中目前存在、準備被替換的完整文字。",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "要替換成的新文字。",
                    },
                },
                "required": [
                    "path",
                    "old_text",
                    "new_text",
                ],
            },
        },
    },
    # ========================================================
    # delete_file
    # ========================================================
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "刪除 LocalAgent 專案中的指定檔案。"
            "這是高風險操作，必須明確指定 confirm=true。"
            "只能刪除檔案，不允許刪除資料夾。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要刪除的檔案路徑。",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "必須明確設為 true 才會執行刪除。",
                    },
                },
                "required": [
                    "path",
                    "confirm",
                ],
            },
        },
    },
]
