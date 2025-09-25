import streamlit as st
from llm_wrapper import summarize_paper, llm_select_papers

st.title("📚 Research Helper")

# Main query input
query = st.text_input("Enter your research query:", key="query_input")

# Collapsible filter section (author filter for now)
with st.expander("🔍 Advanced Filters"):
    author = st.text_input("Filter by author:", key="author_filter")

# General options
max_results = st.slider("Number of results to show", 1, 20, 10, key="max_results_slider")
sort_by = st.selectbox("Sort by", ["relevance", "date"], key="sort_by_select")

if st.button("Search", key="search_button"):
    if not query.strip():
        st.warning("Please enter a query to search.")
    else:
        # Build advanced query string
        advanced_query = query
        if author:
            advanced_query += f' author:"{author}"'

        with st.spinner("🔎 Searching and analyzing papers..."):
            # Run pipeline: scrape → filter → LLM select
            results = llm_select_papers(
                advanced_query,
                pool_size=50,        # scrape pool
                filter_top_k=20,     # heuristic filter
                final_top_n=max_results,
                sort_by=sort_by
            )

        # Display results
        for paper in results:
            st.markdown(f"### 📄 {paper['title']}")
            st.markdown(f"👤 {paper['authors_year']}")
            if paper.get("citations"):
                st.markdown(f"🔢 Citations: {paper['citations']}")

            if paper.get("pdf_link"):
                st.markdown(f"[🔗 PDF Link]({paper['pdf_link']})")
            elif paper.get("scholar_link"):
                st.markdown(f"[🔗 Link]({paper['scholar_link']})")

            # AI summary
            if paper.get("title") or paper.get("snippet"):
                summary = summarize_paper(
                    title=paper.get("title", ""),
                    snippet=paper.get("snippet", ""),
                    authors_year=paper.get("authors_year", "")
                )
                st.markdown(f"**AI Summary:** {summary}")

            st.markdown("---")
