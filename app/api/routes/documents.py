from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import (
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


router = APIRouter(prefix="/documents", tags=["Documents"])


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
