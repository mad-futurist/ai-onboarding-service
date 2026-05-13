from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.newcomer import NewcomerProfile


def get_documents_for_newcomer(db: Session, newcomer_id: int) -> list[Document]:
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise ValueError("Newcomer not found")

    job_title_normalized = (newcomer.job_title or "").lower().replace(" ", "_")

    all_docs = db.query(Document).all()

    def is_relevant(doc: Document) -> bool:
        if doc.scope == "enterprise":
            return True
        if doc.role_target is None:
            return True
        role_targets = [r.strip().lower() for r in doc.role_target.split(",")]
        return "all" in role_targets or job_title_normalized in role_targets

    def relevance_order(doc: Document) -> int:
        if doc.scope == "enterprise":
            return 0
        if doc.role_target and job_title_normalized in doc.role_target.lower():
            return 1
        return 2

    relevant = [d for d in all_docs if is_relevant(d)]
    return sorted(relevant, key=relevance_order)


def get_document_with_chunk_count(db: Session, document_id: int) -> dict | None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None
    chunks_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()
    return {"document": doc, "chunks_count": chunks_count}
