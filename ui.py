import streamlit as st
from llm_wrapper import summarize_paper, llm_select_papers

st.title("📚 Research Helper")

# Main query input
query = st.text_input("Enter your research query:", key="query_input")

# Collapsible filter section
with st.expander("🔍 Advanced Filters"):
    author = st.text_input("Filter by author:", key="author_filter")

# General options
max_results = st.slider("Number of results to show", 1, 20, 10, key="max_results_slider")
sort_by = st.selectbox("Sort by", ["relevance", "date"], key="sort_by_select")

# Algorithm choice
algorithm = st.selectbox("Ranking Algorithm", ["Standard", "Super Smart"])

# Algorithm weight controls (only for Standard)
if algorithm == "Standard":
    with st.expander("⚙️ Ranking Weights"):
        w_sim = st.slider("Similarity weight", 0.0, 1.0, 0.5, 0.01)
        w_cites = st.slider("Citation weight", 0.0, 1.0, 0.3, 0.01)
        w_recency = st.slider("Recency weight", 0.0, 1.0, 0.2, 0.01)

    # Normalize weights
    total = w_sim + w_cites + w_recency
    if total > 0:
        w_sim, w_cites, w_recency = w_sim / total, w_cites / total, w_recency / total
    else:
        st.warning("All weights are zero — falling back to defaults (0.5, 0.3, 0.2).")
        w_sim, w_cites, w_recency = 0.5, 0.3, 0.2
else:
    # Defaults (not used in Super Smart but required by function signature)
    w_sim, w_cites, w_recency = 0.5, 0.3, 0.2

# Search button
if st.button("Search", key="search_button"):
    if not query.strip():
        st.warning("Please enter a query to search.")
    else:
        # Build advanced query string
        advanced_query = query
        if author:
            advanced_query += f' author:"{author}"'

        with st.spinner("🔎 Searching and analyzing papers..."):
            # Run pipeline: scrape → filter (standard or smart) → LLM select
            results = llm_select_papers(
                advanced_query,
                pool_size=50,        # scrape pool
                filter_top_k=20,     # heuristic filter size
                final_top_n=max_results,
                sort_by=sort_by,
                algorithm="smart" if algorithm == "Super Smart" else "standard",
                w_sim=w_sim,
                w_cites=w_cites,
                w_recency=w_recency
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

