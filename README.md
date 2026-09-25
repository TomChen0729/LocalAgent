# LocalAgent

LocalAgent 是一個從零開始實作的 **Local AI Coding Agent**。

使用 **Python + Ollama + Qwen3** 建立，不依賴 LangChain、LangGraph 或 MCP 等高階 Agent Framework。

專案主要用於：

- Local LLM / Agent 開發
- Agent Runtime 實作
- Tool Calling
- File / Git / Command 操作
- Permission / Safety
- Task Specification
- Requirement Verification
- Output Verification
- Failure Classification
- Retry / Recovery
- Coding Agent 實驗

目前定位為 **Functional Local AI Agent Prototype**。

---

# 1. Features

目前 LocalAgent 已支援：

- Local LLM：Ollama + Qwen3
- Multi-turn Conversation
- Tool Calling
- Agent Loop
- File Tools
- Git Tools
- Command Execution
- Project Sandbox
- Tool Permission
- Tool Constraints
- Task Specification
- Specification Validation
- Requirement Verification
- Output Verification
- Task State
- Tool History
- Failure Classification
- Retry Policy
- Tool Recovery
- Recovery Policy
- Recovery Selection
- Recovery Argument Transformation
- Recovery Verification
- Automated Testing

目前 Agent 已具備從：

```text
User Request
    ↓
Task Understanding
    ↓
Task Specification
    ↓
Specification Validation
    ↓
Tool Selection
    ↓
Permission / Constraint Check
    ↓
Tool Execution
    ↓
Failure Detection
    ↓
Retry / Recovery
    ↓
Verification
    ↓
Requirement Verification
    ↓
Final Answer
```

的基本執行能力。

---

# 2. Requirements

## Hardware

目前開發環境：

```text
GPU:

NVIDIA RTX 2060 6GB Max-Q
```

GPU 並不是執行 LocalAgent 的絕對必要條件，但 Local LLM 推理需要足夠的 CPU / RAM / GPU 資源。

## Software

```text
Windows
Python 3.14+
Git
Ollama
```

目前開發環境版本：

```text
Python: 3.14.0
Ollama: 0.34.3
Git: 2.41.0.windows.3
LLM: Qwen3 8B
```

目前主要 Python 套件：

```text
ollama
pytest
```

---

# 3. Project Structure

```text
LocalAgent/
│
├── README.md
├── main.py
│
├── agent/
│   ├── __init__.py
│   ├── runtime.py
│   ├── state.py
│   ├── tool_runner.py
│   ├── permissions.py
│   ├── command_executor.py
│   │
│   ├── failure_classifier.py
│   ├── retry_policy.py
│   │
│   ├── recovery_policy.py
│   ├── recovery_selector.py
│   ├── recovery_executor.py
│   ├── recovery_attempt.py
│   ├── recovery_arguments.py
│   └── recovery_manager.py
│
├── config/
│   ├── __init__.py
│   └── prompts.py
│
├── tools/
│   ├── __init__.py
│   ├── definitions.py
│   ├── file_tools.py
│   ├── git_tools.py
│   ├── command_tools.py
│   ├── project_context.py
│   │
│   └── parsers/
│       ├── __init__.py
│       └── markdown_parser.py
│
├── requirements/
│   ├── __init__.py
│   ├── verifier.py
│   ├── specification.py
│   ├── parser.py
│   ├── output_verifier.py
│   └── specification_validator.py
│
└── tests/
    ├── conftest.py
    │
    ├── test_agent_runtime.py
    ├── test_file_tools.py
    ├── test_git_tools.py
    ├── test_requirement_integration.py
    ├── test_requirement_verifier.py
    ├── test_permissions.py
    ├── test_command_executor.py
    │
    ├── test_requirement_parser.py
    ├── test_task_specification_runtime.py
    ├── test_output_constraints.py
    ├── test_output_verifier.py
    ├── test_specification_validator.py
    ├── test_runtime_specification_enforcement.py
    │
    ├── test_failure_classifier.py
    ├── test_failure_classifier_contract.py
    ├── test_retry_policy.py
    ├── test_runtime_retry.py
    │
    ├── test_state.py
    ├── test_tool_runner.py
    │
    ├── test_recovery_policy.py
    ├── test_recovery_selector.py
    ├── test_recovery_executor.py
    ├── test_recovery_attempt.py
    ├── test_recovery_arguments.py
    ├── test_recovery_manager.py
    ├── test_runtime_recovery.py
    └── test_recovery_e2e.py
```

## Main directories

| Directory        | Purpose                                                                |
| ---------------- | ---------------------------------------------------------------------- |
| `agent/`         | Agent Runtime、Task State、Tool Execution、Permission、Retry、Recovery |
| `tools/`         | Agent 可以使用的 Tools                                                 |
| `tools/parsers/` | 特定格式檔案的 Parser，例如 Markdown                                   |
| `requirements/`  | Task Specification、Requirement、Verification                          |
| `config/`        | Prompt 與設定                                                          |
| `tests/`         | Automated Tests                                                        |
| `main.py`        | 啟動 LocalAgent                                                        |

---

# 4. Installation

## Step 1. Clone Repository

```powershell
git clone <repository-url>

cd LocalAgent
```

---

## Step 2. Create Virtual Environment

```powershell
python -m venv .venv
```

啟動：

```powershell
.\.venv\Scripts\Activate.ps1
```

啟動成功後，Terminal 前面應該會看到：

```text
(.venv)
```

---

## Step 3. Install Python Dependencies

目前主要使用：

```powershell
pip install ollama pytest
```

如果專案之後新增 `requirements.txt`，可以改成：

```powershell
pip install -r requirements.txt
```

---

# 5. Install Ollama

確認 Ollama 是否已安裝：

```powershell
ollama --version
```

確認 Ollama 可以正常使用後，下載 Qwen3：

```powershell
ollama pull qwen3:8b
```

確認模型：

```powershell
ollama list
```

應該可以看到：

```text
qwen3:8b
```

---

# 6. Start LocalAgent

確認：

```text
(.venv)
```

已經啟用，並且目前位於：

```text
LocalAgent/
```

然後執行：

```powershell
python main.py
```

看到：

```text
You >
```

代表 Agent 已經啟動。

例如：

```text
You > 請讀取 README.md，告訴我目前完成哪些 Phase。
```

LocalAgent 會先建立 Task Specification，再由 Agent 決定需要使用的 Tool。

---

# 7. How LocalAgent Works

基本流程：

```text
User
  ↓
Task Specification
  ↓
Specification Validation
  ↓
Agent Runtime
  ↓
Qwen3
  ↓
Tool Selection
  ↓
Tool Constraint
  ↓
Permission
  ↓
Tool Execution
  ↓
Failure Classification
  ↓
Retry / Recovery
  ↓
Verification
  ↓
Requirement Verification
  ↓
Final Answer
```

LLM 負責決定下一步行動。

Runtime 負責：

- Tool 是否允許執行
- Permission 是否通過
- Tool Constraint 是否符合
- Tool 是否實際成功
- 是否需要 Retry
- 是否需要 Recovery
- Recovery 後是否通過 Verification
- Task Requirement 是否完成

簡單來說：

```text
LLM
 ↓
Decision

Runtime
 ↓
Control / Execution

Tool
 ↓
Environment Action

Verification
 ↓
Reality Check
```

---

# 8. Available Tools

## File Tools

目前支援：

```text
list_files
file_exists
read_file
read_section
write_file
create_directory
search_files
edit_file
delete_file
```

其中：

```text
read_file
```

用於讀取完整檔案。

```text
read_section
```

用於讀取 Markdown 檔案中的指定章節。

例如：

```text
請讀取 README.md 的 Development Roadmap 章節。
```

如果 `read_section` 無法完成指定操作，Runtime 可以依照 Recovery Policy 嘗試使用替代 Tool。

目前已實作的替代 Recovery：

```text
read_section
      ↓
     FAIL
      ↓
  NOT_FOUND
      ↓
 Recovery Policy
      ↓
   read_file
```

---

## Git Tools

目前支援：

```text
git_status
git_log
git_diff
git_commit
```

Git 操作受到 Permission Layer 控制。

---

## Command Execution

Agent 可以透過受控的 Command Tool 執行指令。

例如：

```text
請執行 pytest，確認目前測試是否全部通過。
```

Command Execution 受到 Permission Layer 控制。

---

# 9. Permission System

不同 Tool 具有不同權限。

```text
read
    ↓
自動允許

write
    ↓
需要確認

edit
    ↓
需要確認

delete
    ↓
需要輸入 DELETE

execute
    ↓
需要確認

commit
    ↓
需要確認
```

未知 Tool 預設拒絕。

---

# 10. Task Specification

LocalAgent 會先將 User Request 轉換成結構化 Task Specification。

主要包含：

```text
Objective
Tool Constraints
State Requirements
Output Constraints
```

例如：

```text
User:

請讀取 README.md 的 Features 章節，
告訴我目前有哪些功能。
```

可能被解析成：

```text
Objective:
    type = inspect
    target = README.md
    focus = Features

Tool Constraints:
    allowed_tools = []
    forbidden_tools = []

State Requirements:
    []

Output Constraints:
    language = zh-TW
```

Task Specification 建立後會先經過 Specification Validation。

只有通過驗證後，Agent 才會進入後續執行流程。

---

# 11. Requirement Verification

Requirement Verification 用於確認 User 的實際需求是否完成。

目前支援：

```text
file_exists
contains
not_contains
```

Verification 不依賴 LLM 自己宣稱「任務已完成」。

而是直接檢查實際 Project State。

例如：

```text
Requirement:

README.md 必須包含 "Recovery"
```

Runtime 會直接檢查：

```text
README.md
    ↓
contains("Recovery")
    ↓
PASS / FAIL
```

這可以避免 Agent 只根據自己的回答宣稱任務完成。

---

# 12. Output Verification

LocalAgent 也會針對最終輸出進行驗證。

目前支援的 Output Constraints 包含：

```text
parameter_names_only
no_analysis
no_suggestions
no_examples
max_words
language
```

例如 User 要求：

```text
只列出參數名稱，不要分析。
```

Runtime 可以在最終回答後進行 Output Verification。

---

# 13. Failure Classification

Tool 執行失敗後，LocalAgent 會先進行 Failure Classification。

目前支援：

```text
NONE
INVALID_INPUT
NOT_FOUND
PERMISSION_DENIED
EXECUTION_ERROR
TIMEOUT
CONSTRAINT_VIOLATION
UNKNOWN
```

例如：

```text
Tool Result
    ↓
"找不到指定的檔案"
    ↓
Failure Classification
    ↓
NOT_FOUND
```

Failure Classification 是 deterministic component，不依賴 LLM 判斷。

---

# 14. Retry Policy

當 Tool 發生可重試的錯誤時，Runtime 可以依照 Retry Policy 判斷是否允許重新嘗試。

目前不同 Failure Category 有不同 Retry Limit。

例如：

```text
NOT_FOUND
    ↓
Retry allowed

EXECUTION_ERROR
    ↓
Retry allowed

TIMEOUT
    ↓
Retry allowed

PERMISSION_DENIED
    ↓
No Retry

CONSTRAINT_VIOLATION
    ↓
No Retry
```

Retry Policy 負責判斷：

```text
Should Retry?
Retry Count
Maximum Retries
Reason
```

Retry Policy 本身不執行 Tool。

---

# 15. Tool Recovery

如果 Retry 無法解決問題，或者錯誤類型適合使用替代 Tool，Runtime 可以進入 Recovery。

目前 Recovery 流程包含：

```text
Tool Failure
    ↓
Failure Classification
    ↓
Recovery Policy
    ↓
Recovery Attempt Check
    ↓
Recovery Selection
    ↓
Argument Transformation
    ↓
ToolRunner
    ↓
Alternative Tool
    ↓
Verification
    ↓
Requirement Verification
```

目前已實作的 Alternative Tool Recovery：

```text
read_section
    ↓
read_file
```

Recovery 有獨立的：

```text
RecoveryPolicy
RecoverySelector
RecoveryExecutor
RecoveryAttemptPolicy
RecoveryArgumentAdapter
RecoveryManager
```

Recovery 不會直接繞過 ToolRunner 執行 Tool。

---

# 16. Project Sandbox

LocalAgent 支援 Project Context。

AgentRuntime 可以指定：

```text
project_path
```

所有 File Tool 操作都會受到 Project Path 限制。

同時會阻止：

```text
Path Traversal
```

例如：

```text
../../some-file
```

不能直接跳出目前 Project。

另外也會保護部分不應被 Agent 一般操作的目錄，例如：

```text
.git
.venv
__pycache__
node_modules
```

---

# 17. Example Tasks

## Read Project

```text
請讀取 README.md，告訴我這個專案有哪些功能。
```

## Read Specific Section

```text
請讀取 README.md 的 Project Structure 章節。
```

## Create File

```text
請建立 hello.py，內容是：

print("Hello LocalAgent")
```

## Run Command

```text
請執行 pytest，確認測試結果。
```

## Git

```text
請查看目前 Git status。
```

## Recovery

```text
請讀取 README.md 的一個不存在的章節。
```

這類操作可以用來測試 Agent 的 Failure Classification 與 Recovery。

---

# 18. Run Tests

LocalAgent 使用 `pytest` 進行自動化測試。

執行：

```powershell
pytest -q
```

目前完整 Regression Test：

```text
339 passed
```

測試涵蓋：

```text
Agent Runtime
Task State
Tool Runner
File Tools
Git Tools
Command Execution
Permission System

Task Specification
Requirement Parser
Requirement Verification
Specification Validation
Output Verification
Runtime Enforcement

Failure Classification
Retry Policy

Recovery Policy
Recovery Selector
Recovery Executor
Recovery Attempt
Recovery Arguments
Recovery Manager
Runtime Recovery
Recovery E2E
```

目前所有測試均已通過。

---

# 19. Current Development Status

目前 LocalAgent 已完成：

```text
[x] Local LLM
[x] Ollama
[x] Qwen3

[x] Multi-turn Conversation
[x] Tool Calling
[x] Agent Loop

[x] File Tools
[x] Git Tools
[x] Command Execution
[x] Project Sandbox

[x] Permission System
[x] Tool Constraints

[x] Task Specification
[x] Specification Validation
[x] Requirement Verification
[x] Output Verification

[x] Task State
[x] Tool History

[x] Failure Classification
[x] Retry Policy

[x] Recovery Policy
[x] Recovery Selection
[x] Recovery Execution
[x] Recovery Attempt Control
[x] Recovery Argument Transformation
[x] Recovery Manager

[x] Recovery → Verification
[x] Recovery → Requirement Verification
[x] Recovery E2E

[x] Automated Tests
```

目前完整測試：

```text
339 passed
```

---

# 20. Development Roadmap

目前主要開發階段：

```text
Phase 1  LLM + Tool Calling
    ↓
Phase 2  File Tools
    ↓
Phase 3  Automated Testing
    ↓
Phase 4  Agent Runtime
    ↓
Phase 5  Permission / Safety
    ↓
Phase 6  Git Tools
    ↓
Phase 7  Command Execution
    ↓
Phase 8  Task Understanding
    ↓
Phase 9  Recovery
    ↓
Phase 9 Architecture Audit
    ↓
Phase 10 Product Architecture
    ↓
Phase 11 Memory / Context
    ↓
Phase 12 Advanced Agent
```

目前：

```text
Phase 1   ✅
Phase 2   ✅
Phase 3   ✅
Phase 4   ✅
Phase 5   ✅
Phase 6   ✅
Phase 7   ✅
Phase 8   ✅
Phase 9   ✅
```

目前 Phase 9 已完成 Recovery、Verification Integration 與 End-to-End Recovery Testing。

---

# 21. Future Development Direction

下一階段預計先進行 Architecture Audit。

主要確認：

```text
AgentRuntime
    ↓
是否維持 Orchestrator 責任
```

以及：

```text
Task State
Tool Execution
Retry
Recovery
Verification
Requirement Verification
Permission
```

之間的責任是否清楚分離。

完成 Architecture Audit 後，再進入：

```text
Codebase Understanding
        ↓
Task Planning
        ↓
Code Modification
        ↓
Test Execution
        ↓
Error Analysis
        ↓
Automatic Correction
```

長期目標：

```text
User Requirement
        ↓
Task Understanding
        ↓
Planning
        ↓
Codebase Understanding
        ↓
Code Modification
        ↓
Test Execution
        ↓
Error Analysis
        ↓
Recovery
        ↓
Requirement Verification
        ↓
Git Commit
        ↓
Human Approval
        ↓
Git Push
```

---

# 22. Project Philosophy

LocalAgent 的核心理念：

```text
LLM
 ↓
Decision

Runtime
 ↓
Control / Execution

Tool
 ↓
Environment Action

Verification
 ↓
Reality Check
```

簡單來說：

> **讓 LLM 負責思考，讓 Runtime 負責控制。**
