from dataclasses import dataclass

import httpx
from openai import OpenAI
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.ai_question import AIQuestion, AIQuestionSource
from app.models.ai_conversation import AIConversation
from app.services.chunking_service import split_text_into_chunks, estimate_tokens
from app.services.embedding_service import create_embedding
from app.services.event_logger import log_onboarding_event
from app.services.topic_classifier import classify_topic


http_client = httpx.Client(verify=False)
client = OpenAI(http_client=http_client, api_key=settings.OPENAI_API_KEY)



@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    distance: float
    similarity: float


def generate_chunks_for_document(
    db: Session,
    document: Document,
) -> int:
    existing_chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .all()
    )

    for chunk in existing_chunks:
        db.delete(chunk)

    db.flush()

    chunks = split_text_into_chunks(document.content)

    created_count = 0

    for index, chunk_text in enumerate(chunks):
        embedding = create_embedding(chunk_text)

        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            content=chunk_text,
            token_estimate=estimate_tokens(chunk_text),
            embedding=embedding,
            source_title=document.title,
            source_type=document.document_type,
        )

        db.add(chunk)
        created_count += 1

    db.commit()

    return created_count


def retrieve_relevant_chunks(
    db: Session,
    question: str,
    top_k: int = 4,
) -> list[RetrievedChunk]:
    question_embedding = create_embedding(question)

    distance_expr = DocumentChunk.embedding.cosine_distance(question_embedding)

    rows = (
        db.query(DocumentChunk, distance_expr.label("distance"))
        .order_by(distance_expr)
        .limit(top_k)
        .all()
    )

    results: list[RetrievedChunk] = []

    for chunk, distance in rows:
        similarity = 1 - float(distance)

        results.append(
            RetrievedChunk(
                chunk=chunk,
                distance=float(distance),
                similarity=similarity,
            )
        )

    return results


def build_context_from_chunks(retrieved_chunks: list[RetrievedChunk]) -> str:
    if not retrieved_chunks:
        return "No relevant sources found."

    parts = []

    for index, item in enumerate(retrieved_chunks, start=1):
        chunk = item.chunk

        parts.append(
            f"""
SOURCE {index}
Document title: {chunk.source_title or "Untitled document"}
Document ID: {chunk.document_id}
Chunk ID: {chunk.id}
Similarity: {item.similarity:.4f}

Content:
{chunk.content}
"""
        )

    return "\n\n---\n\n".join(parts)


def generate_answer_from_sources(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    if not retrieved_chunks:
        return (
            "I could not find relevant information in the available onboarding documents. "
            "Please ask your mentor or upload more documentation."
        )

    context = build_context_from_chunks(retrieved_chunks)

    system_prompt = """
You are an AI onboarding assistant.

Your job:
- answer newcomer questions using only the provided company/onboarding sources;
- be clear, practical, and concise;
- mention when the sources are insufficient;
- do not invent company rules, links, people, or procedures;
- include a short "Sources used" section at the end with document titles.

If the answer is not in the sources, say that the available documents do not contain enough information.
"""

    user_prompt = f"""
Question:
{question}

Available sources:
{context}

Answer using only these sources.
"""

    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    return response.output_text


def _derive_conversation_title(question: str) -> str:
    cleaned = question.strip().splitlines()[0] if question.strip() else "New conversation"
    if len(cleaned) > 60:
        return cleaned[:57].rstrip() + "…"
    return cleaned or "New conversation"


def _resolve_conversation(
    db: Session,
    question: str,
    user_id: int | None,
    newcomer_id: int | None,
    conversation_id: int | None,
    context_type: str | None,
    context_id: int | None,
) -> AIConversation:
    if conversation_id is not None:
        conversation = (
            db.query(AIConversation)
            .filter(AIConversation.id == conversation_id)
            .first()
        )
        if conversation:
            return conversation

    conversation = AIConversation(
        user_id=user_id,
        newcomer_id=newcomer_id,
        title=_derive_conversation_title(question),
        context_type=context_type,
        context_id=context_id,
    )
    db.add(conversation)
    db.flush()
    return conversation


def ask_ai_with_sources(
    db: Session,
    question: str,
    user_id: int | None = None,
    newcomer_id: int | None = None,
    top_k: int = 4,
    conversation_id: int | None = None,
    context_type: str | None = None,
    context_id: int | None = None,
) -> AIQuestion:
    retrieved_chunks = retrieve_relevant_chunks(
        db=db,
        question=question,
        top_k=top_k,
    )

    answer = generate_answer_from_sources(
        question=question,
        retrieved_chunks=retrieved_chunks,
    )

    conversation = _resolve_conversation(
        db=db,
        question=question,
        user_id=user_id,
        newcomer_id=newcomer_id,
        conversation_id=conversation_id,
        context_type=context_type,
        context_id=context_id,
    )

    ai_question = AIQuestion(
        user_id=user_id,
        newcomer_id=newcomer_id,
        conversation_id=conversation.id,
        question=question,
        answer=answer,
        status="answered",
    )

    db.add(ai_question)
    db.flush()

    # Touch the conversation so it floats to the top of the history list.
    conversation.updated_at = func.now()

    for item in retrieved_chunks:
        chunk = item.chunk

        source = AIQuestionSource(
            question_id=ai_question.id,
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            title=chunk.source_title or "Untitled document",
            content_preview=chunk.content[:500],
            similarity=item.similarity,
        )

        db.add(source)

    db.commit()
    db.refresh(ai_question)

    if newcomer_id:
        topic = classify_topic(question)

        log_onboarding_event(
            db=db,
            newcomer_id=newcomer_id,
            user_id=user_id,
            event_type="ai_question_asked",
            entity_type="ai_question",
            entity_id=ai_question.id,
            topic=topic,
            metadata_json={
                "question": question,
                "source_titles": [source.title for source in ai_question.sources],
                "top_k": top_k,
            },
        )

    db.commit()
    db.refresh(ai_question)

    return ai_question