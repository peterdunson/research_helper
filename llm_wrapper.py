import os
import json
import ast
from app.scholar import search_scholar, rank_papers, smart_rank_papers  # ⬅️ import smart_rank_papers
from openai import OpenAI
from dotenv import load_dotenv

# 🔹 Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def llm_select_papers(
    query: str,
    pool_size: int = 50,
    filter_top_k: int = 20,
    final_top_n: int = 10,
    sort_by: str = "relevance",
    algorithm: str = "standard",   # ⬅️ new parameter
    w_sim: float = 0.5,
    w_cites: float = 0.3,
    w_recency: float = 0.2,
):
    """
    End-to-end pipeline:
    1. Scrape Google Scholar (pool_size results).
    2. Filter papers:
       - "standard": rank_papers (similarity + citations + recency)
       - "smart": smart_rank_papers (semantic + advanced features)
    3. Let LLM pick the final final_top_n most relevant papers.
    """

    # Step 1: scrape a larger pool
    pool = search_scholar(query, pool_size=pool_size, sort_by=sort_by)

    # Step 2: filter with chosen algorithm
    if algorithm == "smart":
        filtered = smart_rank_papers(query, pool, max_results=filter_top_k)
    else:
        filtered = rank_papers(
            query,
            pool,
            max_results=filter_top_k,
            w_sim=w_sim,
            w_cites=w_cites,
            w_recency=w_recency,
        )

    # Step 3: prepare compact input for LLM
    compact_list = "\n\n".join(
        f"[{i+1}] {p['title']} — {p.get('authors_year','')}\n{p.get('snippet','')}"
        for i, p in enumerate(filtered)
    )

    prompt = f"""
    You are an academic assistant. The user query is:

    {query}

    Here is a list of candidate papers (already filtered for quality):

    {compact_list}

    Please select the {final_top_n} most relevant papers for the query.
    Return ONLY a JSON array of indices (e.g., [2, 5, 1, ...]).
    """

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]#,
        #temperature=0,
    )

    try:
        ranked_indices = ast.literal_eval(response.choices[0].message.content.strip())
    except Exception:
        # fallback: just take the first N
        ranked_indices = list(range(1, min(final_top_n, len(filtered)) + 1))

    return [filtered[i - 1] for i in ranked_indices if 0 < i <= len(filtered)]


def summarize_paper(title: str, snippet: str, authors_year: str = "") -> str:
    """Generate a concise AI summary (3-4 sentences) of a paper."""
    context = f"Title: {title}\nAuthors/Year: {authors_year}\nSnippet: {snippet}"

    prompt = f"""
    Please summarize the following academic paper in 3-4 sentences, maximum.
    Focus only on the main idea, methods, and contribution.
    Avoid unnecessary details.

    {context}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    query = "bayesian regression"

    print("🔹 Standard algorithm:")
    final_papers_std = llm_select_papers(
        query,
        pool_size=50,
        filter_top_k=15,
        final_top_n=5,
        algorithm="standard",
        w_sim=0.6,
        w_cites=0.2,
        w_recency=0.2
    )
    for p in final_papers_std:
        print("📄", p["title"], "|", p.get("authors_year"))

    print("\n🔹 Super Smart algorithm:")
    final_papers_smart = llm_select_papers(
        query,
        pool_size=50,
        filter_top_k=15,
        final_top_n=5,
        algorithm="smart"
    )
    for p in final_papers_smart:
        print("📄", p["title"], "|", p.get("authors_year"))
