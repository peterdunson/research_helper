from fastapi import FastAPI, Query
from typing import List, Union
from app.scholar import search_scholar
from app.models import Paper, format_results_for_llm

app = FastAPI()

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/search")
def search(
    query: str,
    max_results: int = Query(10, ge=1, le=50),
    sort_by: str = Query("relevance", pattern="^(relevance|date)$"),
    raw: bool = False
) -> Union[List[Paper], dict]:
    """
    Search Google Scholar.
    - raw=true → return JSON (list of Paper objects)
    - raw=false → return formatted text for LLMs
    """
    results = search_scholar(query, max_results=max_results, sort_by=sort_by)

    if raw:
        return results  # validated as JSON
    else:
        return {"results": format_results_for_llm(results)}
