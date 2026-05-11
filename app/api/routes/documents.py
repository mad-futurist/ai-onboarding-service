from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentRead


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/", response_model=DocumentRead)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    document = Document(
        title=payload.title,
        content=payload.content,
        source=payload.source,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.get("/", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.id.desc()).all()