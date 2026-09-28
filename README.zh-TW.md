# 🤖 LocalAgent

> **完全本地執行的 AI Coding Agent — 不上雲端、不付月費、不洩漏程式碼。**

LocalAgent 是一個開源的 AI 程式開發助理，完全運行在你自己的機器上，使用 [Ollama](https://ollama.com) 搭配小型開源模型（預設：`qwen3:8b`）。它能處理真實的開發任務——讀取檔案、撰寫程式、執行測試、Git Commit——完全不把任何一個 byte 送到 OpenAI 或 Anthropic。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black?logo=ollama)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Model](https://img.shields.io/badge/Model-qwen3%3A8b-orange)](https://ollama.com/library/qwen3)

繁體中文 | [English](README.md)

---

## 為什麼選擇 LocalAgent？

你已經有一台電腦了，為什麼還要每個月付 \$20 給雲端 Coding Agent？

| 功能 | LocalAgent | Claude Code |
|---|---|---|
| **費用** | ✅ 永久免費 | ❌ \$20+/月 |
| **隱私** | ✅ 100% 本地，不傳送任何資料 | ❌ 程式碼送到 Anthropic |
| **需要網路** | ✅ 不需要 | ❌ 需要 |
| **模型彈性** | ✅ 任何 Ollama 模型 | ❌ 只能用 Claude |
| **邊緣運算 / 離網環境** | ✅ 支援 | ❌ 不支援 |
| **開源** | ✅ MIT 授權 | ❌ 閉源商業 |
| **修改前 Diff 預覽** | ✅ 每次改動前顯示 `+`/`-` | ❌ 無 |
| **需求驗證** | ✅ 基於實際檔案系統的 Glob 驗證 | ❌ 無 |

---

## ✨ 功能特色

### 🗂️ 完整的檔案操作工具
- 讀取、寫入、編輯、刪除、搜尋、列出檔案
- 支援遞迴目錄列表——一次呼叫看到完整專案結構
- Glob 模式全專案搜尋

### 🔧 完整的 Git CLI 整合
- 支援 `status`、`diff`、`log`、`commit`、`push`、`pull`、`branch`、`checkout`、`stash` 等
- 根據上下文自動生成 commit message
- 細緻的權限分級：`git add`（staging）與 `git commit`、`git push` 分開確認

### 🛡️ 修改前 Diff 預覽
- `edit_file`：執行前顯示完整的 unified diff（逐行 `+`/`-`）
- `write_file`：顯示帶行號的新檔案內容預覽
- 你在按下確認前就能看到每一行會有什麼變化

### 🔐 安全權限系統
- 六個權限等級：`read` / `write` / `edit` / `commit` / `execute` / `delete`
- 每個敏感操作執行前都需要明確的 CLI 確認
- `git push` 被歸類為最高風險等級（`execute`）

### ✅ 命令執行白名單
- 30+ 個預先核准的程式：`pip`、`ruff`、`mypy`、`pytest`、`npm`、`cargo` 等
- 未知命令預設封鎖——不會有意外的 shell 注入
- 命令永遠在正確的專案目錄執行（跟隨 `--workdir` 設定）

### 🔁 Auto Test Loop
- 寫完或修改 Python 檔案後自動執行 `pytest`
- 測試失敗時自動讀取錯誤輸出並自我修正——最多重試 N 次

### 📋 需求驗證
- 解析任務需求並對照**實際檔案系統**驗證完成度
- 副檔名感知：驗證 `README` 時也會嘗試 `README.md`、`README.txt` 等
- 任務完成前回報哪些需求已達成、哪些未達成

### 💾 Session 持久化 + 命名
- 每次對話自動儲存，並根據任務內容自動生成人類可讀的名稱
- `--resume <SESSION_ID>` 繼續上次的對話——**包含工作目錄也會自動還原**
- 在對話中輸入 `/rename <名稱>` 隨時重新命名 Session
- `--list-sessions` 顯示名稱、工作目錄、時間戳記、訊息數量

### 📂 多專案支援（`--workdir`）
- 用 `--workdir` 把 LocalAgent 指向任何專案目錄，不需要搬移安裝位置
- Resume Session 時自動還原上次的工作目錄，不需要重新指定

### ⚡ 串流即時輸出
- 即時 token 串流，附帶 `🤔` 思考指示符
- 逐步看到 Agent 的推理過程

### 🔄 自動 Recovery
- Tool 呼叫失敗時自動嘗試替代方案
- 優雅降級，讓任務持續推進

---

## 前置需求

| 需求 | 版本 | 說明 |
|---|---|---|
| Python | 3.10+ | |
| [Ollama](https://ollama.com/download) | 最新版 | 須在本機運行 |
| `qwen3:8b` 模型 | — | 下方有 pull 指令 |
| `ollama` Python 套件 | 最新版 | `pip install ollama` |

---

## 🚀 安裝步驟

**1. 安裝 Ollama**

從 [https://ollama.com/download](https://ollama.com/download) 下載安裝，然後啟動 Ollama 服務。

**2. 下載模型**

```bash
ollama pull qwen3:8b
```

**3. Clone 此儲存庫**

```bash
git clone https://github.com/<your-username>/LocalAgent.git
cd LocalAgent
```

**4. 安裝 Python 依賴**

```bash
pip install ollama
```

> 不需要任何重量級框架。LocalAgent 刻意保持輕量。

---

## ⚡ 快速開始

```bash
# 啟動新 Session（在 LocalAgent 自身目錄操作）
python main.py

# 指向特定專案——推薦的使用方式
python main.py --workdir /path/to/your-project

# Windows 範例
python main.py --workdir C:\projects\MyApp
```

啟動時的 banner 會確認工作目錄和 Session 資訊：

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

## 📁 推薦做法：安裝一次，到處使用

把 LocalAgent 安裝在固定位置，用 `--workdir` 指向任何專案：

```bash
# 安裝一次
git clone https://github.com/<your-username>/LocalAgent.git ~/tools/LocalAgent

# 對任何專案使用
python ~/tools/LocalAgent/main.py --workdir ~/projects/my-app
python ~/tools/LocalAgent/main.py --workdir ~/projects/another-project
```

Resume Session 時工作目錄自動還原：

```bash
python main.py --resume a1b2c3d4
# → 📂 工作目錄：C:\projects\MyApp（從 Session 自動還原）
```

---

## 🖥️ CLI 參數說明

```
python main.py [選項]
```

| 選項 | 說明 |
|---|---|
| *（無選項）* | 在 LocalAgent 目錄啟動新 Session |
| `--workdir <PATH>` | **指定 Agent 操作的專案目錄（永遠開新 Session）** |
| `--resume <SESSION_ID>` | 繼續指定的 Session——工作目錄自動還原 |
| `--list-sessions` | 列出所有 Session（名稱、工作目錄、時間、訊息數） |
| `--no-auto-test` | 停用程式碼變更後的自動 `pytest` |
| `--no-stream` | 停用串流輸出（一次印出完整回答） |

### Session 內指令

| 指令 | 說明 |
|---|---|
| `/rename <名稱>` | 重新命名目前的 Session |
| `/bye` | 儲存並離開 |

---

## 🏗️ 架構說明

```
main.py
└── AgentRuntime  (agent/runtime.py)
    ├── RequirementParser     — 用 LLM 將任務解析成可驗證的需求
    ├── SpecificationValidator — 進入 Agent Loop 前驗證 spec 的合法性
    ├── Agent Loop
    │   ├── ToolRunner        — 分派檔案 / Git / Shell 工具
    │   └── PermissionManager — CLI 確認 + Diff 預覽（敏感操作）
    ├── TestRunner            — 執行 pytest 並將失敗回饋給 Agent
    ├── RecoveryManager       — Tool 失敗時自動嘗試替代方案
    ├── RequirementVerifier   — 對照實際檔案系統進行 Glob 驗證
    └── SessionManager        — 儲存 / 載入 Session（含名稱 + 工作目錄綁定）
```

核心流程：

```
使用者任務
  → 解析需求（LLM）
  → 驗證 Specification
  → [思考 → 呼叫 Tool → 觀察結果] × N
  → 驗證需求（實際檔案系統）
  → 回報結果
  → 持久化 Session（名稱 + 工作目錄 + 訊息）
```

---

## 🤝 貢獻指南

歡迎任何形式的貢獻！開始之前：

1. Fork 此儲存庫並建立 feature branch
2. 以清楚、聚焦的 commit 進行修改
3. 執行 `ruff check .` 和 `pytest` 確認所有測試通過（344 個測試）
4. 提交 Pull Request，說明你改了什麼以及為什麼

請保持 PR 的範圍聚焦。重大變更請先開 issue 討論方向。

---

## 📄 授權

本專案採用 **MIT 授權條款**——詳見 [LICENSE](LICENSE) 檔案。

---

<p align="center">
  為重視<strong>隱私</strong>、<strong>自由</strong>和<strong>邊緣運算</strong>的開發者而生。<br/>
  不需要雲端。不需要訂閱。只需要你的機器和一個開源模型。
</p>
