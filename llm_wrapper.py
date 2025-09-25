import os
import json
import ast
import time
from app.scholar import search_scholar, rank_papers, smart_rank_papers, bayesian_rank_papers
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
    algorithm: str = "smart",
    w_sim: float = 0.5,
    w_cites: float = 0.3,
    w_recency: float = 0.2,
):
    """
    Core pipeline:
    1. Scrape Google Scholar (handles captcha with manual confirmation).
    2. Filter papers using chosen algorithm.
    3. If not bayesian, use LLM to rerank top_n.
    """

    # ✅ wait_for_user=True ensures captcha confirmation & "DONE SCRAPING" marker
    pool = search_scholar(query, pool_size=pool_size, sort_by=sort_by, wait_for_user=True)

    # 🔁 Wait until scraping finishes
    while not os.path.exists("scrape_done.txt"):
        print("⏳ Waiting for scraping to finish...")
        time.sleep(2)

    print("✅ Scraping confirmed, proceeding to filtering + LLM rerank...")
    try:
        os.remove("scrape_done.txt")  # clear flag for next run
    except FileNotFoundError:
        pass

    if not pool:
        return []

    # Apply ranking algorithm
    if algorithm == "smart":
        filtered = smart_rank_papers(query, pool, max_results=filter_top_k)
    elif algorithm == "bayesian":
        filtered = bayesian_rank_papers(query, pool, max_results=final_top_n)
        return filtered
    else:
        filtered = rank_papers(
            query,
            pool,
            max_results=filter_top_k,
            w_sim=w_sim,
            w_cites=w_cites,
            w_recency=w_recency,
        )

    if not filtered:
        return []

    # Compact input for LLM reranking
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

    # 🔄 Retry loop in case LLM fails
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            ranked_indices = ast.literal_eval(response.choices[0].message.content.strip())
            break
        except Exception as e:
            print(f"⚠️ LLM rerank failed on attempt {attempt+1}: {e}")
            ranked_indices = []
            time.sleep(2)
    else:
        ranked_indices = list(range(1, min(final_top_n, len(filtered)) + 1))

    return [filtered[i - 1] for i in ranked_indices if 0 < i <= len(filtered)]


def summarize_paper(title: str, snippet: str, authors_year: str = "") -> str:
    """Generate a concise AI summary (3-4 sentences) of a paper."""
    context = f"Title: {title}\nAuthors/Year: {authors_year}\nSnippet: {snippet}"

    prompt = f"""
    Please summarize the following academic paper in 3-4 sentences, maximum.
    Focus on the main idea, methods, and contribution.
    {context}
    """

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


def chat_query(user_message: str, algorithm: str = "smart"):
    """
    Chat-driven entrypoint:
    1. LLM interprets user chat into algorithm parameters.
    2. Runs llm_select_papers with chosen algorithm.
    3. LLM summarizes results back to the user.
    """

    # Step 1: Interpret chat → parameters
    prompt = f"""
    Convert the user's request into JSON with fields:
    - query
    - sort_by ("relevance" or "date")
    - pool_size (default 100)
    - filter_top_k (default 20)
    - final_top_n (default 10)

    Only output JSON.
    User message:
    {user_message}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        params = json.loads(response.choices[0].message.content.strip())
    except Exception:
        params = {"query": user_message, "sort_by": "relevance", "pool_size": 100,
                  "filter_top_k": 20, "final_top_n": 10}

    # Step 2: Run algorithm
    papers = llm_select_papers(
        query=params.get("query", user_message),
        pool_size=params.get("pool_size", 100),
        filter_top_k=params.get("filter_top_k", 20),
        final_top_n=params.get("final_top_n", 10),
        sort_by=params.get("sort_by", "relevance"),
        algorithm=algorithm,
    )

    if not papers:
        return "⚠️ No papers could be retrieved after scraping and filtering."

    # Step 3: Summarize results
    compact_results = json.dumps(papers, indent=2)
    summary_prompt = f"""
    Here are some academic papers retrieved:

    {compact_results}

    Summarize clearly, listing:
    - Title
    - Authors/Year
    - Link
    - Short 2-3 sentence summary
    """

    for attempt in range(3):
        try:
            final_resp = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": summary_prompt}]
            )
            reply = final_resp.choices[0].message.content.strip()
            if reply:
                return reply
        except Exception as e:
            print(f"⚠️ LLM summary failed on attempt {attempt+1}: {e}")
            time.sleep(2)

    return "⚠️ LLM failed to summarize. Raw results:\n\n" + compact_results


if __name__ == "__main__":
    msg = "Find me recent highly cited Bayesian regression papers."
    reply = chat_query(msg, algorithm="smart")
    print("🤖 Chat assistant reply:\n")
    print(reply)
