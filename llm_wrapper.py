import os
import json
import ast
import time
import re
from typing import List, Dict, Optional
from difflib import SequenceMatcher

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
    "recent": dict(w_sim=0.25, w_cites=0.15, w_recency=0.6),
    "famous": dict(w_sim=0.2, w_cites=0.7, w_recency=0.1),
    "influential": dict(w_sim=0.4, w_cites=0.4, w_recency=0.2),
    "hot": dict(w_sim=0.3, w_cites=0.4, w_recency=0.3),
    "auto": None,  # let LLM decide
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _clip_history(history: List[Dict[str, str]], max_chars: int = 4000) -> str:
    if not history:
        return ""
    tail = history
    chunks, running = [], 0
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


# ── Core pipeline (broad search) ──────────────────────────────────────────────
def llm_select_papers(
    query: str,
    pool_size: int = 100,
    filter_top_k: int = 20,
    final_top_n: int = 10,
    sort_by: str = "relevance",
    mode: str = "balanced",
    history_text: str = "",
):
    t0 = time.time()
    pool = search_scholar(query, pool_size=pool_size, sort_by=sort_by, wait_for_user=True)
    if not pool:
        return []
    weights = MODES.get(mode, MODES["balanced"])
    filtered = rank_papers(
        query,
        pool,
        max_results=min(filter_top_k, 30),
        w_sim=weights["w_sim"],
        w_cites=weights["w_cites"],
        w_recency=weights["w_recency"],
    )
    if not filtered:
        return []
    rerank_candidates = filtered[: min(12, len(filtered))]
    compact_list = "\n\n".join(
        f"[{i+1}] {p.get('title','No title')} — {p.get('authors_year','')}\n{p.get('snippet','')}"
        for i, p in enumerate(rerank_candidates)
    )
    rerank_prompt = f"""
Conversation context:
{history_text}

User query:
{query}

Candidate papers:
{compact_list}

Select the {final_top_n} most relevant papers.
Return ONLY a JSON array of indices (e.g., [2, 5, 1]).
"""
    ranked_indices = None
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
    return [
        rerank_candidates[i - 1]
        for i in ranked_indices
        if 0 < i <= len(rerank_candidates)
    ]


# ── Batch summaries ───────────────────────────────────────────────────────────
def summarize_papers(papers: List[Dict], history_text: str = "") -> List[str]:
    paper_contexts = []
    for i, p in enumerate(papers, 1):
        paper_contexts.append(
            f"[{i}] Title: {p.get('title','No title')}\n"
            f"Authors/Year: {p.get('authors_year','Unknown')}\n"
            f"Snippet: {p.get('snippet','')}"
        )
    prompt = f"""
You are an assistant that ONLY summarizes papers.

Task: Summarize each of the following academic papers in 2–3 sentences.
Return one summary per paper, numbered [1], [2], etc.

Rules:
- Direct summaries only. No questions.
- Use Markdown.
- Bold important terms if helpful.
- Be concise and factual.

Conversation context:
{history_text}

Papers:
{chr(10).join(paper_contexts)}
"""
    response = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.strip()
    summaries = []
    for i in range(1, len(papers) + 1):
        marker = f"[{i}]"
        if marker in text:
            part = text.split(marker, 1)[1]
            next_marker = f"[{i+1}]"
            piece = part.split(next_marker)[0].strip() if next_marker in part else part.strip()
            summaries.append(piece)
        else:
            summaries.append("⚠️ Summary missing")
    return summaries


# ── Generalized Scholar lookup ────────────────────────────────────────────────
def scholar_lookup(
    query: str,
    mode: str = "broad",
    pool_size: int = 100,
    filter_top_k: int = 20,
    final_top_n: int = 10,
    sort_by: str = "relevance",
    history_text: str = "",
):
    if mode == "broad":
        return llm_select_papers(
            query=query,
            pool_size=pool_size,
            filter_top_k=filter_top_k,
            final_top_n=final_top_n,
            sort_by=sort_by,
            mode="balanced",
            history_text=history_text,
        )
    elif mode == "direct":
        pool = search_scholar(query, pool_size=3, sort_by=sort_by, wait_for_user=False)
        return pool if pool else []
    return []


# ── Router ────────────────────────────────────────────────────────────────────
def chat_query(user_message: str, mode: str = "balanced", history: Optional[List[Dict[str, str]]] = None):
    history = history or []
    history_text = _clip_history(history)

    # 🔹 Extract "N papers" or "top N" from user request
    match = re.search(r"\b(?:top\s*)?(\d+)\s+(?:papers|articles|studies)\b", user_message.lower())
    requested_n = int(match.group(1)) if match else 10

    # 🔹 Resolve auto mode via LLM
    if mode == "auto":
        mode_prompt = """
You are deciding the best Scholar ranking mode based on the user query.

Available modes (weights = similarity, citations, recency):
- balanced: 0.5, 0.3, 0.2
- recent: 0.3, 0.2, 0.5
- famous: 0.2, 0.7, 0.1
- influential: 0.4, 0.4, 0.2
- hot: 0.3, 0.4, 0.3

Pick ONE mode name (just the word).
"""
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": mode_prompt + "\n\nUser query:\n" + user_message}],
        )
        picked = resp.choices[0].message.content.strip().lower()
        if picked in MODES and picked != "auto":
            mode = picked
        else:
            mode = "balanced"

    router_prompt = f"""
You are a scholarly research assistant.

If the user asks for papers, citations, references, or to check a specific title:
  Output JSON:
  {{
    "action": "scholar_lookup",
    "query": "optimized Scholar search query string",
    "mode": "broad" or "direct",
    "pool_size": 100,
    "filter_top_k": 20,
    "final_top_n": {requested_n}
  }}

If the user is asking a conceptual/explanatory question OR following up:
  Output JSON:
  {{
    "action": "answer",
    "reply": "helpful response in **well-formatted Markdown**. Always use:\n- Headings (##, ###) for structure\n- **bold** for key terms\n- Bullet lists where appropriate\n- Paragraph spacing for readability"
  }}

Conversation history:
{history_text}

User message:
{user_message}
"""
    raw = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": router_prompt}]
    ).choices[0].message.content
    route = _safe_json(raw, fallback={"action": "answer", "reply": "⚠️ Couldn't decide."})

    if route.get("action") == "answer":
        return route.get("reply", ""), None

    if route.get("action") == "scholar_lookup":
        # Attach chosen mode for later
        route["ranking_mode"] = mode
        return f"🔎 Let me check Google Scholar for: **{route.get('query')}** (mode={mode})", route

    return "⚠️ Router returned unknown action.", None


# ── Run Scholar lookup ────────────────────────────────────────────────────────
def run_scholar_lookup(route: dict, history: Optional[List[Dict[str, str]]] = None, log_fn: Optional[callable] = None):
    history = history or []
    history_text = _clip_history(history)

    def log(msg: str):
        if log_fn: log_fn(msg)
        else: print(msg)

    log("⏳ Running Scholar lookup pipeline...")
    papers = scholar_lookup(
        query=route.get("query", ""),
        mode=route.get("mode", "broad"),
        pool_size=int(route.get("pool_size", 100)),
        filter_top_k=int(route.get("filter_top_k", 20)),
        final_top_n=int(route.get("final_top_n", 10)),
        sort_by=route.get("sort_by", "relevance"),
        history_text=history_text,
    )
    if not papers:
        return "⚠️ No papers could be retrieved."

    if route.get("mode") == "direct":
        best = papers[0]
        sim = SequenceMatcher(None, route.get("query","").lower(), best.get("title","").lower()).ratio()
        if sim > 0.85:
            return f"## 📄 {best.get('title')}\n**Status:** ✅ Found\n**👥 Authors/Year:** {best.get('authors_year','Unknown')}\n**📑 Citations:** {best.get('citations','N/A')}\n**🔗 Link:** {best.get('link') or best.get('scholar_link') or 'N/A'}"
        else:
            return f"## 📄 {route.get('query')}\n**Status:** ❌ Not found in Google Scholar — probably fake."

    log("⏳ Starting summarization...")
    summaries = summarize_papers(papers, history_text=history_text)
    blocks = []
    for p, summary in zip(papers, summaries):
        block = (
            f"## 📄 {p.get('title','No title')}\n\n"
            f"**👥 Authors/Year:** {p.get('authors_year','Unknown')}\n\n"
            f"**🔗 Link:** {p.get('link') or p.get('scholar_link') or 'N/A'}\n\n"
            f"**📑 Citations:** {p.get('citations','N/A')}\n\n"
            f"**📝 Summary:**\n{summary}\n"
        )
        blocks.append(block)

    ranking_mode = route.get("ranking_mode", "balanced")
    return f"Here are {len(papers)} papers for **{route.get('query')}** (mode={ranking_mode}):\n\n" + "\n\n---\n\n".join(blocks)
