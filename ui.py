import streamlit as st
from llm_wrapper import chat_query

st.set_page_config(page_title="📚 Research Helper", layout="wide")

st.title("📚 Research Helper (Chat Mode)")

# Initialize chat state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for algorithm choice
with st.sidebar:
    st.header("⚙️ Settings")
    algorithm = st.selectbox(
        "Ranking Algorithm",
        ["Standard", "Super Smart", "Super Super Smart (Bayesian)"],
        index=1,
    )

# Map user-friendly name → internal flag
if algorithm == "Super Smart":
    algo_flag = "smart"
elif algorithm.startswith("Super Super"):
    algo_flag = "bayesian"
else:
    algo_flag = "standard"

# Display past messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input box (chat-like)
if user_input := st.chat_input("Ask me about papers, citations, or concepts..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run query directly (scraper + captcha handled inside llm_wrapper)
    with st.chat_message("assistant"):
        with st.spinner("🔎 Searching papers (solve captcha if popup appears)..."):
            try:
                reply = chat_query(user_input, algorithm=algo_flag)
                if not reply.strip():
                    reply = (
                        "⚠️ No papers were returned. "
                        "If a Google Scholar captcha appeared, please solve it in the popup browser. "
                        "The system will continue automatically once solved."
                    )
            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"

        st.markdown(reply)

    # Add assistant reply to history
    st.session_state.messages.append({"role": "assistant", "content": reply})
