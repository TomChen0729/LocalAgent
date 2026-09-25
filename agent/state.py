from datetime import datetime


def create_task_state(
    user_input=None,
    status="idle",
):
    """
    建立新的 Task State。

    Task State 負責保存目前 Agent Task
    的執行狀態。

    注意：
    這個模組只負責 State 的建立與更新，
    不負責 Agent Decision、Tool Execution
    或 Verification。
    """

    return {
        "status": status,
        "user_input": user_input,
        "started_at": None,
        "finished_at": None,
        # ------------------------------------------------
        # Tool State
        # ------------------------------------------------
        "tool_calls": 0,
        "last_tool": None,
        "last_result": None,
        # ------------------------------------------------
        # Phase 4.6
        # Tool Result Verification
        # ------------------------------------------------
        "verification_required": False,
        "verification_status": None,
        "verification_tool": None,
        "verification_result": None,
        # ------------------------------------------------
        # Phase 4.7
        # Requirement Verification
        # ------------------------------------------------
        "requirement_status": None,
        "requirement_result": None,
        # ------------------------------------------------
        # Phase 4.8
        # Structured Requirements
        # ------------------------------------------------
        "requirements": [],
        "requirement_verification": None,
        # ------------------------------------------------
        # Phase 8.2
        # Task Specification Parser
        # ------------------------------------------------
        "task_specification": None,
        "parser_status": None,
        "parser_error": None,
        # ------------------------------------------------
        # Phase 8.6
        # Specification Validation
        # ------------------------------------------------
        "specification_validation_status": None,
        "specification_validation_result": None,
        # ------------------------------------------------
        # Phase 8.4
        # Requirement Failure / Progress
        # ------------------------------------------------
        "requirement_failure_count": 0,
        "requirement_progress_since_failure": False,
        "last_requirement_signature": None,
        # ------------------------------------------------
        # Phase 8.5
        # Output Verification
        # ------------------------------------------------
        "output_verification_status": None,
        "output_verification_result": None,
        "output_verification_failure_count": 0,
        # ------------------------------------------------
        # Phase 9.3 Recovery
        # ------------------------------------------------
        "recovery_attempt_count": 0,
        "last_recovery_tool": None,
        "last_recovery_result": None,
        "last_recovery_category": None,
    }


def start_task(
    state,
    user_input,
):
    """
    將 Task State 初始化為新的 running Task。

    Parameters
    ----------
    state : dict
        Runtime 目前使用的 Task State。

    user_input : str
        使用者輸入。

    Returns
    -------
    dict
        更新後的 Task State。
    """

    state.clear()

    state.update(
        create_task_state(
            user_input=user_input,
            status="running",
        )
    )

    state["started_at"] = datetime.now().isoformat()

    return state


def finish_task(
    state,
    status,
):
    """
    結束目前 Task。

    status:
        completed
        failed
        stopped
    """

    state["status"] = status
    state["finished_at"] = datetime.now().isoformat()

    return state


def update_task_state(
    state,
    tool_call_count,
    tool_name,
    tool_result,
):
    """
    Tool 執行完成後更新 Task State。
    """

    state["tool_calls"] = tool_call_count
    state["last_tool"] = tool_name
    state["last_result"] = tool_result

    return state
