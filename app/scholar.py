from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import html
from urllib.parse import quote_plus
import time
import math
import re
from difflib import SequenceMatcher


def search_scholar(query: str, pool_size: int = 100, sort_by: str = "relevance"):
    """
    Scrape Google Scholar for a pool of papers (larger than needed).
    :param query: search keywords
    :param pool_size: how many papers to scrape
    :param sort_by: "relevance" (default) or "date"
    """
    results = []
    encoded_query = quote_plus(query)
    per_page = 10  # Scholar shows 10 results per page
    pages = (pool_size + per_page - 1) // per_page

    # Sorting param: relevance = 0, date = 1
    sort_param = "0" if sort_by == "relevance" else "1"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i in range(pages):
            start = i * per_page
            url = f"https://scholar.google.com/scholar?hl=en&q={encoded_query}&start={start}&scisbd={sort_param}"
            
            page.goto(url)
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            entries = soup.select(".gs_ri")

            for entry in entries:
                title_tag = entry.select_one("h3 a")
                title = html.unescape(title_tag.text.strip()) if title_tag else "No title"
                link = title_tag["href"] if title_tag else None

                snippet = entry.select_one(".gs_rs")
                snippet_text = html.unescape(snippet.text.strip()) if snippet else ""

                authors_year = entry.select_one(".gs_a")
                authors_year_text = html.unescape(authors_year.text.strip()) if authors_year else ""

                scholar_link = None
                if title_tag and title_tag.has_attr("href"):
                    scholar_link = (
                        "https://scholar.google.com" + title_tag["href"]
                        if title_tag["href"].startswith("/scholar")
                        else title_tag["href"]
                    )

                # PDF link (handle multiple Scholar layouts)
                pdf_tag = entry.select_one(".gs_or_ggsm a, .gs_ggsd a")
                pdf_link = pdf_tag["href"] if pdf_tag else None

                # citation count
                citations = None
                footer = entry.select_one(".gs_fl")
                if footer:
                    cite_link = footer.find("a", string=lambda s: s and "Cited by" in s)
                    if cite_link:
                        try:
                            citations = int(cite_link.text.replace("Cited by", "").strip())
                        except ValueError:
                            citations = None

                # Try to extract year
                year = None
                match = re.search(r"\b(19|20)\d{2}\b", authors_year_text)
                if match:
                    year = int(match.group(0))

                results.append({
                    "title": title,
                    "link": link,
                    "scholar_link": scholar_link,
                    "pdf_link": pdf_link,
                    "snippet": snippet_text,
                    "authors_year": authors_year_text,
                    "citations": citations,
                    "year": year
                })

            time.sleep(1)  # polite delay

        browser.close()

    return results


def rank_papers(query: str, papers: list, max_results: int = 20):
    """
    Heuristic filtering stage: rank by similarity + citations + recency.
    Returns top max_results to feed into the LLM.
    """
    scored = []
    for paper in papers:
        # similarity (title > snippet)
        sim = 0.0
        if paper.get("title"):
            sim = SequenceMatcher(None, query.lower(), paper["title"].lower()).ratio()
        elif paper.get("snippet"):
            sim = SequenceMatcher(None, query.lower(), paper["snippet"].lower()).ratio()

        # citations (log scaled)
        cites = math.log1p(paper["citations"]) if paper.get("citations") else 0.0

        # recency boost (2000 → 0.0, 2025 → 1.0)
        recency = 0.0
        if paper.get("year"):
            recency = max(0, (paper["year"] - 2000) / 25.0)

        # weighted score
        score = 0.5 * sim + 0.3 * (cites / 10) + 0.2 * recency
        scored.append((score, paper))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_results]]


if __name__ == "__main__":
    print("🔎 Testing scholar scraper...\n")
    pool = search_scholar("bayesian regression", pool_size=50, sort_by="relevance")
    ranked = rank_papers("bayesian regression", pool, max_results=10)

    for idx, r in enumerate(ranked, 1):
        print(f"\n=== Ranked Result {idx} ===")
        for key, value in r.items():
            print(f"{key}: {value}")



