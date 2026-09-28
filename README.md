# 🤖 LocalAgent

> **A fully local AI Coding Agent — no cloud, no subscriptions, no data leaks.**

LocalAgent is an open-source AI coding assistant that runs entirely on your machine using [Ollama](https://ollama.com) and small open-weight models (default: `qwen3:8b`). It handles real coding tasks — reading files, writing code, running tests, making Git commits — all without sending a single byte to OpenAI or Anthropic.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black?logo=ollama)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Model](https://img.shields.io/badge/Model-qwen3%3A8b-orange)](https://ollama.com/library/qwen3)

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
| **Custom permissions** | ✅ Fine-grained CLI confirmation | ⚠️ Limited |
| **Requirement verification** | ✅ Glob-based file system check | ❌ No |

---

## ✨ Features

### 🗂️ Complete File Toolset
- Read, write, edit, delete, search, and list files
- Glob-pattern search across the entire project tree

### 🔧 Full Git CLI Integration
- `status`, `diff`, `log`, `commit`, `push`, `pull`, `branch`, `checkout`, and more
- Commit messages generated automatically from context

### 🛡️ Security Permission System
- Six permission levels: `read` / `write` / `edit` / `commit` / `execute` / `delete`
- Every sensitive action requires explicit CLI confirmation before execution

### ✅ Command Execution Whitelist
- 30+ pre-approved programs: `pip`, `ruff`, `mypy`, `pytest`, `npm`, `cargo`, and more
- Unknown commands are blocked by default — no accidental shell injection

### 🔁 Auto Test Loop
- Automatically runs `pytest` after writing or editing Python files
- On failure, the agent reads the error output and self-corrects — up to N retries

### 📋 Requirement Verification
- Parses task requirements and verifies completion against the **actual file system** (Glob-based)
- Reports which requirements are met before finishing a task

### 💾 Session Persistence
- Every conversation is saved and can be resumed with `--resume <SESSION_ID>`
- List all past sessions with `--list-sessions`

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
# Start a new session
python main.py

# Then type your task, for example:
# > Write a Python script that reads a CSV file and outputs summary statistics
```

The agent will ask for your confirmation before writing files, executing commands, or making Git commits.

---

## 📁 Recommended: Use `--workdir`

The cleanest way to use LocalAgent is to install it **once** in a fixed location and point it at any project with `--workdir`:

```bash
# Install LocalAgent somewhere permanent
git clone https://github.com/<your-username>/LocalAgent.git ~/tools/LocalAgent

# Then use it from anywhere — the agent works on YOUR project, not on LocalAgent itself
python ~/tools/LocalAgent/main.py --workdir /path/to/my-project

# Windows example
python C:\tools\LocalAgent\main.py --workdir C:\projects\MyApp
```

The startup banner confirms which directory the agent is operating on:

```
Local Coding Agent
📂 Working directory: C:\projects\MyApp
📌 Session ID：a1b2c3d4
🧪 Auto Test   ⚡ Streaming
```

This keeps LocalAgent completely separate from your projects — no mixing of tool code and project code.

---

## 🖥️ CLI Reference

```
python main.py [OPTIONS]
```

| Option | Description |
|---|---|
| *(no options)* | Start a new interactive session (works on the current directory) |
| `--workdir <PATH>` | **Point the agent at a specific project directory** |
| `--resume <SESSION_ID>` | Resume a previous session by ID |
| `--list-sessions` | List all saved sessions with timestamps |
| `--no-auto-test` | Disable automatic `pytest` after code changes |
| `--no-stream` | Disable streaming output (print full response at once) |

---

## 🏗️ Architecture

```
main.py
└── AgentRuntime  (agent/runtime.py)
    ├── RequirementParser     — Parses task into verifiable requirements
    ├── Agent Loop
    │   ├── ToolRunner        — Dispatches file / git / shell tools
    │   └── PermissionManager — CLI confirmation for sensitive actions
    ├── TestRunner            — Runs pytest and feeds failures back to agent
    ├── RequirementVerifier   — Glob-based verification against file system
    └── SessionManager        — Saves / loads conversation sessions
```

The core loop is simple:

```
User Task → Parse Requirements → [Think → Act → Observe] × N
         → Verify Requirements → Report Results → Persist Session
```

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork the repository and create a feature branch
2. Make your changes with clear, focused commits
3. Run `ruff check .` and `pytest` to verify your changes
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
