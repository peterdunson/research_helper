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
    """Scrape + filter + rerank papers."""
    t0 = time.time()
    pool = search_scholar(query, pool_size=pool_size, sort_by=sort_by, wait_for_user=True)
    print(f"✅ DONE SCRAPING — got {len(pool)} results in {time.time() - t0:.2f} sec")

    if not pool:
        return []

    # Apply ranking algorithm
    if algorithm == "smart":
        filtered = smart_rank_papers(query, pool, max_results=filter_top_k)
    elif algorithm == "bayesian":
        return bayesian_rank_papers(query, pool, max_results=final_top_n)
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

    rerank_prompt = f"""
    The user asked about: {query}

    Here is a list of candidate papers:

    {compact_list}

    Select the {final_top_n} most relevant papers.
    Return ONLY a JSON array of indices (e.g., [2, 5, 1]).
    """

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": rerank_prompt}]
            )
            ranked_indices = ast.literal_eval(response.choices[0].message.content.strip())
            break
        except Exception as e:
            print(f"⚠️ LLM rerank failed attempt {attempt+1}: {e}")
            ranked_indices = []
            time.sleep(2)
    else:
        ranked_indices = list(range(1, min(final_top_n, len(filtered)) + 1))

    return [filtered[i - 1] for i in ranked_indices if 0 < i <= len(filtered)]


def summarize_paper(title: str, snippet: str, authors_year: str = "") -> str:
    """Generate a concise AI summary of a paper."""
    context = f"Title: {title}\nAuthors/Year: {authors_year}\nSnippet: {snippet}"

    prompt = f"""
    Summarize this academic paper in 2–3 sentences:
    {context}
    """

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


def chat_query(user_message: str, algorithm: str = "smart"):
    """
    Router:
    1. LLM decides whether to scrape or just answer.
    2. If scrape → optimize query for Scholar, then run pipeline.
    3. If answer → just return direct response.
    """

    router_prompt = f"""
    You are a research assistant. Decide how to handle this request.

    If the user is asking for papers, citations, or references:
      Output JSON like this:
      {{
        "action": "scrape",
        "query": "best possible search query to get relevant results",
        "sort_by": "relevance" or "date",
        "pool_size": 100,
        "filter_top_k": 20,
        "final_top_n": number of papers the user explicitly asked for (or 10 if unspecified)
      }}

    If the user is asking a general conceptual/explanatory question (not requiring papers):
      Output JSON like this:
      {{
        "action": "answer",
        "reply": "a direct helpful response to the user"
      }}

    User message:
    {user_message}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": router_prompt}]
        )
        route = json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"⚠️ Router failed: {e}")
        route = {"action": "scrape", "query": user_message, "sort_by": "relevance",
                 "pool_size": 100, "filter_top_k": 20, "final_top_n": 10}

    # Direct answer path
    if route.get("action") == "answer":
        return route.get("reply", "⚠️ LLM did not return an answer.")

    # Scrape path
    elif route.get("action") == "scrape":
        papers = llm_select_papers(
            query=route.get("query", user_message),
            pool_size=route.get("pool_size", 100),
            filter_top_k=route.get("filter_top_k", 20),
            final_top_n=route.get("final_top_n", 10),
            sort_by=route.get("sort_by", "relevance"),
            algorithm=algorithm,
        )

        if not papers:
            return "⚠️ No papers could be retrieved after scraping and filtering."

        # Format papers into conversational output
        summaries = []
        for p in papers:
            summary = summarize_paper(p["title"], p.get("snippet", ""), p.get("authors_year", ""))
            summaries.append(
                f"**{p['title']}**\n\n"
                f"*{p.get('authors_year','Unknown')}*\n\n"
                f"[Link]({p.get('link') or p.get('scholar_link')})\n\n"
                f"{summary}\n"
            )

        return (
            f"Here are the top {len(papers)} papers I found based on your request:\n\n" +
            "\n---\n".join(summaries)
        )

    else:
        return "⚠️ Router returned unknown action."


if __name__ == "__main__":
    msg1 = "Find me the 3 most cited Bayesian factor model papers in the last 5 years."
    print(chat_query(msg1, algorithm="smart"))

    msg2 = "What is a Bayesian prior?"
    print(chat_query(msg2, algorithm="smart"))

