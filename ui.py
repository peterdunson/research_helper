import streamlit as st
from app.scholar import search_scholar
from llm_wrapper import summarize_paper, rerank_papers  # ⬅️ import rerank_papers

st.title("📚 Research Helper")

# Main query input
query = st.text_input("Enter your research query:", key="query_input")

# Collapsible filter section (only author now)
with st.expander("🔍 Advanced Filters"):
    author = st.text_input("Filter by author:", key="author_filter")

# General options
max_results = st.slider("Number of results", 1, 50, 10, key="max_results_slider")
sort_by = st.selectbox("Sort by", ["relevance", "date"], key="sort_by_select")

if st.button("Search", key="search_button"):
    # Build advanced query string
    advanced_query = query
    if author:
        advanced_query += f' author:"{author}"'

    # 🔹 Scrape *more* results than needed (e.g. 30), then rerank to top N
    raw_results = search_scholar(advanced_query, max_results=30, sort_by=sort_by)
    results = rerank_papers(query, raw_results, top_n=max_results)

    # Display results
    for paper in results:
        st.markdown(f"### 📄 {paper['title']}")
        st.markdown(f"👤 {paper['authors_year']}")
        if paper.get("citations"):
            st.markdown(f"🔢 Citations: {paper['citations']}")

        if paper['pdf_link']:
            st.markdown(f"[🔗 PDF Link]({paper['pdf_link']})")
        elif paper['scholar_link']:
            st.markdown(f"[🔗 Link]({paper['scholar_link']})")

        # AI summary
        if paper['title'] or paper['snippet']:
            summary = summarize_paper(
                title=paper['title'],
                snippet=paper['snippet'],
                authors_year=paper['authors_year']
            )
            st.markdown(f"**AI Summary:** {summary}")

        st.markdown("---")
