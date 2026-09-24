# LocalAgent

一個從零開始實作的 **Local Coding Agent（本機程式開發 Agent）**。

LocalAgent 使用 **Python + Ollama + Qwen3** 建立，主要目的不是直接套用現成的 Agent Framework，而是從底層理解一個 AI Coding Agent 是如何運作的。

目前專案已實作：

* 本機 LLM
* Ollama
* Qwen3 4B
* 多輪對話
* Tool Calling
* Agent Loop
* 多 Tool Chain
* 檔案讀取
* 檔案寫入
* 資料夾建立
* 專案結構檢查
* Sandbox 路徑安全限制
* Verification 驗證流程
* Agent Trace
* 模組化 Tool 架構

---

# 1. 專案介紹

現代 AI Coding Agent，例如各種能夠協助撰寫程式碼的 Agent，表面上看起來非常複雜，但其核心概念可以簡化成：

```text
使用者
  ↓
LLM
  ↓
判斷是否需要 Tool
  ↓
Tool Calling
  ↓
Python Tool
  ↓
操作實際環境
  ↓
Tool Result
  ↓
LLM
  ↓
繼續判斷
  ↓
最終回答
```

LocalAgent 的目標就是從這個最基本的架構開始，一步一步建立自己的 Local Coding Agent。

目前沒有使用：

```text
LangChain
LangGraph
MCP
其他高階 Agent Framework
```

而是直接使用 Python 與 Ollama 實作。

這樣做的主要目的，是希望先理解：

> **Agent 到底是怎麼運作的，而不是只知道怎麼使用 Agent Framework。**

---

# 2. 目前架構

目前 LocalAgent 的整體架構如下：

```text
                    ┌─────────────────┐
                    │      使用者      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     main.py     │
                    │  Agent Runtime  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Ollama      │
                    │    Qwen3 4B     │
                    └────────┬────────┘
                             │
                         Tool Call
                             │
                             ▼
                    ┌─────────────────┐
                    │ execute_tool()  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌─────────────────┐
        │list_files│   │read_file │   │create_directory │
        └──────────┘   └──────────┘   └─────────────────┘
              │              │                │
              └──────────────┼────────────────┘
                             ▼
                    ┌─────────────────┐
                    │   Tool Result   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      Qwen       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    最終回答     │
                    └─────────────────┘
```

---

# 3. Agent Loop

LocalAgent 最核心的部分是 **Agent Loop**。

基本流程：

```text
User Input
    ↓
Qwen
    ↓
是否需要 Tool？
    │
    ├── 否
    │    ↓
    │  Final Answer
    │
    └── 是
         ↓
      Tool Call
         ↓
      Python Runtime
         ↓
      執行 Tool
         ↓
      Tool Result
         ↓
      Qwen
         ↓
      再次判斷
```

因此 Agent 並不是：

```text
使用者 → LLM → 回答
```

而是：

```text
使用者
 ↓
LLM
 ↓
Tool
 ↓
結果
 ↓
LLM
 ↓
Tool
 ↓
結果
 ↓
LLM
 ↓
回答
```

這也是 LocalAgent 與單純 Chatbot 的重要差異之一。

---

# 4. 專案目錄結構

目前專案結構：

```text
LocalAgent/
│
├── main.py
│
├── config/
│   ├── __init__.py
│   └── prompts.py
│
├── tools/
│   ├── __init__.py
│   ├── definitions.py
│   └── file_tools.py
│
├── testProject/
│   └── test.py
│
├── .venv/
│
└── README.md
```

其中：

```text
testProject/
```

是目前測試 Agent 功能時建立的測試資料夾。

它不是 LocalAgent 運作所必要的目錄。

而：

```text
.venv/
```

是 Python 虛擬環境。

**不應該上傳到 GitHub。**

---

# 5. 各檔案功能

## `main.py`

LocalAgent 的主要 Runtime。

負責：

* 接收使用者輸入
* 維護對話紀錄
* 呼叫 Ollama
* 將 Tool Definition 傳給 LLM
* 接收 Tool Call
* 執行 Tool
* 將 Tool Result 回傳給 LLM
* 持續執行 Agent Loop
* 顯示 Agent Trace
* 輸出最終回答

可以把它理解成：

> **Agent 的控制中心。**

---

## `config/prompts.py`

負責管理 Agent 的 System Prompt。

目前包含：

### 語言規則

要求 Agent：

```text
使用繁體中文
使用台灣常用用語
避免使用簡體中文
```

### Tool 使用規則

告訴 Agent：

```text
什麼情況可以使用 list_files
什麼情況使用 read_file
什麼情況使用 write_file
什麼情況使用 create_directory
```

### 安全規則

例如：

```text
只能操作 LocalAgent 專案目錄內的檔案。
```

### 驗證規則

如果使用者要求：

```text
確認
檢查
驗證
```

Agent 必須實際使用 Tool 進行確認。

---

# 6. `tools/definitions.py`

這個檔案負責定義：

> **LLM 可以使用哪些 Tool，以及這些 Tool 需要什麼參數。**

目前有四個 Tool：

```text
list_files
read_file
write_file
create_directory
```

例如：

```text
read_file
    ↓
path
```

LLM 看到的是 Tool 的：

```text
名稱
描述
參數
必要參數
```

但是 Tool Definition 本身不會真的操作檔案。

它只是告訴 LLM：

> 「你可以使用這個功能，而且要按照這個格式呼叫。」

---

# 7. `tools/file_tools.py`

這個檔案才是真正執行檔案系統操作的地方。

目前包含：

## `list_files()`

列出 LocalAgent 專案中的檔案與資料夾。

例如：

```text
[FILE] main.py
[DIR]  config
[DIR]  tools
```

---

## `read_file(path)`

讀取指定檔案。

例如：

```text
read_file("main.py")
```

會取得：

```text
main.py
```

的實際內容。

---

## `write_file(path, content)`

建立或修改檔案。

例如：

```text
write_file(
    "testProject/test.py",
    "for i in range(1, 11):\n    print(i)"
)
```

---

## `create_directory(path)`

建立資料夾。

例如：

```text
create_directory("testProject")
```

---

# 8. Tool Calling

LocalAgent 使用 Ollama 提供的 Tool Calling 功能。

需要注意：

> **Qwen 並不是直接執行 Python 函式。**

例如使用者說：

```text
讀取 main.py
```

Qwen 可能產生：

```text
Tool Call:

read_file
{
    "path": "main.py"
}
```

接著 Python Runtime 收到這個 Tool Call：

```text
Qwen
 ↓
Tool Call
 ↓
execute_tool()
 ↓
read_file()
 ↓
取得檔案內容
 ↓
Tool Result
 ↓
Qwen
```

最後 Qwen 才根據 Tool Result 回答使用者。

---

# 9. 多 Tool Chain

目前 Agent 已經可以連續執行多個 Tool。

例如使用者要求：

```text
在 testProject 底下建立 test.py，
內容是用 for 迴圈印出 1 到 10。
```

Agent 可能執行：

```text
Qwen
 ↓
list_files
 ↓
Tool Result
 ↓
Qwen
 ↓
create_directory
 ↓
Tool Result
 ↓
Qwen
 ↓
write_file
 ↓
Tool Result
 ↓
Qwen
 ↓
Final Answer
```

也就是：

> **Tool → Result → Tool → Result → Tool → Result → Final Answer**

這代表目前的 Agent 已經不是只能執行單一步驟。

---

# 10. Sandbox 安全機制

LocalAgent 目前有實際的檔案系統 Sandbox。

Agent 只能操作：

```text
LocalAgent/
```

底下的檔案與資料夾。

例如：

```text
LocalAgent/
├── main.py
├── config/
├── tools/
└── testProject/
```

允許：

```text
main.py

config/prompts.py

tools/file_tools.py

testProject/test.py
```

但不允許：

```text
../outsideProject
```

或任何跳出 LocalAgent 專案目錄的路徑。

---

# 11. 為什麼不能只靠 System Prompt？

這是目前專案非常重要的一個設計概念。

System Prompt 可以告訴 LLM：

```text
不要操作專案之外的檔案。
```

但是不能把它當成真正的安全機制。

因為 LLM 本身仍然可能：

```text
判斷錯誤
產生錯誤 Tool Call
理解錯誤
```

因此真正的限制是在 Python Tool 裡面實作。

目前使用：

```python
project_path = get_project_path()

file_path = (project_path / path).resolve()

file_path.relative_to(project_path)
```

如果路徑跳出專案目錄，就直接拒絕。

因此架構是：

```text
System Prompt
    ↓
告訴 Agent 不可以越界

Python Tool
    ↓
真正強制限制不能越界
```

也就是：

> **LLM 負責遵守規則，Runtime 負責強制執行規則。**

---

# 12. Verification 驗證機制

目前 Agent 也加入了基本的 Verification 概念。

例如使用者要求：

```text
請確認 testProject/test.py 的內容是否真的正確。
```

Agent 不應該直接回答：

```text
正確。
```

而是需要：

```text
Qwen
 ↓
read_file
 ↓
取得實際檔案內容
 ↓
Qwen
 ↓
分析內容
 ↓
回答
```

例如：

```text
🧠 Agent：需要讀取指定檔案的實際內容。
🔧 Tool：read_file
📥 Tool 已完成

Qwen > testProject/test.py 的內容正確。
```

這個流程的核心概念是：

```text
Action
 ↓
Verification
 ↓
Conclusion
```

而不是：

```text
Action
 ↓
假設成功
```

---

# 13. Agent Trace

目前有加入 Agent Trace，方便觀察 Agent 實際執行了什麼。

例如：

```text
🧠 Agent：需要確認目前專案的檔案與資料夾結構。
🔧 Tool：list_files
📥 Tool 已完成

🧠 Agent：需要建立指定的資料夾。
🔧 Tool：create_directory
📥 Tool 已完成

🧠 Agent：需要建立或修改指定檔案。
🔧 Tool：write_file
📥 Tool 已完成

Qwen > 已成功在 testProject 目錄下建立 test.py。
```

其中：

```text
🧠 Agent
```

目前主要是簡短的 Agent Status / Summary。

它不是用來輸出或展示 LLM 的完整私有 Chain-of-Thought。

---

# 14. 目前技術堆疊

| 技術                | 用途                 |
| ----------------- | ------------------ |
| Python            | Agent Runtime      |
| Ollama            | 本機 LLM Runtime     |
| Qwen3 4B          | 本機語言模型             |
| Ollama Python SDK | Python 與 Ollama 溝通 |
| pathlib           | 檔案系統操作             |
| Python venv       | Python 虛擬環境        |

---

# 15. 開發環境

目前開發環境：

```text
作業系統：
Windows

GPU：
NVIDIA RTX 2060 6GB Max-Q

Ollama：
0.34.3

模型：
qwen3:4b
```

目前使用的 Qwen3：

```text
qwen3:4b
```

模型透過 Ollama 在本機執行，不需要使用雲端 API。

---

# 16. 安裝方式

## 16.1 Clone Repository

```bash
git clone https://github.com/<你的 GitHub 帳號>/LocalAgent.git
```

進入專案：

```bash
cd LocalAgent
```

---

## 16.2 建立 Python 虛擬環境

Windows：

```powershell
python -m venv .venv
```

啟動：

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 16.3 安裝 Python 套件

目前只需要：

```powershell
pip install ollama
```

---

# 17. 安裝 Ollama

先確認 Ollama 已經安裝。

官方網站：

https://ollama.com/

確認：

```powershell
ollama --version
```

---

# 18. 下載 Qwen3

目前使用：

```powershell
ollama pull qwen3:4b
```

確認模型：

```powershell
ollama list
```

應該可以看到：

```text
qwen3:4b
```

---

# 19. 啟動 LocalAgent

在專案根目錄執行：

```powershell
python main.py
```

看到：

```text
You >
```

之後即可開始與 Agent 互動。

例如：

```text
You > 列出目前專案有哪些檔案
```

或：

```text
You > 讀取 main.py
```

或：

```text
You > 在 testProject 建立 hello.py，內容是印出 Hello World
```

退出：

```text
/bye
```

---

# 20. 使用範例

## 建立檔案

使用者：

```text
在 testProject 底下建立 test.py，
內容是用 for 迴圈印出 1 到 10
```

Agent：

```text
🧠 Agent：需要確認目前專案的檔案與資料夾結構。
🔧 Tool：list_files
📥 Tool 已完成

🧠 Agent：需要建立指定的資料夾。
🔧 Tool：create_directory
📥 Tool 已完成

🧠 Agent：需要建立或修改指定檔案。
🔧 Tool：write_file
📥 Tool 已完成

Qwen > 已成功在 testProject 目錄下建立 test.py。
```

---

# 21. 驗證檔案

使用者：

```text
請確認 testProject/test.py 的內容是否真的正確
```

Agent：

```text
🧠 Agent：需要讀取指定檔案的實際內容。
🔧 Tool：read_file
📥 Tool 已完成

Qwen > testProject/test.py 的內容正確。
```

這代表 Agent 並不是單純相信自己上一個 Tool 的執行結果，而是重新取得實際檔案內容進行確認。

---

# 22. 安全性測試

如果使用者要求：

```text
請在 ../outsideProject 建立資料夾
```

Agent 會拒絕操作專案目錄之外的路徑。

例如：

```text
Qwen > 根據安全規則，我無法操作專案目錄之外的路徑。
```

即使 Agent 嘗試產生錯誤路徑，Python Tool 仍然會進行第二層安全檢查。

---

# 23. 目前限制

目前 LocalAgent 還是一個早期的功能型 Prototype。

目前尚未實作：

```text
search_files
terminal / shell
Git Tool
程式碼執行
Diff
Patch
自動測試
Persistent Memory
Permission System
```

因此目前它比較接近：

```text
「可以操作專案檔案的 Local Agent」
```

而不是完整的：

```text
「AI Software Engineer」
```

---

# 24. Tool Dispatcher

目前 Tool 執行方式仍然比較簡單。

在 `main.py` 中：

```python
if tool_name == "list_files":
    ...

elif tool_name == "read_file":
    ...

elif tool_name == "write_file":
    ...

elif tool_name == "create_directory":
    ...
```

這種方式在 Tool 很少時沒有問題。

但未來如果增加：

```text
search_files
terminal
git
run_tests
apply_patch
```

`if / elif` 會越來越長。

因此未來會改成：

```text
Tool Registry
```

讓 Tool 可以透過 Registry 動態註冊與執行。

---

# 25. 開發 Roadmap

## Phase 1：Agent Core

* [x] Ollama
* [x] 本機 LLM
* [x] Qwen3
* [x] 多輪對話
* [x] Tool Calling
* [x] Agent Loop
* [x] Multi Tool Chain
* [x] File Read
* [x] File Write
* [x] Directory Create
* [x] Sandbox
* [x] Agent Trace
* [x] Verification

---

## Phase 2：Codebase Understanding

下一階段主要讓 Agent 從：

```text
「可以操作檔案」
```

進一步變成：

```text
「可以搜尋與理解程式碼專案」
```

預計：

* [ ] `search_files`
* [ ] Recursive Project Search
* [ ] 程式碼搜尋
* [ ] Symbol Search
* [ ] Project Context
* [ ] Structured Tool Result
* [ ] Tool Registry

例如：

```text
使用者：

哪裡有使用 execute_tool？
```

Agent：

```text
search_files
      ↓
搜尋整個專案
      ↓
取得符合結果
      ↓
Qwen 分析結果
      ↓
回答使用者
```

---

# 26. Phase 3：Coding Agent

預計加入：

* [ ] Terminal Tool
* [ ] Python 執行
* [ ] Git Tool
* [ ] Diff
* [ ] Patch
* [ ] 修改前預覽
* [ ] Permission Confirmation
* [ ] Error Recovery
* [ ] Test Execution

例如：

```text
使用者：

幫我修正這個 Python 錯誤。
```

未來可能變成：

```text
搜尋程式碼
      ↓
讀取相關檔案
      ↓
分析錯誤
      ↓
提出修改
      ↓
顯示 Diff
      ↓
詢問使用者是否允許
      ↓
修改檔案
      ↓
執行測試
      ↓
驗證結果
```

---

# 27. Phase 4：Advanced Agent

未來可能加入：

* [ ] Persistent Memory
* [ ] Context Management
* [ ] Project Understanding
* [ ] Task Planning
* [ ] Advanced Verification
* [ ] Automatic Debugging
* [ ] Agent State
* [ ] Tool Permission System
* [ ] Long-running Tasks

最終希望逐步形成：

```text
                 ┌──────────────┐
                 │     User     │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │     Agent    │
                 └──────┬───────┘
                        ↓
              ┌───────────────────┐
              │       LLM         │
              └─────────┬─────────┘
                        ↓
                Tool / Planning
                        ↓
              ┌───────────────────┐
              │ Local Environment │
              └─────────┬─────────┘
                        ↓
                  Observation
                        ↓
                       LLM
                        ↓
                 Verification
                        ↓
                  Final Result
```

---

# 28. 設計理念

## 28.1 先理解 Agent，再使用 Framework

本專案不從：

```text
LangChain
LangGraph
MCP
```

開始。

而是從：

```text
Python
+
LLM
+
Tool Calling
+
Agent Loop
```

開始。

原因是希望先理解 Agent 的底層運作方式。

---

## 28.2 LLM 與 Tool 分離

LLM 負責：

```text
理解使用者需求
決定是否需要 Tool
選擇 Tool
提供 Tool 參數
分析 Tool Result
```

Python Runtime 負責：

```text
執行 Tool
檢查安全性
控制檔案存取
回傳 Tool Result
```

因此：

```text
LLM
 ↓
決策

Python Runtime
 ↓
執行與控制
```

---

## 28.3 Tool Result 優先於猜測

當 Agent 需要知道實際專案狀態時，不應該自行猜測。

例如：

```text
不要：

「我記得 main.py 裡面應該有 execute_tool。」
```

而應該：

```text
search / read
      ↓
取得實際內容
      ↓
根據結果回答
```

---

## 28.4 安全性不能只依賴 Prompt

Prompt 可以降低錯誤操作的機率。

但真正的安全限制應該存在於 Runtime / Tool 層。

因此：

```text
Prompt Security
+
Runtime Security
```

兩者共同形成 Agent 的安全邊界。

---

# 29. 專案目前定位

目前 LocalAgent 的定位是：

> **一個從零開始研究 Local Coding Agent 核心架構的實作型專案。**

目前已經完成：

```text
LLM
 ↓
Tool Calling
 ↓
Agent Loop
 ↓
Multiple Tool Chain
 ↓
Filesystem Tools
 ↓
Sandbox
 ↓
Verification
 ↓
Final Answer
```

下一個主要目標則是：

```text
「能操作檔案」
        ↓
「能搜尋程式碼」
        ↓
「能理解 Codebase」
        ↓
「能修改程式碼」
        ↓
「能執行測試」
        ↓
「能驗證修改結果」
```

---

# 30. Project Status

目前狀態：

**🟢 Early-stage Functional Prototype**

目前核心 Agent 架構已經可以正常運作。

目前已驗證：

```text
✓ Local LLM
✓ Ollama
✓ Qwen3
✓ Multi-turn Conversation
✓ Tool Calling
✓ Agent Loop
✓ Multiple Tool Chain
✓ File Read
✓ File Write
✓ Directory Creation
✓ Sandbox Protection
✓ Agent Trace
✓ Verification
```

目前正在從：

```text
「一個可以呼叫 Tool 的 LLM」
```

逐步發展成：

```text
「真正可以理解與操作程式碼專案的 Local Coding Agent」
```

---

# 31. License

目前本專案主要作為：

* 個人學習
* Agent 架構研究
* Local LLM 實驗
* Coding Agent 開發

使用。

License 尚未決定。

如果未來要公開作為 Open Source Project，可以考慮加入：

```text
MIT License
```

或其他適合的開源授權。
