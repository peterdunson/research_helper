import os
import json
import ast
import time
from typing import List, Dict, Optional

from app.scholar import search_scholar, rank_papers
from openai import OpenAI
from dotenv import load_dotenv

# ── OpenAI client ──────────────────────────────────────────────────────────────
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-5-mini"  # single model everywhere

# ── Ranking modes (similarity, citations, recency weights) ─────────────────────
MODES = {
    "balanced": dict(w_sim=0.5, w_cites=0.3, w_recency=0.2),
    "recent": dict(w_sim=0.3, w_cites=0.2, w_recency=0.5),
    "famous": dict(w_sim=0.2, w_cites=0.7, w_recency=0.1),
    "influential": dict(w_sim=0.4, w_cites=0.4, w_recency=0.2),
    "hot": dict(w_sim=0.3, w_cites=0.4, w_recency=0.3),
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _clip_history(history: List[Dict[str, str]], max_chars: int = 4000) -> str:
    """Turn last few chat messages into a compact transcript for LLM context."""
    if not history:
        return ""

    tail = history[-8:]
    chunks = []
    running = 0
    for m in tail:
        piece = f"{m['role'].upper()}: {m['content']}\n"
        running += len(piece)
        chunks.append(piece)
    text = "".join(chunks)
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text.strip()


def _safe_json(s: str, fallback: dict) -> dict:
    try:
        return json.loads(s.strip())
    except Exception:
        return fallback


# ── Core pipeline (scrape → filter → optional LLM rerank) ─────────────────────
def llm_select_papers(
    query: str,
    pool_size: int = 100,
    filter_top_k: int = 20,
    final_top_n: int = 10,
    sort_by: str = "relevance",
    mode: str = "balanced",
    history_text: str = "",
):
    """Scrape Scholar → filter with mode → LLM rerank top candidates."""
    t0 = time.time()
    print("⏳ Starting Scholar scrape...")
    pool = search_scholar(query, pool_size=pool_size, sort_by=sort_by, wait_for_user=True)
    print(f"✅ DONE SCRAPING — {len(pool)} results in {time.time() - t0:.2f}s")

    if not pool:
        return []

    # Step 1. Filtering with mode
    t1 = time.time()
    weights = MODES.get(mode, MODES["balanced"])
    print(f"⏳ Starting filtering (mode={mode}, weights={weights})...")
    filtered = rank_papers(
        query,
        pool,
        max_results=min(filter_top_k, 30),
        w_sim=weights["w_sim"],
        w_cites=weights["w_cites"],
        w_recency=weights["w_recency"],
    )
    print(f"✅ Filtering done in {time.time() - t1:.2f}s")

    if not filtered:
        return []

    # Step 2. Build compact rerank input
    t2 = time.time()
    rerank_candidates = filtered[: min(12, len(filtered))]
    compact_list = "\n\n".join(
        f"[{i+1}] {p.get('title','No title')} — {p.get('authors_year','')}\n{p.get('snippet','')}"
        for i, p in enumerate(rerank_candidates)
    )

    rerank_prompt = f"""
Conversation context (resolve pronouns like 'those papers'):
{history_text}

User intent/topic to rank for:
{query}

Candidate papers:
{compact_list}

Select the {final_top_n} most relevant papers.
Return ONLY a JSON array of indices (e.g., [2, 5, 1]).
"""

    ranked_indices: Optional[List[int]] = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": rerank_prompt}],
            )
            ranked_indices = ast.literal_eval(
                response.choices[0].message.content.strip()
            )
            break
        except Exception as e:
            print(f"⚠️ LLM rerank failed attempt {attempt+1}: {e}")

    if not ranked_indices:
        ranked_indices = list(range(1, min(final_top_n, len(rerank_candidates)) + 1))

    print(f"✅ Rerank done in {time.time() - t2:.2f}s")
    return [
        rerank_candidates[i - 1]
        for i in ranked_indices
        if 0 < i <= len(rerank_candidates)
    ]


# ── Summaries ─────────────────────────────────────────────────────────────────
def summarize_paper(
    title: str, snippet: str, authors_year: str = "", history_text: str = ""
) -> str:
    """Generate a Markdown summary of a paper."""
    context = f"Title: {title}\nAuthors/Year: {authors_year}\nSnippet: {snippet}"

    prompt = f"""
Conversation history (for style/context):
{history_text}

Summarize this academic paper in 2–3 sentences.

**Formatting requirements:**
- Return the summary in Markdown.
- Use bold for important terms if useful.
- Keep the tone clear and concise.

Context:
{context}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ── Router (ask for confirmation before scraping) ──────────────────────────────
def chat_query(
    user_message: str,
    mode: str = "balanced",
    history: Optional[List[Dict[str, str]]] = None,
):
    """
    Router:
    - If "answer" → direct response in Markdown.
    - If "scrape" → first ask user for confirmation.
    """
    history = history or []
    history_text = _clip_history(history)

    router_prompt = f"""
You are a scholarly research assistant.

If the user is asking for papers, citations, references, "top N", "recent N", or "find/show me papers":
  Output JSON:
  {{
    "action": "confirm_scrape",
    "query": "optimized Scholar search query string",
    "sort_by": "relevance" or "date",
    "pool_size": 100,
    "filter_top_k": 20,
    "final_top_n": <integer or 10 if not clear>
  }}

If the user is asking a conceptual/explanatory question OR following up on papers already listed:
  Output JSON:
  {{
    "action": "answer",
    "reply": "helpful response in Markdown (use bold, bullet points, or sections if appropriate)."
  }}

Conversation history:
{history_text}

User message:
{user_message}
"""

    raw = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": router_prompt}],
    ).choices[0].message.content

    route = _safe_json(
        raw,
        fallback={
            "action": "answer",
            "reply": "⚠️ Sorry, I couldn't decide how to handle that.",
        },
    )

    if route.get("action") == "answer":
        return route.get("reply", ""), None

    if route.get("action") == "confirm_scrape":
        return (
            f"🤔 I think this request may require a Google Scholar search.\n\n"
            f"Do you want me to scrape Scholar with query: **{route.get('query')}** ?",
            route,
        )

    return "⚠️ Router returned unknown action.", None

def run_scrape(
    route: dict,
    mode: str = "balanced",
    history: Optional[List[Dict[str, str]]] = None,
    log_fn: Optional[callable] = None,
):
    """Actually run the scrape after user confirmation, with optional logging to UI."""
    history = history or []
    history_text = _clip_history(history)

    # Wrapper to send logs to Streamlit if log_fn is provided
    def log(msg: str):
        if log_fn:
            log_fn(msg)   # update UI
        else:
            print(msg)    # fallback to terminal

    log("⏳ Running full scrape pipeline...")
    papers = llm_select_papers(
        query=route.get("query", ""),
        pool_size=int(route.get("pool_size", 100)),
        filter_top_k=int(route.get("filter_top_k", 20)),
        final_top_n=int(route.get("final_top_n", 10)),
        sort_by=route.get("sort_by", "relevance"),
        mode=mode,
        history_text=history_text,
    )

    if not papers:
        return "⚠️ No papers could be retrieved after scraping and filtering."

    log("⏳ Starting summarization...")
    t3 = time.time()
    intro = f"Here are the top {len(papers)} papers for **{route.get('query')}**:\n"
    blocks = []
    for p in papers:
        title = p.get("title", "No title")
        authors = p.get("authors_year", "Unknown")
        snippet = p.get("snippet", "")
        link = p.get("link") or p.get("scholar_link") or p.get("pdf_link") or ""
        citations = p.get("citations", "N/A")

        summary = summarize_paper(title, snippet, authors, history_text=history_text)

        block = (
            f"## 📄 {title}\n\n"
            f"**👥 Authors/Year:** {authors}\n\n"
            f"**🔗 Link:** {('[Link](' + link + ')') if link else 'N/A'}\n\n"
            f"**📑 Citations:** {citations}\n\n"
            f"**📝 Summary:**\n{summary}\n"
        )

        blocks.append(block)

    log(f"✅ Summarization done in {time.time() - t3:.2f}s")
    return intro + "\n\n---\n\n".join(blocks)