from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import html
from urllib.parse import quote_plus

def search_scholar(query: str, max_results: int = 5):
    results = []
    encoded_query = quote_plus(query)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"https://scholar.google.com/scholar?q={encoded_query}")

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

        # scholar link (stable result URL)
        scholar_link = None
        if title_tag and title_tag.has_attr("href"):
            scholar_link = "https://scholar.google.com" + title_tag["href"] if title_tag["href"].startswith("/scholar") else title_tag["href"]

        # pdf link (if available in right-hand column)
        pdf_tag = entry.find_parent().select_one(".gs_ggsd a")
        pdf_link = pdf_tag["href"] if pdf_tag else None

        results.append({
            "title": title,
            "link": link,
            "scholar_link": scholar_link,
            "pdf_link": pdf_link,
            "snippet": snippet_text,
            "authors_year": authors_year_text
        })

    return results
