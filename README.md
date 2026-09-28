# 🤖 LocalAgent

> **A fully local AI Coding Agent — no cloud, no subscriptions, no data leaks.**

LocalAgent is an open-source AI coding assistant that runs entirely on your machine using [Ollama](https://ollama.com) and small open-weight models (default: `qwen3:8b`). It handles real coding tasks — reading files, writing code, running tests, making Git commits — all without sending a single byte to OpenAI or Anthropic.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black?logo=ollama)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Model](https://img.shields.io/badge/Model-qwen3%3A8b-orange)](https://ollama.com/library/qwen3)

[繁體中文](README.zh-TW.md) | English

---

## Why LocalAgent?

You already have a laptop. Why pay \$20/month for a cloud coding agent?

| Feature | LocalAgent | Claude Code |
|---|---|---|
| **Cost** | ✅ Free forever | ❌ \$20+/month |
| **Privacy** | ✅ 100% local, no data sent | ❌ Code sent to Anthropic |
| **Internet required** | ✅ No | ❌ Yes |
| **Model flexibility** | ✅ Any Ollama model | ❌ Claude only |
| **Edge / air-gap friendly** | ✅ Yes | ❌ No |
| **Open source** | ✅ MIT licensed | ❌ Proprietary |
| **Diff preview before edit** | ✅ Shows `+`/`-` before every change | ❌ No |
| **Requirement verification** | ✅ Glob-based file system check | ❌ No |

---

## ✨ Features

### 🗂️ Complete File Toolset
- Read, write, edit, delete, search, and list files
- Recursive directory listing — see the full project tree in one call
- Glob-pattern search across the entire project tree

### 🔧 Full Git CLI Integration
- `status`, `diff`, `log`, `commit`, `push`, `pull`, `branch`, `checkout`, `stash`, and more
- Commit messages generated automatically from context
- Fine-grained permission levels: staging (`add`) is separate from committing and pushing

### 🛡️ Diff Preview Before Every Change
- `edit_file` shows a full unified diff (`+`/`-` by line) before executing
- `write_file` shows a numbered line preview of new content
- You see exactly what will change before approving

### 🔐 Security Permission System
- Six permission levels: `read` / `write` / `edit` / `commit` / `execute` / `delete`
- Every sensitive action requires explicit CLI confirmation
- `git push` is classified at the highest risk level (`execute`)

### ✅ Command Execution Whitelist
- 30+ pre-approved programs: `pip`, `ruff`, `mypy`, `pytest`, `npm`, `cargo`, and more
- Unknown commands are blocked by default — no accidental shell injection
- Commands always run in the correct project directory (respects `--workdir`)

### 🔁 Auto Test Loop
- Automatically runs `pytest` after writing or editing Python files
- On failure, the agent reads the error output and self-corrects — up to N retries

### 📋 Requirement Verification
- Parses task requirements and verifies completion against the **actual file system**
- Extension-aware: verifying `README` also matches `README.md`, `README.txt`, etc.
- Reports which requirements are met before finishing a task

### 💾 Session Persistence + Naming
- Every conversation is saved with an auto-generated human-readable name
- `--resume <SESSION_ID>` continues the exact session — **including the workdir**
- Rename any session with `/rename <name>` during the chat
- `--list-sessions` shows name, workdir, timestamp, and message count

### 📂 Multi-Project Support via `--workdir`
- Point LocalAgent at any project directory without changing its install location
- Resuming a session automatically restores the original workdir — no need to re-specify

### ⚡ Streaming Output
- Real-time token streaming with a `🤔` thinking indicator
- See the agent reason step-by-step as it works

### 🔄 Automatic Recovery
- When a tool call fails, the agent automatically tries an alternative approach
- Graceful degradation keeps tasks moving forward

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | |
| [Ollama](https://ollama.com/download) | Latest | Must be running locally |
| `qwen3:8b` model | — | Pull command below |
| `ollama` Python package | Latest | `pip install ollama` |

---

## 🚀 Installation

**1. Install Ollama**

Download and install from [https://ollama.com/download](https://ollama.com/download), then start the Ollama service.

**2. Pull the model**

```bash
ollama pull qwen3:8b
```

**3. Clone this repository**

```bash
git clone https://github.com/<your-username>/LocalAgent.git
cd LocalAgent
```

**4. Install Python dependencies**

```bash
pip install ollama
```

> No heavy frameworks required. LocalAgent is intentionally lightweight.

---

## ⚡ Quick Start

```bash
# Start a new session (operates on the LocalAgent directory itself)
python main.py

# Point at a specific project — the recommended way to use LocalAgent
python main.py --workdir /path/to/your-project

# Windows
python main.py --workdir C:\projects\MyApp
```

The startup banner confirms the working directory and session:

```
Local Coding Agent
📂 工作目錄：C:\projects\MyApp
📌 Session ID：a1b2c3d4
   （使用 --resume a1b2c3d4 繼續此 Session）
🧪 Auto Test   ⚡ Streaming
輸入 /bye 結束，/rename <名稱> 重新命名 Session。

You >
```

---

## 📁 Recommended: Install Once, Use Anywhere

Install LocalAgent in a permanent location and use `--workdir` to point it at any project:

```bash
# Install once
git clone https://github.com/<your-username>/LocalAgent.git ~/tools/LocalAgent

# Use on any project
python ~/tools/LocalAgent/main.py --workdir ~/projects/my-app
python ~/tools/LocalAgent/main.py --workdir ~/projects/another-project
```

Resume a session — the workdir is restored automatically:

```bash
python main.py --resume a1b2c3d4
# → 📂 工作目錄：C:\projects\MyApp（從 Session 自動還原）
```

---

## 🖥️ CLI Reference

```
python main.py [OPTIONS]
```

| Option | Description |
|---|---|
| *(no options)* | Start a new session in the LocalAgent directory |
| `--workdir <PATH>` | **Point the agent at a specific project directory (always starts a new session)** |
| `--resume <SESSION_ID>` | Resume a previous session — workdir is restored automatically |
| `--list-sessions` | List all saved sessions (name, workdir, timestamp, message count) |
| `--no-auto-test` | Disable automatic `pytest` after code changes |
| `--no-stream` | Disable streaming output (print full response at once) |

### In-session commands

| Command | Description |
|---|---|
| `/rename <name>` | Rename the current session |
| `/bye` | Save and exit |

---

## 🏗️ Architecture

```
main.py
└── AgentRuntime  (agent/runtime.py)
    ├── RequirementParser     — Parses task into verifiable requirements (via LLM)
    ├── SpecificationValidator — Validates parsed spec before entering agent loop
    ├── Agent Loop
    │   ├── ToolRunner        — Dispatches file / git / shell tools
    │   └── PermissionManager — CLI confirmation + diff preview for sensitive actions
    ├── TestRunner            — Runs pytest and feeds failures back to agent
    ├── RecoveryManager       — Tries alternative approaches on tool failure
    ├── RequirementVerifier   — Glob-based verification against actual file system
    └── SessionManager        — Saves / loads sessions (with name + workdir binding)
```

The core loop:

```
User Task
  → Parse Requirements (LLM)
  → Validate Specification
  → [Think → Tool Call → Observe] × N
  → Verify Requirements (file system)
  → Report Results
  → Persist Session (name + workdir + messages)
```

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork the repository and create a feature branch
2. Make your changes with clear, focused commits
3. Run `ruff check .` and `pytest` to verify your changes (344 tests)
4. Open a Pull Request with a description of what you changed and why

Please keep PRs focused. For major changes, open an issue first to discuss your approach.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built for developers who value <strong>privacy</strong>, <strong>freedom</strong>, and <strong>edge computing</strong>.<br/>
  No cloud required. No subscription needed. Just your machine and an open model.
</p>
