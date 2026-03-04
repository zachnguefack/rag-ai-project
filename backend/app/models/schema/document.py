from pydantic import BaseModel


class DocumentCreateRequest(BaseModel):
    title: str
    content: str


class DocumentResponse(BaseModel):
    id: int
    title: str
    content: str
