from fastapi import FastAPI
# from app.scholar import search_scholar

app = FastAPI()

@app.get("/ping")
def ping():
    return {"message": "pong"}

# @app.get("/search")
# def search(query: str, max_results: int = 5):
#     return search_scholar(query, max_results)
