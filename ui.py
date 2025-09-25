import streamlit as st
from llm_wrapper import chat_query

st.set_page_config(page_title="📚 Research Helper", layout="wide")

st.title("📚 Research Helper (Chat Mode)")

# ── Session state init ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": "user"/"assistant", "content": str}

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    algorithm = st.selectbox(
        "Ranking Algorithm",
        ["Standard", "Super Smart", "Super Super Smart (Bayesian)"],
        index=1,
    )

# Map to internal flags
if algorithm == "Super Smart":
    algo_flag = "smart"
elif algorithm.startswith("Super Super"):
    algo_flag = "bayesian"
else:
    algo_flag = "standard"

# ── Display chat history ─────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ───────────────────────────────────────────────────────
if user_input := st.chat_input("Ask me about papers, citations, or concepts..."):
    # Record user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run query (LLM router decides scrape vs. answer)
    with st.chat_message("assistant"):
        with st.spinner("🔎 Thinking (solve captcha if popup appears)..."):
            try:
                reply = chat_query(
                    user_input,
                    algorithm=algo_flag,
                    history=st.session_state.messages,
                )
                if not reply.strip():
                    reply = (
                        "⚠️ No response was generated. "
                        "If a Google Scholar captcha appeared, please solve it in the popup browser. "
                        "The system will continue automatically once solved."
                    )
            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"

        st.markdown(reply)

    # Record assistant reply
    st.session_state.messages.append({"role": "assistant", "content": reply})
