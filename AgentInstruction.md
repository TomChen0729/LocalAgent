# AgentInstruction — LocalAgent 使用文件

> 版本：Phase 9.3+（含 Streaming、Auto Test Loop、Session 持久化）
> 最後更新：2026-09-28

---

## 目錄

1. [簡介](#1-簡介)
2. [快速開始](#2-快速開始)
3. [CLI 使用方式](#3-cli-使用方式)
4. [Session 管理（對話持久化）](#4-session-管理對話持久化)
5. [Streaming 輸出](#5-streaming-輸出)
6. [Auto Test Loop（自動測試）](#6-auto-test-loop自動測試)
7. [工具清單](#7-工具清單)
8. [Git 操作](#8-git-操作)
9. [Permission 系統](#9-permission-系統)
10. [Requirement Verification](#10-requirement-verification)
11. [Recovery 機制](#11-recovery-機制)
12. [行為限制與安全設計](#12-行為限制與安全設計)
13. [已知限制](#13-已知限制)
14. [進階配置](#14-進階配置)

---

## 1. 簡介

**LocalAgent** 是一個完全在本地執行的 AI Coding Agent，不依賴任何外部 API（無 OpenAI、無 Anthropic）。

核心特性：

- 🔒 **完全本地**：模型跑在 Ollama，資料不離開你的機器
- ⚡ **Streaming 輸出**：Token 即時顯示，不需要等待完整回答
- 🛡️ **安全設計**：所有寫入、執行操作需要使用者明確確認
- ✅ **Requirement Verification**：Agent 不自我宣告完成，Runtime 從檔案系統實際驗證（支援 Glob 路徑）
- 🧪 **Auto Test Loop**：寫完程式碼後自動跑 pytest，失敗自動修復
- 💾 **Session 持久化**：重啟後可繼續上次的任務
- 🔄 **Recovery 機制**：Tool 失敗時自動嘗試替代方案

---

## 2. 快速開始

### 前置需求

```bash
# 安裝 Ollama
# https://ollama.com/download

# 下載 Qwen3 模型
ollama pull qwen3:8b

# 安裝 Python 依賴
pip install ollama
```

### 啟動

```bash
python main.py
```

```
Local Coding Agent
📌 Session ID：ab12cd34
   （使用 --resume ab12cd34 繼續此 Session）
🧪 Auto Test   ⚡ Streaming
輸入 /bye 結束程式。

You >
```

### 基本對話

```
You > 幫我讀取 README.md 的前 20 行
You > 在 src/ 目錄下建立一個 calculator.py，要有 add 和 subtract 函式
You > 幫我 git commit，訊息是 "feat: add calculator module"
You > /bye
```

---

## 3. CLI 使用方式

### 基本啟動

```bash
python main.py
```

### 指令參數

| 參數 | 說明 | 範例 |
|---|---|---|
| `--resume <SESSION_ID>` | 繼續指定的 Session | `python main.py --resume ab12cd34` |
| `--list-sessions` | 列出所有可繼續的 Session | `python main.py --list-sessions` |
| `--no-auto-test` | 停用 Auto Test Loop | `python main.py --no-auto-test` |
| `--no-stream` | 停用 Streaming，一次印出完整回答 | `python main.py --no-stream` |

### 內建指令

| 指令 | 說明 |
|---|---|
| `/bye` | 結束程式（同時顯示 Session ID） |

---

## 4. Session 管理（對話持久化）

LocalAgent 每次完成任務後會自動把對話歷史儲存到磁碟。

### Session 儲存位置

```
~/.localagent/sessions/<session_id>.json
```

### 繼續上次任務

```bash
# 第一次啟動，注意 Session ID
python main.py
# 📌 Session ID：ab12cd34

# 做完事、關掉程式後，用 --resume 繼續
python main.py --resume ab12cd34
# ✅ 已載入 Session：ab12cd34
#    上次更新：2026-09-26T02:35:00
#    訊息數量：42
```

### 列出所有 Session

```bash
python main.py --list-sessions
```

```
Session ID   Updated                   Messages
--------------------------------------------------
ab12cd34     2026-09-26T02:48:00          42
c9f3e1a2     2026-09-25T19:22:00          18
```

### Context Window 管理

Resume 時只載入最後 **50 條訊息**（保留 system prompt），避免超出 Qwen3 的 context window。

---

## 5. Streaming 輸出

LocalAgent 預設啟用 Streaming，Token 從 LLM 生成的同時即時顯示。

### 運作原理

```
Agent 呼叫 Tool（中間步驟）
  → Ollama 在中間 chunk 回傳 tool_calls
  → Runtime 自動於整個串流中累計 tool_calls
  → 執行 Tool 並印出 TRACE（如 🔧 Tool：list_files）

Agent 給出最終回答（無 Tool Call）
  → Token 即時顯示：
    Qwen > 我已完成...（字一個一個出現）
```

### 思考狀態指示符與過濾

- **即時思考指示**：在等待模型回應或思考時顯示 `🤔 .....`，讓使用者知道後端正常運作。
- **`<think>` 區塊過濾**：自動過濾 Qwen3 內部思考過程，終端機只會顯示乾淨的最終輸出。

### 停用 Streaming

```bash
python main.py --no-stream
# 完整回答計算完才一次印出
```

---

## 6. Auto Test Loop（自動測試）

每次 Agent 寫完 Python 檔案後，Runtime 會自動執行 `pytest`，並把結果回傳給 Agent。

### 觸發條件（全部成立才執行）

1. 有 `.py` 檔案被寫入或修改
2. 專案中存在測試檔案（`test_*.py` 或 `*_test.py`）
3. `pytest` 已安裝

### 執行流程

```
Agent 寫完 calculator.py
  ↓
🧪 Auto Test：執行 pytest -x --tb=short -q
  ↓
  ├── ✅ PASS → 告知 Agent 測試通過，可繼續
  └── ❌ FAIL → 把錯誤訊息注入 LLM context
                   ↓
                Agent 讀到錯誤，用 edit_file 修復
                   ↓
                🧪 Auto Test：再次執行 pytest
                   ↓
                （最多重試 3 次）
```

### 停用 Auto Test

```bash
python main.py --no-auto-test
```

---

## 7. 工具清單

Agent 共有 **15 個工具**，分為三類：

### 📁 檔案操作（9 個）

| 工具 | 說明 | Permission |
|---|---|---|
| `list_files` | 列出目錄內容 | 自動允許 |
| `file_exists` | 確認檔案或資料夾是否存在 | 自動允許 |
| `read_file` | 讀取檔案（支援 `start_line` / `end_line`） | 自動允許 |
| `read_section` | 讀取 Markdown 指定 Heading 的內容 | 自動允許 |
| `search_files` | 搜尋專案內的文字（支援 `file_pattern`） | 自動允許 |
| `write_file` | 建立或覆寫檔案 | 需要確認 |
| `edit_file` | 精確取代檔案中的文字片段 | 需要確認 |
| `create_directory` | 建立資料夾 | 需要確認 |
| `delete_file` | 刪除檔案（需要輸入 `DELETE` 確認） | 強制確認 |

### 🔧 Git 操作（5 個）

| 工具 | 說明 | Permission |
|---|---|---|
| `git_status` | 查看 Repository 狀態與 branch | 自動允許 |
| `git_diff` | 查看未提交的差異 | 自動允許 |
| `git_log` | 查看 commit 歷史（預設最近 10 筆） | 自動允許 |
| `git_commit` | 建立 commit（包含 `git add -A`） | 需要確認 |
| `git_run` | 執行任意 git 子命令 | 依 subcommand |

### ⚙️ 命令執行（1 個）

| 工具 | 說明 | Permission |
|---|---|---|
| `execute_command` | 執行開發工具（timeout 最大 600 秒） | 需要確認 |

**允許執行的程式（30 個）：**

| 類別 | 程式 |
|---|---|
| Python | `python` `python3` `pytest` |
| 套件管理 | `pip` `pip3` `uv` |
| Linter | `ruff` `flake8` `pylint` |
| 型別檢查 | `mypy` `pyright` |
| Formatter | `black` `isort` |
| Build | `make` |
| JavaScript | `npm` `node` `npx` `yarn` `pnpm` |
| PHP | `php` `composer` |
| 其他語言 | `cargo` `go` `ruby` `bundle` |
| 容器 | `docker` `docker-compose` |

---

## 8. Git 操作

### 常用 `git_run` 範例

```
# 查看 branch（自動允許）
"幫我列出所有 git branch"
→ git_run("branch", ["-a"])

# 建立並切換 branch（需要確認）
"建立一個叫 feature/login 的 branch"
→ git_run("checkout", ["-b", "feature/login"])

# 推到遠端（需要確認，timeout 自動 120 秒）
"把目前的 branch push 到 origin"
→ git_run("push", ["origin", "feature/login"])

# 拉取最新（需要確認）
"git pull origin main"
→ git_run("pull", ["origin", "main"])

# 暫存
"先 stash 目前的修改"
→ git_run("stash", ["push", "-m", "WIP: 暫存"])

# Tag
"幫目前 commit 打一個 v1.0.0 的 tag"
→ git_run("tag", ["-a", "v1.0.0", "-m", "Release v1.0.0"])
```

### git_run Permission 對照

| Subcommand 類型 | Permission | 說明 |
|---|---|---|
| `status / log / diff / branch / tag / show / ...` | 自動允許 | 唯讀操作 |
| `push` | 需要確認（execute） | 遠端寫入 |
| `commit / checkout / merge / reset / stash / ...` | 需要確認（commit） | 本地寫入 |

### Timeout

- 網路操作（`pull / push / fetch / clone`）：預設 **120 秒**
- 其他操作：預設 **30 秒**
- 最大值：**600 秒**

### Conflict 解決流程

```
git_run("pull", ["origin", "main"])
  ↓ 若有 conflict
git_run("status")  # 找出衝突檔案
read_file("conflicted_file.py")  # 看到 <<<<<<< / ======= / >>>>>>>
edit_file(...)  # 解決 conflict markers
git_commit("resolve conflict: merge origin/main")
```

> **注意：** 需要事先設定 SSH key 或 credential helper，Agent 無法處理互動式密碼輸入。

---

## 9. Permission 系統

所有可能影響檔案系統或 Repository 的操作，都需要通過 Permission Layer。

### Permission 類型

| Action | 觸發工具 | 行為 |
|---|---|---|
| `read` | 所有讀取工具 | **自動允許**，不需確認 |
| `write` | `write_file`, `create_directory` | 輸入 `y` 允許 |
| `edit` | `edit_file` | 輸入 `y` 允許 |
| `commit` | `git_commit`, `git_run`（多數子命令） | 輸入 `y` 允許 |
| `execute` | `execute_command`, `git_run("push")` | 輸入 `y` 允許 |
| `delete` | `delete_file` | 必須輸入 `DELETE` 字串 |
| `unknown` | 未登記的工具 | **自動拒絕** |

---

## 10. Requirement Verification

LocalAgent 在任務開始時由 LLM 解析出 **Structured Requirements**，並在每次寫入操作後驗證。

### 驗證類型

| 類型 | 說明 | 精確路徑範例 | Glob 路徑範例 |
|---|---|---|---|
| `file_exists` | 確認檔案或資料夾存在 | `src/main.py` | `**/*.py` |
| `contains` | 確認檔案包含特定文字 | `requirements.txt` | `**/requirements.txt` |
| `not_contains` | 確認檔案不包含特定文字 | `main.py` | `**/*.py` |

### Glob 路徑支援

Glob 路徑讓 Parser 對「建立新專案」類任務也能生成有效 Requirement：

```json
// 精確路徑（知道確切名稱）
{"type": "file_exists", "path": "MyProject/main.py"}

// Glob 路徑（不確定資料夾名稱）
{"type": "file_exists", "path": "**/*.py"}
{"type": "contains",    "path": "**/requirements.txt", "text": "requests"}
```

### 建立型任務的 Requirement 生成規則

Parser 會根據使用者提到的技術推斷 Requirement：

| 使用者提到 | 自動生成 |
|---|---|
| Python 專案 | `file_exists: **/*.py` |
| 爬蟲 | `contains: **/requirements.txt → "requests"` |
| 視覺化 / matplotlib | `contains: **/requirements.txt → "matplotlib"` |
| pandas / 資料處理 | `contains: **/requirements.txt → "pandas"` |
| Flask / API | `contains: **/requirements.txt → "flask"` |
| 測試 / test | `file_exists: **/test_*.py` |

### 驗證觸發時機

1. `write_file` / `edit_file` / `create_directory` / `delete_file` 執行後
2. Agent 試圖給出最終答案時

---

## 11. Recovery 機制

當工具執行失敗時，Runtime 會自動嘗試 Recovery。

### 目前支援的 Recovery 規則

| 失敗情境 | 自動恢復方式 |
|---|---|
| `read_section` 找不到 heading | 自動改用 `read_file` 讀取整個檔案 |

### 失敗分類

| 類型 | 可重試 | 說明 |
|---|---|---|
| `NOT_FOUND` | ✅ | 找不到檔案或路徑 |
| `INVALID_INPUT` | ✅ | 輸入格式錯誤 |
| `EXECUTION_ERROR` | ✅ | 執行時發生問題 |
| `TIMEOUT` | ✅ | 逾時 |
| `PERMISSION_DENIED` | ❌ | 使用者拒絕 |
| `CONSTRAINT_VIOLATION` | ❌ | 工具被禁止 |

---

## 12. 行為限制與安全設計

### 路徑安全（Sandbox）

Agent **只能操作專案目錄內**的檔案，無法讀寫任意系統路徑。

```
✅ 允許：src/calculator.py
❌ 拒絕：/etc/passwd
❌ 拒絕：C:\Windows\System32\...
```

### 命令執行白名單

`execute_command` 只允許白名單內的 30 個程式（見工具清單）。

### Shell Injection 防護

所有命令使用 `shell=False`，arguments 為 list，不透過 shell 解析。

### 工具呼叫上限

```
MAX_TOOL_CALLS = 50
```

---

## 13. 已知限制

### LLM 相關

| 限制 | 說明 |
|---|---|
| Context Window | Qwen3:8b 約 8K–32K tokens |
| 複雜推理 | 8B 模型對複雜邏輯的一次成功率有限 |
| 大型 Repo | 超過幾百行的程式碼理解會不準確 |

### 功能限制

| 限制 | 說明 |
|---|---|
| 身份驗證 | git push/pull 需事先設定 SSH key 或 credential helper |
| `git add --patch` | 只支援 `git add -A`，無法選擇性 stage |
| Web 搜尋 | 不支援，Agent 不知道外部資訊 |
| Diff Preview | Permission Request 顯示完整 content，尚未實作 diff 格式 |

### Auto Test 限制

- 只偵測 `pytest`，不支援 `jest` / `go test` / `cargo test`
- 測試 timeout 上限 120 秒
- 每個 Task 最多自動修復 **3 次**

---

## 14. 進階配置

### `agent/runtime.py` 常數

| 常數 | 預設值 | 說明 |
|---|---|---|
| `MAX_TOOL_CALLS` | `50` | 每個 Task 最多呼叫幾次工具 |
| `MAX_REPEATED_TOOL_CALLS` | `3` | 相同工具+參數連續幾次視為循環 |
| `MAX_REQUIREMENT_FAILURES` | `3` | Requirement FAIL 多少次後停止 |
| `MAX_OUTPUT_VERIFICATION_FAILURES` | `3` | Output Constraint FAIL 多少次後停止 |
| `MAX_AUTO_TEST_FIX_ATTEMPTS` | `3` | Auto Test 失敗最多嘗試幾次修復 |

### `agent/session.py` 常數

| 常數 | 預設值 | 說明 |
|---|---|---|
| `MAX_MESSAGES_ON_RESUME` | `50` | Resume 時載入最後幾條訊息 |

### `agent/test_runner.py` 常數

| 常數 | 預設值 | 說明 |
|---|---|---|
| `MAX_OUTPUT_LINES` | `60` | 測試輸出截斷行數 |
| `DEFAULT_TIMEOUT` | `120` | pytest 執行 timeout（秒） |

### `agent/command_executor.py` 常數

| 常數 | 預設值 | 說明 |
|---|---|---|
| `DEFAULT_TIMEOUT` | `60` | 命令執行預設 timeout（秒） |
| `MAX_TIMEOUT` | `600` | 命令執行最大 timeout（秒） |

---

## 附錄 A：Session 檔案格式

```json
{
  "session_id": "ab12cd34",
  "created_at": "2026-09-26T02:30:00.123456",
  "updated_at": "2026-09-26T02:48:00.654321",
  "message_count": 42,
  "model": "qwen3:8b",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "幫我建立 calculator.py"},
    {"role": "assistant", "content": "..."}
  ]
}
```

## 附錄 B：啟動旗標速查

```bash
python main.py                                      # 標準啟動（Streaming + Auto Test）
python main.py --no-stream                          # 停用 Streaming
python main.py --no-auto-test                       # 停用 Auto Test
python main.py --no-stream --no-auto-test           # 最簡模式
python main.py --resume ab12cd34                    # 繼續 Session
python main.py --list-sessions                      # 列出所有 Session
```

---

*LocalAgent 是開源專案，歡迎 PR 和 Issue。*
