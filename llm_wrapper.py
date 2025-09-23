import os
import json
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
        model="gpt-5-mini",  # can switch to gpt-4o or gpt-4.1 if you prefer
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


if __name__ == "__main__":
    query = "bayesian regression"
    formatted = format_with_llm(query, max_results=5, sort_by="date")
    print(formatted)

