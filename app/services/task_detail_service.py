import re

from sqlalchemy.orm import Session

from app.models.ai_question import AIQuestion
from app.models.document import Document
from app.models.onboarding_task import OnboardingTask


TOPIC_KEYWORDS: dict[str, list[str]] = {
    "deployment": ["deploy", "pipeline", "release", "staging", "rollback"],
    "access": ["access", "permission", "account", "login", "vpn"],
    "hr_process": ["vacation", "pointage", "leave", "hr", "holiday"],
    "code_review": ["review", "pr", "pull request", "merge", "approval"],
    "testing": ["test", "jest", "pytest", "unit", "integration"],
    "architecture": ["architecture", "service", "design", "component"],
    "jira_workflow": ["jira", "ticket", "sprint", "backlog", "story"],
}


def _get_task_keywords(task: OnboardingTask) -> set[str]:
    text = f"{task.title} {task.description or ''} {task.task_type}".lower()
    found: set[str] = set()
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in kws):
            found.add(topic)
    return found


def _tokens(value: str | None) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", (value or "").casefold())
        if len(token) > 3
    }


def _related_document_score(task_tokens: set[str], document: Document) -> int:
    document_tokens = _tokens(
        " ".join(
            filter(
                None,
                [
                    document.title,
                    document.source,
                    document.document_type,
                    document.domain,
                ],
            )
        )
    )

    return sum(
        1
        for task_token in task_tokens
        if any(
            task_token in document_token or document_token in task_token
            for document_token in document_tokens
        )
    )


def _role_tokens(value: str | None) -> set[str]:
    return {
        part.strip().casefold().replace(" ", "_")
        for part in (value or "").split(",")
        if part.strip()
    }


def _newcomer_role_aliases(plan) -> set[str]:
    if not plan or not plan.newcomer:
        return set()

    newcomer = plan.newcomer
    role_text = f"{newcomer.job_title or ''} {newcomer.team or ''}".casefold()
    aliases = _role_tokens(newcomer.job_title)

    if any(token in role_text for token in ["sales", "bdr", "account executive", "ae"]):
        aliases.update({"sales", "sales_manager", "bdr", "account_executive"})
    if any(token in role_text for token in ["backend", "developer", "engineering", "payments"]):
        aliases.update({"backend", "backend_developer", "engineering"})

    return aliases


def _documents_for_task(documents: list[Document], task: OnboardingTask, plan) -> list[Document]:
    task_tokens = _tokens(f"{task.title} {task.description or ''} {task.task_type}")
    scored_documents = sorted(
        (
            (_related_document_score(task_tokens, document), index, document)
            for index, document in enumerate(documents)
        ),
        key=lambda item: (-item[0], item[1]),
    )
    matched_documents = [
        document for score, _, document in scored_documents if score > 0
    ][:5]

    # Generated tasks can be phrased differently from their source document.
    # Keep a role-targeted fallback so sales tasks always keep useful sources.
    role_aliases = _newcomer_role_aliases(plan)
    role_documents = [
        document
        for document in documents
        if (_role_tokens(document.role_target) - {"all"}) & role_aliases
    ]

    related_documents: list[Document] = []
    seen_document_ids: set[int] = set()
    for document in [*matched_documents, *role_documents]:
        if document.id in seen_document_ids:
            continue
        related_documents.append(document)
        seen_document_ids.add(document.id)
        if len(related_documents) == 5:
            break

    return related_documents


def get_task_detail(db: Session, task_id: int) -> dict | None:
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if not task:
        return None

    task_keywords = _get_task_keywords(task)
    task_text = f"{task.title} {task.task_type}".lower()

    from app.models.onboarding_plan import OnboardingPlan
    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == task.plan_id).first()

    # Related documents
    all_docs = db.query(Document).limit(50).all()
    related_documents = _documents_for_task(all_docs, task, plan)

    # Related AI questions — from same plan/newcomer by keyword match
    related_questions = []
    if plan:
        from sqlalchemy.orm import joinedload
        qs = (
            db.query(AIQuestion)
            .options(joinedload(AIQuestion.sources))
            .filter(AIQuestion.newcomer_id == plan.newcomer_id)
            .order_by(AIQuestion.id.desc())
            .limit(20)
            .all()
        )
        for q in qs:
            q_text = q.question.lower()
            if any(kw in q_text for kw in task_text.split() if len(kw) > 4):
                related_questions.append(q)
                if len(related_questions) >= 3:
                    break

    # People to ask (from person_contacts if available)
    people_to_ask = []
    try:
        from app.models.person_contact import PersonContact
        contacts = db.query(PersonContact).filter(PersonContact.is_active == True).all()
        for c in contacts:
            c_topics = c.topics or []
            if any(t in task_keywords or any(kw in t for kw in task_text.split()) for t in c_topics):
                people_to_ask.append(c)
                if len(people_to_ask) >= 3:
                    break
    except Exception:
        pass

    # Blocked report status
    blocked_report_status = None
    try:
        from app.models.blocked_report import BlockedReport
        br = (
            db.query(BlockedReport)
            .filter(BlockedReport.task_id == task_id, BlockedReport.status == "open")
            .order_by(BlockedReport.id.desc())
            .first()
        )
        if br:
            blocked_report_status = br.status
    except Exception:
        pass

    why_it_matters = task.success_criteria or f"Completing this task moves you forward in your onboarding plan."
    suggested_prompt = f"How do I {task.title.lower()}?"

    return {
        "task": task,
        "why_it_matters": why_it_matters,
        "related_documents": related_documents,
        "related_ai_questions": related_questions,
        "people_to_ask": people_to_ask,
        "suggested_prompt": suggested_prompt,
        "blocked_report_status": blocked_report_status,
    }
