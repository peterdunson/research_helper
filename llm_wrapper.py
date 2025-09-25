import os
import json
import ast
import time
from typing import List, Dict, Optional

from app.scholar import (
    search_scholar,
    rank_papers,
    smart_rank_papers,
    bayesian_rank_papers,
)
from openai import OpenAI
from dotenv import load_dotenv

# ── OpenAI client ──────────────────────────────────────────────────────────────
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-5-mini"  # single model everywhere (no temperature anywhere)


# ── Small helpers ──────────────────────────────────────────────────────────────
def _clip_history(history: List[Dict[str, str]], max_chars: int = 4000) -> str:
    """
    Turn the last few chat messages into a compact plain-text transcript that fits
    within max_chars. This gives the LLM enough context to resolve pronouns like
    'those papers above' without blowing up tokens.
    """
    if not history:
        return ""

    # Take the last ~8 turns and trim by characters
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
    algorithm: str = "smart",  # "standard", "smart", "bayesian"
    w_sim: float = 0.5,
    w_cites: float = 0.3,
    w_recency: float = 0.2,
    history_text: str = "",
):
    """
    Scrape Scholar → filter → (optionally) LLM rerank top candidates.
    history_text is a compact transcript snippet to help the LLM disambiguate
    references like 'those papers'.
    """
    t0 = time.time()
    pool = search_scholar(query, pool_size=pool_size, sort_by=sort_by, wait_for_user=True)
    print(f"✅ DONE SCRAPING — got {len(pool)} results in {time.time() - t0:.2f} sec")

    if not pool:
        return []

    # Step 1. Heuristic filter
    if algorithm == "smart":
        filtered = smart_rank_papers(query, pool, max_results=min(filter_top_k, 30))
    elif algorithm == "bayesian":
        # Fully model-based ranking, no LLM re-rank
        return bayesian_rank_papers(query, pool, max_results=final_top_n)
    else:
        filtered = rank_papers(
            query,
            pool,
            max_results=min(filter_top_k, 30),
            w_sim=w_sim,
            w_cites=w_cites,
            w_recency=w_recency,
        )

    if not filtered:
        return []

    # Step 2. Build compact rerank input (cap to top 10–12 for speed)
    rerank_candidates = filtered[: min(12, len(filtered))]
    compact_list = "\n\n".join(
        f"[{i+1}] {p['title']} — {p.get('authors_year','')}\n{p.get('snippet','')}"
        for i, p in enumerate(rerank_candidates)
    )

    rerank_prompt = f"""
You are helping pick the best research papers.

Conversation history (for context; resolve any 'those/the above' references from it):
{history_text}

User intent/topic to rank for:
{query}

Candidate papers (already prefiltered for quality):
{compact_list}

Select the {final_top_n} most relevant papers for the user intent above.
Return ONLY a JSON array of indices (e.g., [2, 5, 1]).
"""

    # Step 3. Rerank with LLM
    ranked_indices: Optional[List[int]] = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": rerank_prompt}],
            )
            ranked_indices = ast.literal_eval(response.choices[0].message.content.strip())
            break
        except Exception as e:
            print(f"⚠️ LLM rerank failed attempt {attempt+1}: {e}")

    if not ranked_indices:
        ranked_indices = list(range(1, min(final_top_n, len(rerank_candidates)) + 1))

    return [rerank_candidates[i - 1] for i in ranked_indices if 0 < i <= len(rerank_candidates)]


# ── Summaries ─────────────────────────────────────────────────────────────────
def summarize_paper(title: str, snippet: str, authors_year: str = "", history_text: str = "") -> str:
    """Generate a conversational 2–3 sentence summary of a paper."""
    context = f"Title: {title}\nAuthors/Year: {authors_year}\nSnippet: {snippet}"

    prompt = f"""
Use the conversation context to keep tone consistent. Summarize this paper in 2–3 sentences.
Focus on the main idea, method, and contribution. Avoid speculation.

Conversation history (for style/context):
{history_text}

{context}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ── Chat entrypoint (router) ───────────────────────────────────────────────────
def chat_query(
    user_message: str,
    algorithm: str = "smart",
    history: Optional[List[Dict[str, str]]] = None,
):
    """
    Router:
    - If "answer" → respond directly using history.
    - If "scrape" → LLM optimizes Scholar query, then scrape → filter → summarize.
    Pass in the recent Streamlit chat: history = st.session_state.messages
      (list of {role: "user"/"assistant", content: "..."}).
    """
    history = history or []
    history_text = _clip_history(history)

    router_prompt = f"""
You are a scholarly research assistant. Decide how to handle the user's request using the conversation so far.

If the user is asking for papers, citations, references, "top N", "recent N", or "find/show me papers":
  Output JSON exactly:
  {{
    "action": "scrape",
    "query": "an optimized Google Scholar query string for the user's need (concise, include key terms, date/field qualifiers if appropriate)",
    "sort_by": "relevance" or "date",
    "pool_size": 100,
    "filter_top_k": 20,
    "final_top_n": <integer number of papers requested, or 10 if not clearly specified>
  }}

If the user is asking a conceptual/explanatory question OR following up on papers you already listed (e.g., 'which one is most important', 'explain the second one', 'compare those two'):
  Output JSON exactly:
  {{
    "action": "answer",
    "reply": "a direct, helpful, concise response grounded in the conversation history"
  }}

Conversation history:
{history_text}

User message:
{user_message}
"""

    route_raw = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": router_prompt}],
    ).choices[0].message.content

    route = _safe_json(
        route_raw,
        fallback={
            "action": "scrape",
            "query": user_message,
            "sort_by": "relevance",
            "pool_size": 100,
            "filter_top_k": 20,
            "final_top_n": 10,
        },
    )

    # Direct answer path
    if route.get("action") == "answer":
        reply = route.get("reply", "").strip()
        return reply or "I tried to answer directly, but I didn't receive a reply payload."

    # Scrape path
    if route.get("action") == "scrape":
        # Run the end-to-end pipeline
        papers = llm_select_papers(
            query=route.get("query", user_message),
            pool_size=int(route.get("pool_size", 100)),
            filter_top_k=int(route.get("filter_top_k", 20)),
            final_top_n=int(route.get("final_top_n", 10)),
            sort_by=route.get("sort_by", "relevance"),
            algorithm=algorithm,
            history_text=history_text,
        )

        if not papers:
            return "⚠️ I couldn’t retrieve any papers after scraping and filtering. Try refining your query."

        # Summaries + conversational intro
        intro = (
            f"Got it — here are the top {len(papers)} papers I recommend "
            f"for **{route.get('query', user_message)}**:"
        )

        blocks = []
        for p in papers:
            summary = summarize_paper(
                p["title"],
                p.get("snippet", ""),
                p.get("authors_year", ""),
                history_text=history_text,
            )
            link = p.get("link") or p.get("scholar_link") or p.get("pdf_link") or ""
            block = (
                f"**{p['title']}**\n"
                f"*{p.get('authors_year','Unknown')}*\n"
                f"{('[Link](' + link + ')') if link else ''}\n"
                f"{summary}"
            )
            blocks.append(block)

        return intro + "\n\n" + "\n\n---\n\n".join(blocks)

    return "⚠️ I couldn’t determine how to handle that request."
