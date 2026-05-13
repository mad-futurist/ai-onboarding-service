from fastapi import APIRouter, Depends, HTTPException
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
        content=payload.content,
        source=payload.source,
        document_type=payload.document_type,
        domain=payload.domain,
        role_target=payload.role_target,
        scope=payload.scope,
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
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if domain:
        query = query.filter(Document.domain == domain)
    if role_target:
        query = query.filter(Document.role_target == role_target)
    if scope:
        query = query.filter(Document.scope == scope)
    return query.order_by(Document.id.desc()).all()


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

    if payload.title is not None:
        document.title = payload.title

    if payload.content is not None:
        document.content = payload.content

    if payload.source is not None:
        document.source = payload.source

    if payload.document_type is not None:
        document.document_type = payload.document_type

    if payload.domain is not None:
        document.domain = payload.domain

    if payload.role_target is not None:
        document.role_target = payload.role_target

    if payload.scope is not None:
        document.scope = payload.scope

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