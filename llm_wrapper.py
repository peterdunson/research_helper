import os
import json
import ast
from datetime import datetime
from app.scholar import search_scholar
from openai import OpenAI
from dotenv import load_dotenv

# 🔹 Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_with_llm(query: str, max_results: int = 10, sort_by: str = "relevance"):
    # Step 1: scrape papers
    papers = search_scholar(query, max_results=max_results, sort_by=sort_by)

    # Step 2: build prompt
    raw_results = json.dumps(papers, indent=2)

    prompt = f"""
    You are a helpful research assistant. I scraped some papers from Google Scholar.
    Please list them clearly, with title, authors, year, and link.
    Only use the provided JSON input.

    JSON input:
    {raw_results}

    Format output in this style:

    📄 Title  
    👤 Authors/Year  
    🔗 Link  
    📝 Short Summary
    """

    # Step 3: call LLM
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content


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


def rerank_papers(query: str, papers: list, top_n: int = 10, method: str = "simple") -> list:
    """
    Rerank scraped papers by relevance.
    - simple: heuristic using citations + recency
    - LLM-powered: ask GPT to rerank by relevance
    """
    if method.startswith("simple"):
        scored = []
        for p in papers:
            # Citations score (log-scale to dampen huge numbers)
            c = p.get("citations") or 0
            citation_score = (c ** 0.5)

            # Year score (try to extract year from authors_year text)
            year_score = 0
            if p.get("authors_year"):
                for token in p["authors_year"].split():
                    if token.isdigit() and 1900 < int(token) <= datetime.now().year:
                        year_score = int(token)
                        break

            score = citation_score + (year_score / 1000.0)
            scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:top_n]]

    elif method.startswith("LLM"):
        compact_list = "\n\n".join(
            f"[{i+1}] {p['title']} — {p.get('authors_year','')}\n{p.get('snippet','')}"
            for i, p in enumerate(papers)
        )

        prompt = f"""
        You are an academic assistant. The user query is:

        {query}

        Here is a list of papers scraped from Google Scholar:

        {compact_list}

        Please rank these papers by **relevance to the query** and return only the top {top_n}.
        Return the result as a JSON array of indices (e.g., [2, 5, 1, ...]).
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        try:
            ranked_indices = ast.literal_eval(response.choices[0].message.content.strip())
        except Exception:
            ranked_indices = list(range(1, min(top_n, len(papers)) + 1))

        return [papers[i - 1] for i in ranked_indices if 0 < i <= len(papers)]

    else:
        return papers[:top_n]


if __name__ == "__main__":
    query = "bayesian regression"
    raw_papers = search_scholar(query, max_results=30, sort_by="relevance")

    print("🔹 Simple rerank:")
    top_simple = rerank_papers(query, raw_papers, top_n=5, method="simple")
    for p in top_simple:
        print("📄", p["title"], "| Citations:", p.get("citations"))

    print("\n🔹 LLM rerank:")
    top_llm = rerank_papers(query, raw_papers, top_n=5, method="LLM-powered")
    for p in top_llm:
        print("📄", p["title"], "|", p.get("authors_year"))
