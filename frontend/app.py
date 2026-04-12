"""
Streamlit frontend for the AI Research Agent.
Communicates exclusively with the API Gateway — no direct service calls.

Run with: streamlit run app.py
"""
import streamlit as st

from config import API_GATEWAY_URL
from api_client import GatewayClient
from state import init_session_state, create_new_thread, get_active_thread, add_message, set_last_result
from ui import apply_global_css, render_sidebar, render_chat_history, render_result_metadata, render_health_panel

st.set_page_config(
    page_title="AI Research Agent",
    page_icon="🔬",
    layout="wide",
)

apply_global_css()
init_session_state()

client = GatewayClient(base_url=API_GATEWAY_URL)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _on_new_thread():
    name = f"Thread {len(st.session_state.threads) + 1}"
    create_new_thread(name)
    st.rerun()


def _on_select_thread(tid: str):
    st.session_state.active_thread_id = tid
    st.rerun()


render_sidebar(
    threads=st.session_state.threads,
    active_id=st.session_state.active_thread_id,
    on_new_thread=_on_new_thread,
    on_select_thread=_on_select_thread,
)


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

col_main, col_meta = st.columns([3, 1])

with col_main:
    st.header("Developer Research Assistant")

    thread = get_active_thread()
    render_chat_history(thread["history"])

    # Chat input
    user_query = st.chat_input("Ask a technical question…")

    if user_query:
        add_message("user", user_query)

        with st.spinner("Researching…"):
            try:
                result = client.run_research_sync(
                    query=user_query,
                    thread_id=st.session_state.active_thread_id,
                    history=thread["history"][:-1],  # exclude the message we just added
                )

                status = result.get("status", "failed")

                if status == "clarifying":
                    reply = (
                        f"**Clarification needed:** {result.get('clarification_question', '')}"
                    )
                elif status == "completed":
                    reply = result.get("final_report", "No report generated.")
                else:
                    reply = f"Research failed. Status: {status}"

                add_message("assistant", reply)
                set_last_result(result)

            except Exception as exc:
                err_msg = f"**Error contacting API Gateway:** {exc}"
                add_message("assistant", err_msg)

        st.rerun()

    # Show last result metadata below conversation
    render_result_metadata(thread.get("last_result"))


with col_meta:
    st.subheader("Service Health")

    if st.button("Check health", use_container_width=True):
        health = client.health_sync()
        render_health_panel(health)
    else:
        st.caption("Click to check all microservice health.")

    st.divider()
    st.metric("Session tokens", st.session_state.get("total_tokens", 0))
    st.caption(f"Gateway: `{API_GATEWAY_URL}`")
