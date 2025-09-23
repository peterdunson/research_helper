from pydantic import BaseModel
from typing import Optional

class Paper(BaseModel):
    title: str
    link: Optional[str]
    scholar_link: Optional[str]
    pdf_link: Optional[str]
    snippet: Optional[str]
    authors_year: Optional[str]
