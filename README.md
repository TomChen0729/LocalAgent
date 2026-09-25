# LocalAgent

LocalAgent 是一個從零開始實作的 **Local AI Coding Agent**。

使用 **Python + Ollama + Qwen3** 建立，不依賴 LangChain、LangGraph 或 MCP 等高階 Agent Framework。

專案目前主要用於：

- Local LLM / Agent 開發
- Agent Runtime 實作
- Tool Calling
- File / Git / Command 操作
- Permission / Safety
- Task Specification
- Verification
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
- Automated Testing

---

# 2. Requirements

## Hardware

目前開發環境：

```text
GPU:
NVIDIA RTX 2060 6GB Max-Q
```

GPU 並不是執行 LocalAgent 的絕對必要條件，但 Local LLM 推理會需要足夠的 CPU / RAM / GPU 資源。

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
│   ├── permissions.py
│   ├── command_executor.py
│   └── output_verifier.py
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
│   └── command_tools.py
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
    ├── test_agent_runtime.py
    ├── test_file_tools.py
    ├── test_git_tools.py
    ├── test_requirement_integration.py
    ├── test_requirement_verifier.py
    ├── test_permissions.py
    ├── test_command_executor.py
    ├── test_requirement_parser.py
    ├── test_task_specification_runtime.py
    ├── test_output_constraints.py
    ├── test_output_verifier.py
    ├── test_specification_validator.py
    └── test_runtime_specification_enforcement.py
```

### Main directories

| Directory       | Purpose                                       |
| --------------- | --------------------------------------------- |
| `agent/`        | Agent Runtime、Permission、Command Execution  |
| `tools/`        | Agent 可以使用的 Tools                        |
| `requirements/` | Task Specification、Requirement、Verification |
| `config/`       | Prompt 與設定                                 |
| `tests/`        | Automated Tests                               |
| `main.py`       | 啟動 LocalAgent                               |

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
Permission
 ↓
Tool Execution
 ↓
Verification
 ↓
Final Answer
```

LLM 負責決定下一步行動，Runtime 負責實際控制 Tool 是否可以執行。

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

# 10. Example Tasks

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

---

# 11. Run Tests

LocalAgent 使用 `pytest` 進行自動化測試。

執行：

```powershell
pytest -q
```

目前完整測試：

```text
240 passed
```

測試涵蓋：

```text
Agent Runtime
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
```

---

# 12. Troubleshooting

## Ollama 找不到模型

確認：

```powershell
ollama list
```

如果沒有：

```text
qwen3:8b
```

執行：

```powershell
ollama pull qwen3:8b
```

---

## Python 環境問題

確認：

```powershell
python --version
```

以及：

```powershell
where python
```

確認 Python 是目前 `.venv` 中的 Python。

---

## Agent 無法啟動

確認目前目錄：

```powershell
Get-Location
```

應該位於：

```text
LocalAgent
```

並確認：

```powershell
python main.py
```

可以正常執行。

---

# 13. Current Status

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

[x] Permission System
[x] Tool Constraints
[x] Task Specification
[x] Specification Validation
[x] Requirement Verification
[x] Output Verification
[x] Task State
[x] Tool History

[x] Automated Tests
```

目前測試：

```text
240 passed
```

---

# 14. Development Direction

目前下一階段開發方向為：

```text
Recovery
Codebase Understanding
Task Planning
Automated Testing
Error Analysis
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

# 15. Project Philosophy

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
