from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import html

def search_scholar(query: str, max_results: int = 5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"https://scholar.google.com/scholar?q={query}")

        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    entries = soup.select(".gs_ri")[:max_results]

    for entry in entries:
        title_tag = entry.select_one("h3 a")
        title = html.unescape(title_tag.text.strip()) if title_tag else "No title"
        link = title_tag["href"] if title_tag else None

        snippet = entry.select_one(".gs_rs")
        snippet_text = html.unescape(snippet.text.strip()) if snippet else ""

        authors_year = entry.select_one(".gs_a")
        authors_year_text = html.unescape(authors_year.text.strip()) if authors_year else ""

        results.append({
            "title": title,
            "link": link,
            "snippet": snippet_text,
            "authors_year": authors_year_text
        })

    return results
