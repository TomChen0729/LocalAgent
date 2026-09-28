import argparse
import sys
from pathlib import Path

from agent.runtime import AgentRuntime
from agent.session import SessionManager


def main():

    # ----------------------------------------------------------
    # CLI Arguments
    # ----------------------------------------------------------

    parser = argparse.ArgumentParser(
        description="LocalAgent - Local AI Coding Agent",
    )

    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="繼續指定的 Session（自動還原上次的工作目錄）。",
    )

    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="列出所有可繼續的 Session。",
    )

    parser.add_argument(
        "--no-auto-test",
        action="store_true",
        help="停用 Auto Test Loop（寫完程式後不自動跑測試）。",
    )

    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="停用 Streaming 輸出（一次印出全部回答）。",
    )

    parser.add_argument(
        "--workdir",
        metavar="PATH",
        help="指定 Agent 操作的專案目錄（指定後永遠開新 Session）。",
    )

    args = parser.parse_args()

    # ----------------------------------------------------------
    # --list-sessions
    # ----------------------------------------------------------

    if args.list_sessions:
        sm = SessionManager()
        sessions = sm.list_sessions()

        if not sessions:
            print("尚無任何 Session 記錄。")
        else:
            # 動態計算欄寬
            max_name = max((len(s.get("name") or "（未命名）") for s in sessions), default=8)
            name_col = max(max_name, 8)

            # workdir 欄：只顯示最後兩層路徑（避免太長）
            def _short_workdir(wd: str) -> str:
                if not wd:
                    return "（預設）"
                p = Path(wd)
                parts = p.parts
                return str(Path(*parts[-2:])) if len(parts) >= 2 else wd

            max_wd = max((len(_short_workdir(s.get("workdir", ""))) for s in sessions), default=6)
            wd_col = max(max_wd, 6)

            header = (
                f"{'Session ID':<12} "
                f"{'名稱':<{name_col}} "
                f"{'工作目錄':<{wd_col}} "
                f"{'Updated':<20} "
                f"{'Messages':>8}"
            )
            print(header)
            print("-" * len(header))
            for s in sessions:
                name_display = s.get("name") or "（未命名）"
                wd_display = _short_workdir(s.get("workdir", ""))
                print(
                    f"{s['session_id']:<12} "
                    f"{name_display:<{name_col}} "
                    f"{wd_display:<{wd_col}} "
                    f"{s['updated_at'][:19]:<20} "
                    f"{s['message_count']:>8}"
                )
        return

    # ----------------------------------------------------------
    # 決定 workdir 與 Session 的關係
    #
    # 規則：
    #   --resume                → 新 Session
    #   --workdir               → 新 Session（忽略 --resume）
    #   --resume + --workdir    → --workdir 優先，但沿用指定 Session
    #   --resume（無 workdir）  → 從 Session metadata 還原 workdir
    # ----------------------------------------------------------

    user_specified_workdir = args.workdir is not None

    # --workdir 指定時永遠開新 Session（除非同時指定 --resume）
    if user_specified_workdir and not args.resume:
        resume_id = None
    else:
        resume_id = args.resume

    # ----------------------------------------------------------
    # Workdir 解析
    # ----------------------------------------------------------

    if user_specified_workdir:
        workdir = Path(args.workdir).resolve()
        if not workdir.exists():
            print(f"❌ 錯誤：--workdir 路徑不存在：{workdir}")
            sys.exit(1)
        if not workdir.is_dir():
            print(f"❌ 錯誤：--workdir 必須是目錄：{workdir}")
            sys.exit(1)
        workdir_source = "cli"   # 來源：命令列
    else:
        workdir = None
        workdir_source = "default"

    # ----------------------------------------------------------
    # Session Manager
    # ----------------------------------------------------------

    session_manager = SessionManager(session_id=resume_id)
    is_resume = bool(resume_id) and session_manager.exists

    # ----------------------------------------------------------
    # --resume 時，從 Session metadata 還原 workdir
    # ----------------------------------------------------------

    workdir_restored = False   # 是否是自動還原的（用於 banner 顯示）

    if is_resume and not user_specified_workdir:
        info = session_manager.get_info()
        saved_workdir = (info or {}).get("workdir")

        if saved_workdir:
            candidate = Path(saved_workdir)
            if candidate.exists() and candidate.is_dir():
                workdir = candidate
                workdir_source = "session"
                workdir_restored = True
            else:
                print(f"⚠️  Session 的工作目錄已不存在：{saved_workdir}")
                print("   將使用 LocalAgent 預設目錄繼續。")

    # ----------------------------------------------------------
    # Agent 初始化
    # ----------------------------------------------------------

    use_stream = not args.no_stream

    agent = AgentRuntime(
        project_path=workdir,
        session_manager=session_manager,
        auto_test=not args.no_auto_test,
        stream=use_stream,
    )

    # ----------------------------------------------------------
    # Startup Banner
    # ----------------------------------------------------------

    print("Local Coding Agent")

    # 工作目錄顯示
    if workdir:
        if workdir_restored:
            print(f"📂 工作目錄：{workdir}（從 Session 自動還原）")
        else:
            print(f"📂 工作目錄：{workdir}")

    # Session 資訊
    if is_resume:
        info = session_manager.get_info()
        session_name = session_manager.get_name()
        name_display = f"「{session_name}」" if session_name else ""
        print(f"✅ 已載入 Session：{session_manager.session_id} {name_display}".strip())
        if info:
            print(f"   上次更新：{info['updated_at'][:19]}")
            print(f"   訊息數量：{info['message_count']}")
    else:
        print(f"📌 Session ID：{session_manager.session_id}")
        print(f"   （使用 --resume {session_manager.session_id} 繼續此 Session）")

    flags = []
    if not args.no_auto_test:
        flags.append("🧪 Auto Test")
    if use_stream:
        flags.append("⚡ Streaming")

    if flags:
        print("   ".join(flags))

    print("輸入 /bye 結束，/rename <名稱> 重新命名 Session。")
    print()

    # ----------------------------------------------------------
    # 儲存 workdir 到 Session 的 helper
    # ----------------------------------------------------------

    def _save():
        """儲存 Session，永遠包含 workdir。"""
        session_manager.save(
            agent.messages,
            extra={
                "model": agent.model,
                # 儲存絕對路徑，resume 時可以精確還原
                "workdir": str(agent.project_path),
            },
        )

    # ----------------------------------------------------------
    # Main Loop
    # ----------------------------------------------------------

    # 記錄是否已顯示過自動命名提示（每個 session 只顯示一次）
    _shown_auto_name = is_resume  # resume 時不再顯示（已有名稱）

    while True:
        user_input = input("You > ")
        stripped = user_input.strip()

        # ---- /bye ----
        if stripped == "/bye":
            _save()
            name = session_manager.get_name()
            name_display = f"「{name}」 " if name else ""
            print(f"Bye！Session {name_display}ID：{session_manager.session_id}")
            break

        # ---- /rename <name> ----
        if stripped.startswith("/rename "):
            new_name = stripped[8:].strip()
            if new_name:
                session_manager.set_name(new_name)
                _save()
                print(f"✅ Session 已重新命名為：「{new_name}」")
            else:
                print("用法：/rename <新名稱>")
                print("例如：/rename TaiwanStockScraper 分析")
            continue

        # ---- 空輸入 ----
        if not stripped:
            continue

        # ---- 正常對話 ----
        final_answer = agent.run(user_input)

        # 每次 run 結束後都存檔（含 workdir）
        _save()

        # 第一次 run 後，若已自動命名，印出名稱讓使用者知道
        if not _shown_auto_name and session_manager.get_name():
            name = session_manager.get_name()
            if len(agent.messages) <= 6:
                print(f"   💬 Session 已命名為：「{name}」")
                _shown_auto_name = True

        # Streaming 模式：答案已在 run() 內部即時印出。
        # Non-streaming 模式：由 main.py 負責印出。
        if agent._last_response_was_streamed:
            print()
        else:
            print()
            print("Qwen > " + final_answer)
            print()


if __name__ == "__main__":
    main()
