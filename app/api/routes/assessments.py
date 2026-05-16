from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.db.session import SessionLocal
from app.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentQuestion,
    AssessmentSubmission,
)
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.schemas.assessment import (
    AssessmentAnswerUpdate,
    AssessmentGenerateRequest,
    AssessmentPublishRequest,
    AssessmentQuestionCreate,
    AssessmentQuestionRead,
    AssessmentQuestionUpdate,
    AssessmentRead,
    AssessmentRegenerateRequest,
    AssessmentSubmissionCreate,
    AssessmentSubmissionRead,
    AssessmentUpdate,
)
from app.services.ai_assessment_service import (
    build_plan_context_from_submission,
    evaluate_submission_with_ai,
    generate_assessment_with_ai,
    persist_generated_assessment,
    regenerate_single_question,
)
from app.services.ai_plan_service import generate_onboarding_plan_with_ai


router = APIRouter(prefix="/assessments", tags=["Assessments"])


def _load_assessment(db: Session, assessment_id: int) -> Assessment:
    assessment = (
        db.query(Assessment)
        .options(joinedload(Assessment.questions))
        .filter(Assessment.id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


def _load_documents(db: Session, ids: list[int]) -> list[Document]:
    if not ids:
        return []
    docs = db.query(Document).filter(Document.id.in_(ids)).all()
    found = {d.id for d in docs}
    missing = set(ids) - found
    if missing:
        raise HTTPException(
            status_code=404, detail=f"Documents not found: {sorted(missing)}"
        )
    return docs


# ----------------------------------------------------------------------
# Generation / regeneration
# ----------------------------------------------------------------------

@router.post("/generate", response_model=AssessmentRead)
def generate_assessment(
    payload: AssessmentGenerateRequest,
    db: Session = Depends(get_db),
):
    documents = _load_documents(db, payload.document_ids)

    # Optionally enrich with newcomer profile if id was provided
    if payload.newcomer_id:
        newcomer = (
            db.query(NewcomerProfile)
            .options(joinedload(NewcomerProfile.user))
            .filter(NewcomerProfile.id == payload.newcomer_id)
            .first()
        )
        if newcomer:
            payload.job_title = payload.job_title or newcomer.job_title
            payload.seniority = payload.seniority or newcomer.seniority
            payload.team = payload.team or newcomer.team

    result = generate_assessment_with_ai(payload, documents)
    assessment = persist_generated_assessment(db, payload, result)
    return assessment


@router.post("/{assessment_id}/regenerate", response_model=AssessmentRead)
def regenerate_assessment(
    assessment_id: int,
    payload: AssessmentRegenerateRequest,
    db: Session = Depends(get_db),
):
    assessment = _load_assessment(db, assessment_id)
    if assessment.status not in ("draft", "published"):
        raise HTTPException(
            status_code=400,
            detail="Cannot regenerate an assessment after submission.",
        )

    documents = _load_documents(db, payload.document_ids)

    base_request = AssessmentGenerateRequest(
        newcomer_id=assessment.newcomer_id,
        mentor_id=assessment.mentor_id,
        mentor_notes=payload.mentor_notes or assessment.mentor_notes,
        role_context=assessment.role_context,
        document_ids=payload.document_ids or (assessment.source_document_ids or []),
        question_count=len(assessment.questions) or 8,
        question_types=["mcq", "short_answer", "scenario"],
    )

    if payload.scope == "all":
        # Wipe existing questions and re-generate the full set
        db.query(AssessmentQuestion).filter(
            AssessmentQuestion.assessment_id == assessment.id
        ).delete()
        db.flush()

        result = generate_assessment_with_ai(base_request, documents)
        for idx, q in enumerate(result.output.questions):
            options_json = [o.model_dump() for o in q.options] if q.options else None
            db.add(
                AssessmentQuestion(
                    assessment_id=assessment.id,
                    order_index=idx,
                    question_type=q.question_type,
                    prompt=q.prompt,
                    context=q.context,
                    options=options_json,
                    expected_answer=q.expected_answer,
                    skill_tag=q.skill_tag,
                    difficulty=q.difficulty,
                )
            )
        assessment.title = result.output.title
        assessment.used_fallback = result.used_fallback
        db.commit()
        db.refresh(assessment)
        return assessment

    if payload.scope == "question":
        if not payload.target_id:
            raise HTTPException(
                status_code=400, detail="target_id is required for scope=question"
            )
        existing = (
            db.query(AssessmentQuestion)
            .filter(
                AssessmentQuestion.id == payload.target_id,
                AssessmentQuestion.assessment_id == assessment.id,
            )
            .first()
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Question not found")

        new_q = regenerate_single_question(base_request, documents)
        options_json = [o.model_dump() for o in new_q.options] if new_q.options else None

        existing.question_type = new_q.question_type
        existing.prompt = new_q.prompt
        existing.context = new_q.context
        existing.options = options_json
        existing.expected_answer = new_q.expected_answer
        existing.skill_tag = new_q.skill_tag
        existing.difficulty = new_q.difficulty

        db.commit()
        db.refresh(assessment)
        return assessment

    raise HTTPException(status_code=400, detail=f"Unknown scope: {payload.scope}")


# ----------------------------------------------------------------------
# Read / list / edit
# ----------------------------------------------------------------------

@router.get("", response_model=list[AssessmentRead])
def list_assessments(
    newcomer_id: int | None = None,
    mentor_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Assessment).options(joinedload(Assessment.questions))
    if newcomer_id is not None:
        query = query.filter(Assessment.newcomer_id == newcomer_id)
    if mentor_id is not None:
        query = query.filter(Assessment.mentor_id == mentor_id)
    if status:
        query = query.filter(Assessment.status == status)
    return query.order_by(Assessment.id.desc()).all()


@router.get("/{assessment_id}", response_model=AssessmentRead)
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    return _load_assessment(db, assessment_id)


@router.patch("/{assessment_id}", response_model=AssessmentRead)
def update_assessment(
    assessment_id: int,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
):
    assessment = _load_assessment(db, assessment_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assessment, field, value)
    db.commit()
    db.refresh(assessment)
    return assessment


# ----------------------------------------------------------------------
# Question CRUD
# ----------------------------------------------------------------------

@router.post("/{assessment_id}/questions", response_model=AssessmentQuestionRead)
def add_question(
    assessment_id: int,
    payload: AssessmentQuestionCreate,
    db: Session = Depends(get_db),
):
    assessment = _load_assessment(db, assessment_id)

    if payload.order_index is None:
        max_idx = max((q.order_index for q in assessment.questions), default=-1)
        order_index = max_idx + 1
    else:
        order_index = payload.order_index

    options_json = (
        [o.model_dump() for o in payload.options] if payload.options else None
    )
    question = AssessmentQuestion(
        assessment_id=assessment.id,
        order_index=order_index,
        question_type=payload.question_type,
        prompt=payload.prompt,
        context=payload.context,
        options=options_json,
        expected_answer=payload.expected_answer,
        skill_tag=payload.skill_tag,
        difficulty=payload.difficulty or "medium",
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.patch(
    "/{assessment_id}/questions/{question_id}",
    response_model=AssessmentQuestionRead,
)
def update_question(
    assessment_id: int,
    question_id: int,
    payload: AssessmentQuestionUpdate,
    db: Session = Depends(get_db),
):
    question = (
        db.query(AssessmentQuestion)
        .filter(
            AssessmentQuestion.id == question_id,
            AssessmentQuestion.assessment_id == assessment_id,
        )
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    data = payload.model_dump(exclude_unset=True)
    if "options" in data and data["options"] is not None:
        data["options"] = [o.model_dump() if hasattr(o, "model_dump") else o for o in data["options"]]
    for field, value in data.items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question


@router.delete("/{assessment_id}/questions/{question_id}")
def delete_question(
    assessment_id: int,
    question_id: int,
    db: Session = Depends(get_db),
):
    question = (
        db.query(AssessmentQuestion)
        .filter(
            AssessmentQuestion.id == question_id,
            AssessmentQuestion.assessment_id == assessment_id,
        )
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.commit()
    return {"detail": "Question deleted", "question_id": question_id}


# ----------------------------------------------------------------------
# Publish
# ----------------------------------------------------------------------

@router.patch("/{assessment_id}/publish", response_model=AssessmentRead)
def publish_assessment(
    assessment_id: int,
    payload: AssessmentPublishRequest,
    db: Session = Depends(get_db),
):
    assessment = _load_assessment(db, assessment_id)

    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == payload.newcomer_id)
        .first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    if not assessment.questions:
        raise HTTPException(
            status_code=400, detail="Cannot publish an assessment with no questions."
        )

    assessment.newcomer_id = newcomer.id
    if not assessment.mentor_id and newcomer.mentor_id:
        assessment.mentor_id = newcomer.mentor_id
    assessment.status = "published"
    assessment.published_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(assessment)
    return assessment


# ----------------------------------------------------------------------
# Newcomer-facing
# ----------------------------------------------------------------------

@router.get("/by-newcomer/{newcomer_id}", response_model=AssessmentRead | None)
def get_active_assessment_for_newcomer(
    newcomer_id: int, db: Session = Depends(get_db)
):
    """Returns the latest published assessment for the newcomer, or None."""
    assessment = (
        db.query(Assessment)
        .options(joinedload(Assessment.questions))
        .filter(Assessment.newcomer_id == newcomer_id)
        .filter(Assessment.status.in_(["published", "submitted", "evaluated"]))
        .order_by(Assessment.id.desc())
        .first()
    )
    return assessment


@router.post(
    "/{assessment_id}/submit",
    response_model=AssessmentSubmissionRead,
)
def submit_assessment(
    assessment_id: int,
    payload: AssessmentSubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    assessment = _load_assessment(db, assessment_id)
    if assessment.status not in ("published", "submitted"):
        raise HTTPException(
            status_code=400, detail="Assessment is not open for submission."
        )

    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == payload.newcomer_id)
        .first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    # Prevent double-submission
    existing = (
        db.query(AssessmentSubmission)
        .filter(
            AssessmentSubmission.assessment_id == assessment_id,
            AssessmentSubmission.newcomer_id == newcomer.id,
            AssessmentSubmission.submitted_at.isnot(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Assessment already submitted by this newcomer."
        )

    submission = AssessmentSubmission(
        assessment_id=assessment_id,
        newcomer_id=newcomer.id,
        submitted_at=datetime.now(timezone.utc),
        duration_seconds=payload.duration_seconds,
    )
    db.add(submission)
    db.flush()

    question_ids = {q.id for q in assessment.questions}
    for item in payload.answers:
        if item.question_id not in question_ids:
            continue
        db.add(
            AssessmentAnswer(
                submission_id=submission.id,
                question_id=item.question_id,
                answer_text=item.answer_text,
                selected_option_ids=item.selected_option_ids,
            )
        )

    assessment.status = "submitted"
    db.commit()
    db.refresh(submission)

    # Schedule evaluation + plan generation in the background
    background_tasks.add_task(_evaluate_and_generate_plan, submission.id)

    return submission


def _evaluate_and_generate_plan(submission_id: int) -> None:
    """Background hook: evaluate answers then trigger plan generation."""
    db = SessionLocal()
    try:
        evaluate_submission_with_ai(db, submission_id)

        submission = (
            db.query(AssessmentSubmission)
            .filter(AssessmentSubmission.id == submission_id)
            .first()
        )
        if not submission:
            return

        newcomer = (
            db.query(NewcomerProfile)
            .options(joinedload(NewcomerProfile.user))
            .filter(NewcomerProfile.id == submission.newcomer_id)
            .first()
        )
        if not newcomer:
            return

        # Don't re-generate if a draft plan already exists for this newcomer
        existing_plan = (
            db.query(OnboardingPlan)
            .filter(OnboardingPlan.newcomer_id == newcomer.id)
            .first()
        )
        if existing_plan:
            return

        plan_context = build_plan_context_from_submission(db, submission_id)
        documents: list[Document] = []
        ai_result = generate_onboarding_plan_with_ai(
            newcomer=newcomer,
            documents=documents,
            mentor_notes=plan_context,
        )
        ai_plan = ai_result.plan

        plan = OnboardingPlan(
            newcomer_id=newcomer.id,
            mentor_id=newcomer.mentor_id,
            title=ai_plan.title,
            description=(
                f"{ai_plan.description}\n\n"
                f"Plan summary: {ai_plan.plan_summary}\n\n"
                f"First 30 days goal: {ai_plan.first_30_days_goal}\n"
                f"Days 31-60 goal: {ai_plan.days_31_60_goal}\n"
                f"Days 61-90 goal: {ai_plan.days_61_90_goal}\n\n"
                f"Mentor focus: {ai_plan.mentor_focus}\n"
                f"Newcomer focus: {ai_plan.newcomer_focus}\n\n"
                f"Risk areas: {', '.join(ai_plan.risk_areas)}"
            ),
            status="draft",
            generated_by_ai=True,
            mentor_approved=False,
        )
        db.add(plan)
        db.flush()

        for task_output in ai_plan.tasks:
            db.add(
                OnboardingTask(
                    plan_id=plan.id,
                    title=task_output.title,
                    description=task_output.description,
                    week_number=task_output.week_number,
                    day_number=task_output.day_number,
                    task_type=task_output.task_type,
                    priority=task_output.priority,
                    success_criteria=task_output.success_criteria,
                    status="todo",
                )
            )

        newcomer.onboarding_status = "plan_generated"
        db.commit()
    finally:
        db.close()


# ----------------------------------------------------------------------
# Mentor review of submission
# ----------------------------------------------------------------------

@router.get(
    "/{assessment_id}/submission",
    response_model=AssessmentSubmissionRead | None,
)
def get_assessment_submission(
    assessment_id: int, db: Session = Depends(get_db)
):
    submission = (
        db.query(AssessmentSubmission)
        .options(joinedload(AssessmentSubmission.answers))
        .filter(AssessmentSubmission.assessment_id == assessment_id)
        .order_by(AssessmentSubmission.id.desc())
        .first()
    )
    return submission


@router.patch(
    "/{assessment_id}/answers/{answer_id}",
    response_model=AssessmentSubmissionRead,
)
def update_answer_mentor_score(
    assessment_id: int,
    answer_id: int,
    payload: AssessmentAnswerUpdate,
    db: Session = Depends(get_db),
):
    answer = (
        db.query(AssessmentAnswer)
        .join(AssessmentSubmission, AssessmentAnswer.submission_id == AssessmentSubmission.id)
        .filter(
            AssessmentAnswer.id == answer_id,
            AssessmentSubmission.assessment_id == assessment_id,
        )
        .first()
    )
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(answer, field, value)

    db.commit()

    submission = (
        db.query(AssessmentSubmission)
        .options(joinedload(AssessmentSubmission.answers))
        .filter(AssessmentSubmission.id == answer.submission_id)
        .first()
    )
    return submission
