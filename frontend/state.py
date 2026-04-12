"""Frontend session state helpers."""
import uuid
import streamlit as st


def init_session_state() -> None:
    if "threads" not in st.session_state:
        st.session_state.threads = {}  # thread_id → {name, history, last_result}

    if "active_thread_id" not in st.session_state:
        _create_new_thread()

    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0


def _create_new_thread(name: str | None = None) -> str:
    thread_id = str(uuid.uuid4())
    st.session_state.threads[thread_id] = {
        "name": name or f"Thread {len(st.session_state.threads) + 1}",
        "history": [],
        "last_result": None,
    }
    st.session_state.active_thread_id = thread_id
    return thread_id


def create_new_thread(name: str | None = None) -> str:
    return _create_new_thread(name)


def get_active_thread() -> dict:
    tid = st.session_state.active_thread_id
    return st.session_state.threads[tid]


def add_message(role: str, content: str) -> None:
    thread = get_active_thread()
    thread["history"].append({"role": role, "content": content})


def set_last_result(result: dict) -> None:
    thread = get_active_thread()
    thread["last_result"] = result
    st.session_state.total_tokens += result.get("token_usage", 0)
