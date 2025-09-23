from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import html
from urllib.parse import quote_plus
import time

def search_scholar(query: str, max_results: int = 10, sort_by: str = "relevance"):
    """
    Scrape Google Scholar for papers.
    :param query: search keywords
    :param max_results: number of results to return
    :param sort_by: "relevance" (default) or "date"
    """
    results = []
    encoded_query = quote_plus(query)
    per_page = 10  # Scholar shows 10 results per page
    pages = (max_results + per_page - 1) // per_page

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
                print("\n=== ENTRY DEBUG ===")
                print(entry.prettify())

                title_tag = entry.select_one("h3 a")
                title = html.unescape(title_tag.text.strip()) if title_tag else "No title"
                link = title_tag["href"] if title_tag else None

                snippet = entry.select_one(".gs_rs")
                snippet_text = html.unescape(snippet.text.strip()) if snippet else ""

                authors_year = entry.select_one(".gs_a")
                authors_year_text = html.unescape(authors_year.text.strip()) if authors_year else ""
                print(entry.prettify()[:1000])

                scholar_link = None
                if title_tag and title_tag.has_attr("href"):
                    scholar_link = (
                        "https://scholar.google.com" + title_tag["href"]
                        if title_tag["href"].startswith("/scholar")
                        else title_tag["href"]
                    )

                pdf_tag = entry.find_parent().select_one(".gs_ggsd a")
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


                results.append({
                    "title": title,
                    "link": link,
                    "scholar_link": scholar_link,
                    "pdf_link": pdf_link,
                    "snippet": snippet_text,
                    "authors_year": authors_year_text,
                    "citations": citations
                })


                if len(results) >= max_results:
                    break

            if len(results) >= max_results:
                break

            time.sleep(1)  # polite delay

        browser.close()
        # Post-process: allow sorting by citations if requested
    if sort_by == "citations":
        results = sorted(
            results,
            key=lambda r: (r.get("citations") or 0),
            reverse=True
        )

    return results

if __name__ == "__main__":
    print("🔎 Testing scholar scraper...\n")
    results = search_scholar("bayesian regression", max_results=3, sort_by="relevance")
    for idx, r in enumerate(results, 1):
        print(f"\n=== Result {idx} ===")
        for key, value in r.items():
            print(f"{key}: {value}")


