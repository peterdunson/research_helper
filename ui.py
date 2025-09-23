import streamlit as st
from app.scholar import search_scholar
from llm_wrapper import summarize_paper  # ⬅️ import the new helper

st.title("📚 Research Helper")

query = st.text_input("Enter your research query:")
max_results = st.slider("Number of results", 1, 50, 10)
sort_by = st.selectbox("Sort by", ["relevance", "date"])

if st.button("Search"):
    results = search_scholar(query, max_results=max_results, sort_by=sort_by)
    for paper in results:
        st.markdown(f"### 📄 {paper['title']}")
        st.markdown(f"👤 {paper['authors_year']}")
        if paper.get("citations") is not None:
            st.markdown(f"🔢 Cited by: {paper['citations']}")   # 👈 add this


        if paper['pdf_link']:
            st.markdown(f"[🔗 PDF Link]({paper['pdf_link']})")
        elif paper['scholar_link']:
            st.markdown(f"[🔗 Link]({paper['scholar_link']})")

        # 🔹 Add concise AI summary (if snippet/title exist)
        if paper['title'] or paper['snippet']:
            summary = summarize_paper(
                title=paper['title'],
                snippet=paper['snippet'],
                authors_year=paper['authors_year']
            )
            st.markdown(f"**AI Summary:** {summary}")

        st.markdown("---")
