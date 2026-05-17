from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.newcomer import NewcomerProfile


def _normalize_token(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def _role_aliases(newcomer: NewcomerProfile) -> set[str]:
    text = f"{newcomer.job_title or ''} {newcomer.team or ''}".lower()
    aliases = {_normalize_token(newcomer.job_title), "all"}
    if any(token in text for token in ["sales", "bdr", "account executive", "ae"]):
        aliases.update({"sales", "sales_manager", "bdr", "account_executive"})
    if any(token in text for token in ["backend", "developer", "engineering", "payments"]):
        aliases.update({"backend", "backend_developer", "engineering"})
    return {alias for alias in aliases if alias}


def _doc_role_targets(doc: Document) -> set[str]:
    if not doc.role_target:
        return {"all"}
    return {_normalize_token(part) for part in doc.role_target.split(",") if part.strip()}


def get_documents_for_newcomer(db: Session, newcomer_id: int) -> list[dict]:
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise ValueError("Newcomer not found")

    aliases = _role_aliases(newcomer)
    all_docs = db.query(Document).order_by(Document.created_at.desc(), Document.id.desc()).all()

    def recommendation(doc: Document) -> tuple[bool, str | None, int]:
        targets = _doc_role_targets(doc)
        if (targets - {"all"}) & aliases:
            return True, "Recommended for your role and current onboarding plan.", 0
        if doc.scope == "enterprise" or "all" in targets:
            return True, "Company-wide context recommended for every newcomer.", 1
        return False, None, 2

    items: list[dict] = []
    for doc in all_docs:
        is_recommended, reason, rank = recommendation(doc)
        items.append(
            {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "document_type": doc.document_type,
                "domain": doc.domain,
                "role_target": doc.role_target,
                "scope": doc.scope,
                "source_type": doc.source_type,
                "external_url": doc.external_url,
                "is_recommended": is_recommended,
                "recommendation_reason": reason,
                "created_at": doc.created_at,
                "_rank": rank,
            }
        )
    items.sort(key=lambda item: (item["_rank"], str(item["domain"] or ""), str(item["title"] or "")))
    for item in items:
        item.pop("_rank", None)
    return items


def get_document_with_chunk_count(db: Session, document_id: int) -> dict | None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None
    chunks_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()
    return {"document": doc, "chunks_count": chunks_count}
