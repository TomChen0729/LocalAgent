import argparse

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
        help="繼續指定的 Session（例如 --resume ab12cd34）。",
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
            print(f"{'Session ID':<12} {'Updated':<25} {'Messages':>8}")
            print("-" * 50)
            for s in sessions:
                print(
                    f"{s['session_id']:<12} "
                    f"{s['updated_at'][:19]:<25} "
                    f"{s['message_count']:>8}"
                )
        return

    # ----------------------------------------------------------
    # Session Manager
    # ----------------------------------------------------------

    session_manager = SessionManager(session_id=args.resume)
    is_resume = bool(args.resume) and session_manager.exists

    # ----------------------------------------------------------
    # Agent
    # ----------------------------------------------------------

    use_stream = not args.no_stream

    agent = AgentRuntime(
        session_manager=session_manager,
        auto_test=not args.no_auto_test,
        stream=use_stream,
    )

    # ----------------------------------------------------------
    # Startup Banner
    # ----------------------------------------------------------

    print("Local Coding Agent")

    if is_resume:
        info = session_manager.get_info()
        print(f"✅ 已載入 Session：{session_manager.session_id}")
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

    print("輸入 /bye 結束程式。")
    print()

    # ----------------------------------------------------------
    # Main Loop
    # ----------------------------------------------------------

    while True:
        user_input = input("You > ")

        if user_input.strip() == "/bye":
            # 離開前存檔
            session_manager.save(
                agent.messages,
                extra={"model": agent.model},
            )
            print(f"Bye！Session ID：{session_manager.session_id}")
            break

        if not user_input.strip():
            continue

        final_answer = agent.run(user_input)

        # 每次 run 結束後都存檔（不管成功或失敗）
        # runtime 內部的 save 只在 Final Answer PASS 時觸發，
        # 這裡補上其他路徑（空答案上限、tool 上限等）。
        session_manager.save(
            agent.messages,
            extra={"model": agent.model},
        )

        # Streaming 模式：答案已在 run() 內部即時印出（含 "Qwen > " 前綴）。
        # Non-streaming 模式：由 main.py 負責印出完整答案。
        if agent._last_response_was_streamed:
            print()  # 串流結束後加一個空行
        else:
            print()
            print("Qwen > " + final_answer)
            print()


if __name__ == "__main__":
    main()
