import streamlit as st
from app.scholar import search_scholar

st.title("📚 Research Helper")

query = st.text_input("Enter your research query:")
max_results = st.slider("Number of results", 1, 50, 10)
sort_by = st.selectbox("Sort by", ["relevance", "date"])

if st.button("Search"):
    results = search_scholar(query, max_results=max_results, sort_by=sort_by)
    for paper in results:
        st.markdown(f"### 📄 {paper['title']}")
        st.markdown(f"👤 {paper['authors_year']}")
        if paper['pdf_link']:
            st.markdown(f"[🔗 PDF Link]({paper['pdf_link']})")
        elif paper['scholar_link']:
            st.markdown(f"[🔗 Link]({paper['scholar_link']})")
        st.markdown(f"📝 {paper['snippet']}")
        st.markdown("---")
