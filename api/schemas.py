from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    session_id: str
