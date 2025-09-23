from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def search_scholar(query: str, max_results: int = 5):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"https://scholar.google.com/scholar?q={query}")

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    entries = soup.select(".gs_ri")[:max_results]

    for entry in entries:
        title_tag = entry.select_one("h3 a")
        title = title_tag.text if title_tag else "No title"
        link = title_tag["href"] if title_tag else None

        snippet = entry.select_one(".gs_rs")
        snippet_text = snippet.text if snippet else ""

        authors_year = entry.select_one(".gs_a")
        authors_year_text = authors_year.text if authors_year else ""

        results.append({
            "title": title,
            "link": link,
            "snippet": snippet_text,
            "authors_year": authors_year_text
        })

    return results

