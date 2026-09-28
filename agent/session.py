"""
Session Persistence for LocalAgent.

將對話歷史儲存到磁碟，讓使用者可以在重啟後繼續上次的任務。

Session 存放路徑：
    ~/.localagent/sessions/<session_id>.json
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class SessionManager:
    """
    LocalAgent Session 持久化管理器。

    功能：
    - 每輪對話後自動儲存 messages 到磁碟
    - 支援 --resume <session_id> 繼續上次任務
    - Context window 管理：resume 時只載入最後 N 條訊息
    - 原子寫入（tmpfile + replace）

    使用方式：

        # 新 Session
        sm = SessionManager()
        sm.save(messages)
        print(sm.session_id)   # 顯示 session id 給使用者

        # 繼續 Session
        sm = SessionManager(session_id="abc12345")
        messages = sm.load_messages()
    """

    DEFAULT_DIR = Path.home() / ".localagent" / "sessions"

    # Resume 時最多載入幾條訊息（context window 管理）
    MAX_MESSAGES_ON_RESUME = 50

    def __init__(
        self,
        session_id: Optional[str] = None,
        sessions_dir: Optional[Path] = None,
    ):
        """
        Parameters
        ----------
        session_id :
            指定 Session ID。
            None 則自動生成新的 8 字元 ID。

        sessions_dir :
            Session 檔案存放目錄。
            None 則使用預設路徑 ~/.localagent/sessions/。
        """
        self.sessions_dir = Path(sessions_dir or self.DEFAULT_DIR)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        if session_id:
            self.session_id = session_id
        else:
            self.session_id = uuid.uuid4().hex[:8]

        # Session 名稱（記憶體中，下次 save() 時持久化到磁碟）
        self._name: Optional[str] = None

    # ----------------------------------------------------------
    # Path
    # ----------------------------------------------------------

    @property
    def session_file(self) -> Path:
        """Session 檔案的完整路徑。"""
        return self.sessions_dir / f"{self.session_id}.json"

    @property
    def exists(self) -> bool:
        """Session 檔案是否存在。"""
        return self.session_file.exists()

    # ----------------------------------------------------------
    # Name
    # ----------------------------------------------------------

    def set_name(self, name: str) -> None:
        """
        設定 Session 名稱。

        名稱只存在記憶體中，下次 save() 時才寫入磁碟。
        """
        self._name = name.strip()

    def get_name(self) -> Optional[str]:
        """
        取得 Session 名稱。

        優先回傳記憶體中的名稱；
        若無，則從磁碟讀取。
        """
        if self._name:
            return self._name
        data = self._load_raw()
        return (data or {}).get("name")

    # ----------------------------------------------------------
    # Save
    # ----------------------------------------------------------

    def save(
        self,
        messages: list,
        extra: Optional[dict] = None,
    ) -> bool:
        """
        將目前對話儲存到磁碟（原子寫入）。

        Parameters
        ----------
        messages :
            目前的 LLM messages list。
        extra :
            額外要儲存的 metadata（例如 model、task_count 等）。

        Returns
        -------
        bool : 儲存是否成功。
        """
        now = datetime.now().isoformat()

        # 讀取現有 created_at（若有）
        existing = self._load_raw()
        created_at = (existing or {}).get("created_at", now)

        # 序列化 messages（Ollama Message 物件 → dict）
        serialized = self._serialize_messages(messages)

        # 決定 name：優先用記憶體中的 _name，其次保留磁碟既有的 name
        name = self._name or (existing or {}).get("name")

        data = {
            "session_id": self.session_id,
            "created_at": created_at,
            "updated_at": now,
            "message_count": len(serialized),
            "messages": serialized,
            **(extra or {}),
        }

        if name:
            data["name"] = name

        tmp = self.session_file.with_suffix(".tmp")

        try:
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.session_file)
            return True

        except Exception as exc:
            # 印出錯誤方便 debug，不再靜默吞掉
            print(f"⚠️ Session 儲存失敗：{exc}")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            return False

    @staticmethod
    def _serialize_messages(messages: list) -> list:
        """
        將 messages list 中的 Ollama Message 物件轉成 dict。

        Ollama 的 Message 物件不可直接 JSON 序列化，
        必須呼叫 model_dump() 轉換。
        同時清除不需要的欄位（images、thinking 等），
        只保留 role、content、tool_calls。
        """
        result = []

        for msg in messages:
            if isinstance(msg, dict):
                result.append(msg)
            elif hasattr(msg, "model_dump"):
                # Ollama Message (Pydantic model)
                d = msg.model_dump()
                # 只保留有值的欄位，減少磁碟佔用
                cleaned = {"role": d.get("role", "assistant")}
                if d.get("content"):
                    cleaned["content"] = d["content"]
                if d.get("tool_calls"):
                    # tool_calls 裡可能也有 Pydantic 物件
                    cleaned["tool_calls"] = d["tool_calls"]
                result.append(cleaned)
            else:
                # fallback：嘗試 __dict__
                result.append(
                    getattr(msg, "__dict__", {"content": str(msg)})
                )

        return result

    # ----------------------------------------------------------
    # Load
    # ----------------------------------------------------------

    def _load_raw(self) -> Optional[dict]:
        """讀取原始 Session JSON。"""
        if not self.session_file.exists():
            return None

        try:
            return json.loads(
                self.session_file.read_text(encoding="utf-8")
            )
        except Exception:
            return None

    def load_messages(self) -> list:
        """
        載入 Session 的 messages，並套用 context window 管理。

        只載入最後 MAX_MESSAGES_ON_RESUME 條訊息，
        避免超出 LLM 的 context window。
        同時從磁碟還原 name 到記憶體。

        Returns
        -------
        list : messages list，若 Session 不存在則回傳 []。
        """
        data = self._load_raw()
        if not data:
            return []

        # 還原 name 到記憶體（若磁碟有記錄）
        if data.get("name") and not self._name:
            self._name = data["name"]

        messages = data.get("messages", [])

        if len(messages) > self.MAX_MESSAGES_ON_RESUME:
            # 保留 system prompt（第一條）+ 最後 N 條對話
            system_messages = [m for m in messages if m.get("role") == "system"]
            non_system = [m for m in messages if m.get("role") != "system"]
            non_system = non_system[-(self.MAX_MESSAGES_ON_RESUME - 1):]
            messages = system_messages[:1] + non_system

        return messages

    def get_info(self) -> Optional[dict]:
        """取得 Session 的摘要資訊。"""
        data = self._load_raw()
        if not data:
            return None

        return {
            "session_id": data.get("session_id"),
            "name": data.get("name"),
            "workdir": data.get("workdir"),   # 上次使用的工作目錄（絕對路徑）
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "message_count": data.get("message_count", 0),
        }

    # ----------------------------------------------------------
    # List
    # ----------------------------------------------------------

    def list_sessions(self) -> list:
        """
        列出所有 Session，依最後更新時間倒序排列。
        """
        sessions = []

        for f in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                sessions.append({
                    "session_id": data.get("session_id", f.stem),
                    "name": data.get("name", ""),
                    "workdir": data.get("workdir", ""),
                    "created_at": data.get("created_at", "?"),
                    "updated_at": data.get("updated_at", "?"),
                    "message_count": data.get("message_count", 0),
                })
            except Exception:
                continue

        return sorted(
            sessions,
            key=lambda x: x["updated_at"],
            reverse=True,
        )
