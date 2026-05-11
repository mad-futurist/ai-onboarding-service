from pydantic import BaseModel
from fastapi import APIRouter

from app.services.llm_service import generate_answer


router = APIRouter(prefix="/ai", tags=["AI"])


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AskResponse)
def ask_ai(payload: AskRequest):
    answer = generate_answer(payload.question)
    return AskResponse(answer=answer)