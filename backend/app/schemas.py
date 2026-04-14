from pydantic import BaseModel
from typing import Optional


class Source(BaseModel):
    filename: str
    page: Optional[int] = None
    excerpt: str


class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    session_id: str


class IngestResponse(BaseModel):
    message: str
    chunks_added: int
    files_skipped: int = 0


class HistoryMessage(BaseModel):
    role: str  # "human" | "ai"
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]
