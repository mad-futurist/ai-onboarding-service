import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import (
    DocumentClassifyRequest,
    DocumentClassifyResponse,
    DocumentCreate,
    DocumentUpdate,
    DocumentRead,
    DocumentListItem,
    DocumentWithChunksRead,
    KnowledgeBaseGroupItem,
    KnowledgeBaseResponse,
)
from app.models.document_chunk import DocumentChunk
from app.schemas.document_chunk import DocumentChunkListItem
from app.services.llm_service import generate_answer


router = APIRouter(prefix="/documents", tags=["Documents"])


_ALLOWED_DOMAINS = ["engineering", "hr", "product", "finance", "security", "general"]
_ALLOWED_TYPES = ["guide", "handbook", "policy", "runbook", "checklist", "reference"]
_ALLOWED_SOURCE_TYPES = ["text", "url", "github", "file"]


def _coerce_choice(value: str, allowed: list[str], fallback: str) -> str:
    if not value:
        return fallback
    v = value.strip().lower().replace("-", "_")
    return v if v in allowed else fallback


_FALLBACK_DOMAIN_HINTS = {
    "engineering": ["api", "code", "deploy", "build", "git", "backend", "frontend", "infra", "ci/cd", "kubernetes", "docker"],
    "hr": ["onboarding", "vacation", "leave", "pointage", "absence", "salary", "hr ", "policy hr", "employee handbook"],
    "product": ["roadmap", "feature", "spec", "user story", "product"],
    "finance": ["budget", "invoice", "expense", "finance", "accounting", "revenue"],
    "security": ["security", "vpn", "credentials", "auth", "compliance", "audit", "incident"],
}

_FALLBACK_TYPE_HINTS = {
    "runbook": ["incident", "runbook", "on-call", "page", "alert"],
    "policy": ["policy", "rules", "compliance"],
    "checklist": ["checklist", "todo", "steps"],
    "handbook": ["handbook", "guidelines", "welcome"],
    "reference": ["reference", "spec", "api reference", "cheatsheet"],
}


def _heuristic_classify(content: str) -> tuple[str, str, str]:
    text = content.lower()
    domain = "general"
    best = 0
    for d, kws in _FALLBACK_DOMAIN_HINTS.items():
        score = sum(1 for k in kws if k in text)
        if score > best:
            best, domain = score, d
    doc_type = "guide"
    best = 0
    for t, kws in _FALLBACK_TYPE_HINTS.items():
        score = sum(1 for k in kws if k in text)
        if score > best:
            best, doc_type = score, t
    summary = re.sub(r"\s+", " ", content.strip())[:240]
    return domain, doc_type, summary


@router.post("/ai-classify", response_model=DocumentClassifyResponse)
def ai_classify_document(payload: DocumentClassifyRequest):
    """Look at the content (and optional title) and propose title/summary/domain/type/source_type.

    Mentors keep full control — the response is a suggestion they can override before saving.
    Falls back to keyword heuristics when the LLM is unavailable or returns junk.
    """
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    snippet = content[:4000]
    prompt = (
        "Classify this onboarding document. Return strict JSON with keys "
        "`title`, `summary`, `domain`, `document_type`, `source_type`.\n\n"
        f"Allowed domain values: {_ALLOWED_DOMAINS}.\n"
        f"Allowed document_type values: {_ALLOWED_TYPES}.\n"
        f"Allowed source_type values: {_ALLOWED_SOURCE_TYPES} (use 'text' for pasted text, 'file' for files).\n"
        "title: a concise (<=80 chars) human-readable title for the document.\n"
        "summary: 1–2 sentences (<=240 chars).\n\n"
        f"Title hint from user: {payload.title or '(none)'}\n"
        f"Content:\n---\n{snippet}\n---\n\n"
        "Return ONLY valid JSON, nothing else."
    )

    fallback_domain, fallback_type, fallback_summary = _heuristic_classify(content)
    fallback_title = payload.title or fallback_summary.split(".")[0][:80] or "Untitled document"

    try:
        raw = generate_answer(prompt) or ""
    except Exception:
        return DocumentClassifyResponse(
            title=fallback_title,
            summary=fallback_summary,
            domain=fallback_domain,
            document_type=fallback_type,
            source_type="text",
        )

    # Try to extract JSON block from the LLM response.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return DocumentClassifyResponse(
            title=fallback_title,
            summary=fallback_summary,
            domain=fallback_domain,
            document_type=fallback_type,
            source_type="text",
        )

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return DocumentClassifyResponse(
            title=fallback_title,
            summary=fallback_summary,
            domain=fallback_domain,
            document_type=fallback_type,
            source_type="text",
        )

    title = (parsed.get("title") or fallback_title).strip()[:140]
    summary = (parsed.get("summary") or fallback_summary).strip()[:300]
    domain = _coerce_choice(parsed.get("domain") or "", _ALLOWED_DOMAINS, fallback_domain)
    document_type = _coerce_choice(parsed.get("document_type") or "", _ALLOWED_TYPES, fallback_type)
    source_type = _coerce_choice(parsed.get("source_type") or "", _ALLOWED_SOURCE_TYPES, "text")

    return DocumentClassifyResponse(
        title=title,
        summary=summary,
        domain=domain,
        document_type=document_type,
        source_type=source_type,
    )


@router.get("/knowledge-base", response_model=KnowledgeBaseResponse)
def get_knowledge_base(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.id.desc()).all()
    groups_map: dict[tuple, list] = {}
    for doc in docs:
        key = (doc.domain, doc.scope)
        groups_map.setdefault(key, []).append(doc)
    groups = [
        KnowledgeBaseGroupItem(domain=k[0], scope=k[1], documents=v)
        for k, v in sorted(groups_map.items(), key=lambda x: -len(x[1]))
    ]
    return KnowledgeBaseResponse(total=len(docs), groups=groups)


@router.post("/", response_model=DocumentRead)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    document = Document(
        title=payload.title,
        content=payload.content or "",
        source=payload.source,
        document_type=payload.document_type,
        domain=payload.domain,
        role_target=payload.role_target,
        scope=payload.scope,
        source_type=payload.source_type,
        external_url=payload.external_url,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.get("/", response_model=list[DocumentListItem])
def list_documents(
    domain: str | None = None,
    role_target: str | None = None,
    scope: str | None = None,
    document_type: str | None = None,
    source_type: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if domain:
        query = query.filter(Document.domain == domain)
    if role_target:
        query = query.filter(Document.role_target == role_target)
    if scope:
        query = query.filter(Document.scope == scope)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if source_type:
        query = query.filter(Document.source_type == source_type)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Document.title.ilike(like), Document.source.ilike(like)))
    return (
        query.order_by(Document.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.get("/{document_id}/with-chunks", response_model=DocumentWithChunksRead)
def get_document_with_chunks(document_id: int, db: Session = Depends(get_db)):
    document = (
        db.query(Document)
        .options(joinedload(Document.chunks))
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)

    return document


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return {
        "detail": "Document deleted successfully",
        "document_id": document_id,
    }

@router.get("/{document_id}/chunks", response_model=list[DocumentChunkListItem])
def list_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
