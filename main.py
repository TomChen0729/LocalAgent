from agent.runtime import AgentRuntime


def main():
    agent = AgentRuntime()

    print("Local Coding Agent")
    print("輸入 /bye 結束程式。")
    print()

    while True:
        user_input = input("You > ")

        if user_input.strip() == "/bye":
            print("Bye!")
            break

        if not user_input.strip():
            continue

        final_answer = agent.run(user_input)

        print()
        print("Qwen > " + final_answer)
        print()


if __name__ == "__main__":
    main()
