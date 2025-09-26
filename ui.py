import streamlit as st
from llm_wrapper import chat_query, run_scrape

st.set_page_config(page_title="📚 Research Helper", layout="wide")

st.title("📚 Research Helper (Chat Mode)")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_route" not in st.session_state:
    st.session_state.pending_route = None

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

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input box
if user_input := st.chat_input("Ask me about papers, citations, or concepts..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("🔎 Thinking..."):
            try:
                reply, route = chat_query(
                    user_input, algorithm=algo_flag, history=st.session_state.messages
                )
                # If the LLM wants confirmation before scraping
                if route.get("action") == "confirm_scrape":
                    st.session_state.pending_route = route
                    reply = route.get("reply", "⚠️ Do you want me to scrape Scholar?")
            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"
                route = None

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

# Pending scrape confirmation
if st.session_state.pending_route:
    with st.chat_message("assistant"):
        st.markdown(st.session_state.pending_route.get("reply", ""))

        query = st.session_state.pending_route.get("query", "")
        if query:
            st.code(query, language="text")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, scrape now"):
                reply = run_scrape(
                    st.session_state.pending_route,
                    algorithm=algo_flag,
                    history=st.session_state.messages,
                )
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.session_state.pending_route = None
                st.rerun()
        with col2:
            if st.button("❌ No, skip it"):
                st.session_state.messages.append(
                    {"role": "assistant", "content": "Okay, I won’t scrape this time."}
                )
                st.session_state.pending_route = None
                st.rerun()
