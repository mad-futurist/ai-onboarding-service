import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.services.llm_service import client


_SYSTEM_PROMPT = (
    "You build concise, well-structured mind maps from documents. "
    "You always reply with strict JSON (no prose, no markdown fences) using the schema: "
    '{"root": "<central topic, 2-6 words>", '
    '"branches": [{"label": "<branch label, 2-5 words>", '
    '"leaves": ["<leaf 1, 2-6 words>", "<leaf 2>", ...]}, ...]}'
    " Aim for 4-7 branches, each with 2-4 leaves. Avoid duplicates. "
    "Use the document's own language (French or English) for labels."
)


_USER_PROMPT_TEMPLATE = (
    "Document title: {title}\n\n"
    "Document content (truncated):\n{content}\n\n"
    "Return the mind map JSON now."
)


def _truncate(text: str, limit: int = 6000) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + "…"


def _strip_code_fences(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _flatten_mindmap(parsed: dict[str, Any]) -> dict[str, Any]:
    root_label = str(parsed.get("root") or "Knowledge").strip() or "Knowledge"
    nodes: list[dict[str, str]] = [{"id": "root", "label": root_label, "kind": "root"}]
    edges: list[dict[str, str]] = []

    branches = parsed.get("branches") or []
    for b_idx, branch in enumerate(branches):
        if not isinstance(branch, dict):
            continue
        branch_label = str(branch.get("label") or f"Branch {b_idx + 1}").strip()
        branch_id = f"b{b_idx}"
        nodes.append({"id": branch_id, "label": branch_label, "kind": "branch"})
        edges.append({"source": "root", "target": branch_id})

        leaves = branch.get("leaves") or []
        for l_idx, leaf in enumerate(leaves):
            leaf_label = str(leaf).strip()
            if not leaf_label:
                continue
            leaf_id = f"{branch_id}_l{l_idx}"
            nodes.append({"id": leaf_id, "label": leaf_label, "kind": "leaf"})
            edges.append({"source": branch_id, "target": leaf_id})

    return {"root": root_label, "nodes": nodes, "edges": edges}


def _fallback_mindmap(doc: Document) -> dict[str, Any]:
    return {
        "root": doc.title or "Document",
        "nodes": [
            {"id": "root", "label": doc.title or "Document", "kind": "root"},
            {"id": "b0", "label": doc.domain or "Domain", "kind": "branch"},
            {"id": "b1", "label": doc.document_type or "Type", "kind": "branch"},
        ],
        "edges": [
            {"source": "root", "target": "b0"},
            {"source": "root", "target": "b1"},
        ],
    }


def generate_mindmap_for_document(db: Session, document_id: int) -> dict[str, Any] | None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return None

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        title=doc.title or "Untitled",
        content=_truncate(doc.content or ""),
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(_strip_code_fences(raw))
        return _flatten_mindmap(parsed)
    except (json.JSONDecodeError, Exception):
        return _fallback_mindmap(doc)
