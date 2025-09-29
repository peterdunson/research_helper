# 📚 research_helper

**research_helper** is a lightweight research assistant that combines  
👉 Large Language Models (LLMs) for reasoning, synthesis, and critique  
👉 Google Scholar scraping + ranking for literature discovery and verification  

It runs locally with a simple Streamlit UI or as a FastAPI backend, making it flexible for both interactive exploration and programmatic use.

---

## 🚀 Features

- **Chat UI (Streamlit)**
  - Ask conceptual questions and get Markdown-formatted answers
  - Search Google Scholar with multiple **ranking modes**:
    - `balanced`, `recent`, `famous`, `influential`, `hot`
  - Automatic summarization of top results with:
    - Title, authors/year  
    - Citations  
    - Link (Scholar/PDF)  
    - 2–3 sentence LLM-generated summary  
  - **Title verification mode**: paste one or more paper titles and the helper will:
    - ✅ Confirm + summarize if found in Scholar  
    - ❌ Warn if not found (likely fabricated)  
  - **Citation checking**: copy citations that an LLM gives you and verify if they are real or fake. Great for spotting hallucinated references.

- **Backend API (FastAPI)**
  - `/ping` health check
  - `/search` endpoint to query Scholar directly
  - JSON or LLM-friendly formatted output

- **Algorithms for Research Workflows**
  - Idea-to-Outline (turn topics into structured plans)
  - Evidence Synthesizer (summarize + compare notes/abstracts)
  - Critique-and-Revise (reviewer-in-the-loop feedback)

---

## 📂 Project Structure

```text
.
├─ README.md                # You are here
├─ requirements.txt         # Python dependencies
├─ Dockerfile               # Container build
├─ ui.py                    # Streamlit UI (chat mode)
├─ llm_wrapper.py           # LLM orchestration, Scholar integration
├─ app/
│  ├─ main.py               # FastAPI entry
│  ├─ scholar.py            # Scholar scraper + ranking modes
│  ├─ models.py             # Data models + formatters
│  └─ arxiv.py              # (placeholder for future Arxiv integration)
├─ tests/
│  └─ test_scholar.py       # Testing scaffold
└─ scrape_done.txt          # Marker file from scraper runs
````

---

## ⚡ Quick Start

### Prerequisites

* Python 3.10+
* An OpenAI API key (set `OPENAI_API_KEY` as an environment variable)
* [Playwright](https://playwright.dev/python/) (first-time setup: `playwright install chromium`)

### Installation

```bash
git clone https://github.com/peterdunson/research_helper.git
cd research_helper
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the Chat UI

```bash
streamlit run ui.py
```

### Run the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

Example:

```bash
curl "http://localhost:8000/search?query=bayesian+regression&max_results=5&raw=true"
```

---

## 🧮 Ranking Modes

Papers from Google Scholar are scored using different weightings of:

* **Similarity** (query ↔ title/snippet)
* **Citations** (log-scaled)
* **Recency** (year-based boost)

Available modes:

* `balanced` → 0.5 sim, 0.3 cites, 0.2 recency
* `recent` → 0.3 sim, 0.2 cites, 0.5 recency
* `famous` → 0.2 sim, 0.7 cites, 0.1 recency
* `influential` → 0.4 sim, 0.4 cites, 0.2 recency
* `hot` → 0.3 sim, 0.4 cites, 0.3 recency

---

## 🧑‍💻 Usage Patterns

* **Check if a paper is real:** Paste the title → get confirmation + summary.
* **Check if citations from an LLM are fake:** Copy the references into the helper → verify existence in Google Scholar.
* **Find top papers on a topic:** Ask for "recent Bayesian factor analysis papers" → ranked results + summaries.
* **Ask conceptual questions:** The LLM responds in Markdown with explanations.
* **Automate via API:** Integrate the `/search` endpoint into pipelines.

---

## 🐳 Docker

Build and run with Docker:

```bash
docker build -t research_helper .
docker run --rm -e OPENAI_API_KEY=$OPENAI_API_KEY -p 7860:7860 research_helper
```

---

## 🧪 Testing

Run tests:

```bash
pytest -q
```
