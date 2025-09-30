import streamlit as st
from llm_wrapper import chat_query, run_scholar_lookup

st.set_page_config(page_title="📚 Research Helper", layout="wide")

st.title("📚 Research Helper")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_route" not in st.session_state:
    st.session_state.pending_route = None

# Sidebar for mode choice
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.selectbox(
        "Ranking Mode",
        ["auto", "balanced", "recent", "famous", "influential", "hot"],  # added auto
        index=0,  # default = auto
    )

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
                    user_input, mode=mode, history=st.session_state.messages
                )

                if route and route.get("action") == "scholar_lookup":
                    # Store pending route for later confirmation
                    st.session_state.pending_route = route
                    reply = f"🤔 This request may require a Google Scholar search.\n\nQuery: **{route.get('query','')}**"

            except Exception as e:
                print(f"⚠️ chat_query error: {e}")
                reply = f"⚠️ Error: {str(e)}"
                route = None

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

# Pending Scholar lookup confirmation
if st.session_state.pending_route:
    route = st.session_state.pending_route
    with st.chat_message("assistant"):
        st.markdown(route.get("reply", ""))

        query = route.get("query", "")
        if query:
            st.code(query, language="text")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Yes, search now"):
                print("🔎 User confirmed Scholar lookup...")

                status_box = st.empty()

                def log_update(msg: str):
                    print(msg)
                    status_box.markdown(f"```\n{msg}\n```")

                reply = run_scholar_lookup(
                    route, history=st.session_state.messages, log_fn=log_update
                )

                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )
                st.session_state.pending_route = None
                st.rerun()

        with col2:
            if st.button("❌ No, skip it"):
                print("⏭️ User declined Scholar lookup.")
                st.session_state.messages.append(
                    {"role": "assistant", "content": "Okay, I won’t query Scholar this time."}
                )
                st.session_state.pending_route = None
                st.rerun()

