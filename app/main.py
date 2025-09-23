from fastapi import FastAPI
from typing import List
from app.scholar import search_scholar
from app.models import Paper

app = FastAPI(
    title="Research Helper API",
    description="Scrapes Google Scholar for research papers and returns structured results.",
    version="0.1.0"
)

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/search", response_model=List[Paper])
def search(query: str, max_results: int = 5):
    """
    Search Google Scholar for papers matching the query.
    - **query**: search keywords
    - **max_results**: number of results to return (default: 5)
    """
    return search_scholar(query, max_results)
