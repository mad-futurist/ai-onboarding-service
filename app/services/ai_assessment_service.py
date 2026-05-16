import json
import httpx
import uuid

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentSubmission,
    AssessmentAnswer,
)
from app.models.document import Document
from app.schemas.assessment import (
    AIAssessmentOutput,
    AIAssessmentQuestionOutput,
    AIAssessmentOptionOutput,
    AIAssessmentServiceResult,
    AssessmentGenerateRequest,
)

http_client = httpx.Client(verify=False)
client = OpenAI(http_client=http_client, api_key=settings.OPENAI_API_KEY)


SYSTEM_PROMPT = """
You are an expert onboarding coach helping a mentor calibrate a new joiner's real-world skill level.
You design short, fair, and friendly skill-check assessments composed of three question types:
- mcq: single-correct multiple choice. 3-4 options. Exactly one is_correct=true. Distractors are plausible.
- short_answer: a concise free-form question that probes understanding. Provide an expected_answer (1-3 sentences) the evaluator can compare against.
- scenario: a real workplace situation. The candidate explains how they would approach it. Provide an expected_answer describing the ideal reasoning.
Always tag each question with a skill_tag (a short slug, e.g., "git", "react", "team-communication").
Difficulty must be one of: easy, medium, hard.
Questions must be answerable in under 3 minutes each.
Avoid trivia. Focus on judgment, applied knowledge, and team-relevant scenarios.
Output strictly valid JSON.
""".strip()


def _build_documents_context(documents: list[Document]) -> str:
    if not documents:
        return "No reference documents were provided."

    parts = []
    for document in documents:
        content = (document.content or "")[:2500]
        parts.append(
            f"DOCUMENT ID: {document.id}\n"
            f"TITLE: {document.title}\n"
            f"TYPE: {getattr(document, 'document_type', None) or 'unknown'}\n"
            f"CONTENT:\n{content}"
        )
    return "\n\n---\n\n".join(parts)


def _build_user_prompt(
    request: AssessmentGenerateRequest,
    documents: list[Document],
) -> str:
    type_list = ", ".join(request.question_types) or "mcq, short_answer, scenario"
    return f"""
Generate a skill-check assessment.

NEWCOMER ROLE CONTEXT:
Job title: {request.job_title or "unknown"}
Seniority: {request.seniority or "unknown"}
Team: {request.team or "unknown"}
Known skills (mentor input): {request.known_skills or "n/a"}
Known gaps (mentor input): {request.known_gaps or "n/a"}
Additional role context: {request.role_context or "n/a"}

MENTOR NOTES (steer the questions toward what the mentor wants to check):
{request.mentor_notes or "No mentor notes."}

REFERENCE MATERIALS (use these to ground question content):
{_build_documents_context(documents)}

CONSTRAINTS:
- Exactly {request.question_count} questions.
- Mix question_type only from: {type_list}.
- Roughly balance the mix unless the mentor notes ask otherwise.
- Each MCQ option needs a stable id (e.g., "a", "b", "c", "d").
- For short_answer and scenario, fill expected_answer with a reasonable model answer (the evaluator uses it).
- Vary difficulty (easy/medium/hard) to calibrate the level.
- Tag every question with a useful skill_tag.

Return JSON matching the schema.
""".strip()


def _build_fallback_assessment(request: AssessmentGenerateRequest) -> AIAssessmentOutput:
    role = request.job_title or "team member"
    questions: list[AIAssessmentQuestionOutput] = [
        AIAssessmentQuestionOutput(
            question_type="mcq",
            prompt=f"As a {role}, what's the best first step when you join a new team?",
            options=[
                AIAssessmentOptionOutput(id="a", label="Start coding immediately on a small task to feel productive.", is_correct=False),
                AIAssessmentOptionOutput(id="b", label="Read team docs and meet your manager / mentor to align on expectations.", is_correct=True),
                AIAssessmentOptionOutput(id="c", label="Refactor an old module to leave a mark.", is_correct=False),
                AIAssessmentOptionOutput(id="d", label="Wait for someone to assign you work.", is_correct=False),
            ],
            expected_answer=None,
            skill_tag="onboarding-attitude",
            difficulty="easy",
        ),
        AIAssessmentQuestionOutput(
            question_type="short_answer",
            prompt="In one or two sentences, describe how you'd ask for help when blocked on a task.",
            expected_answer="Briefly describe the goal, what you tried, where you got stuck, and what hypothesis you have, then ping the right person/channel.",
            skill_tag="team-communication",
            difficulty="easy",
        ),
        AIAssessmentQuestionOutput(
            question_type="scenario",
            prompt=f"You're a {role}. Two senior teammates give you conflicting advice on how to solve a problem. What do you do?",
            expected_answer="Acknowledge both inputs, summarize them back to confirm, surface the conflict openly, ask for the decision criteria, and propose a small experiment if needed.",
            skill_tag="judgment",
            difficulty="medium",
        ),
        AIAssessmentQuestionOutput(
            question_type="mcq",
            prompt="When reading a new codebase for the first time, what's the most efficient strategy?",
            options=[
                AIAssessmentOptionOutput(id="a", label="Read every file from A to Z.", is_correct=False),
                AIAssessmentOptionOutput(id="b", label="Pick a user-facing flow and trace it end-to-end.", is_correct=True),
                AIAssessmentOptionOutput(id="c", label="Only look at tests.", is_correct=False),
                AIAssessmentOptionOutput(id="d", label="Rewrite the parts you don't understand.", is_correct=False),
            ],
            expected_answer=None,
            skill_tag="codebase-navigation",
            difficulty="medium",
        ),
        AIAssessmentQuestionOutput(
            question_type="short_answer",
            prompt="What's one question you'd ask your mentor in your first 1:1?",
            expected_answer="Should reveal curiosity about the team's priorities, the mentor's expectations, or success criteria for the first weeks.",
            skill_tag="growth-mindset",
            difficulty="easy",
        ),
        AIAssessmentQuestionOutput(
            question_type="scenario",
            prompt="You notice a bug in production on day 3. You're not sure if it's serious. How do you proceed?",
            expected_answer="Reproduce quickly, capture evidence (logs/screenshot), flag it to mentor/oncall promptly with severity guess, do not silently fix in prod.",
            skill_tag="incident-handling",
            difficulty="medium",
        ),
    ]

    # Trim or pad to the requested count
    if len(questions) > request.question_count:
        questions = questions[: request.question_count]
    else:
        while len(questions) < request.question_count:
            questions.append(questions[len(questions) % 6])

    return AIAssessmentOutput(
        title=f"Skill check for {role}",
        questions=questions,
    )


def generate_assessment_with_ai(
    request: AssessmentGenerateRequest,
    documents: list[Document],
) -> AIAssessmentServiceResult:
    user_prompt = _build_user_prompt(request, documents)
    schema = AIAssessmentOutput.model_json_schema()

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "skill_assessment",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        raw_output = response.output_text
        parsed = json.loads(raw_output)
        output = AIAssessmentOutput.model_validate(parsed)
        _normalize_output(output)
        return AIAssessmentServiceResult(output=output, used_fallback=False)

    except (ValidationError, json.JSONDecodeError, Exception):
        return AIAssessmentServiceResult(
            output=_build_fallback_assessment(request),
            used_fallback=True,
        )


def _normalize_output(output: AIAssessmentOutput) -> None:
    for q in output.questions:
        if q.question_type == "mcq":
            if not q.options:
                # Ensure at least 2 options exist for an MCQ; downgrade type otherwise
                q.question_type = "short_answer"
                q.options = None
                continue
            # Make sure exactly one correct answer is flagged
            correct_count = sum(1 for o in q.options if o.is_correct)
            if correct_count == 0:
                q.options[0].is_correct = True
            elif correct_count > 1:
                # Keep first as correct, mark others false
                seen = False
                for o in q.options:
                    if o.is_correct and not seen:
                        seen = True
                    else:
                        o.is_correct = False
            # Stable IDs if missing
            for idx, o in enumerate(q.options):
                if not o.id:
                    o.id = chr(ord("a") + idx)
        else:
            q.options = None


def regenerate_single_question(
    request: AssessmentGenerateRequest,
    documents: list[Document],
) -> AIAssessmentQuestionOutput:
    """Generate a single replacement question. Reuses the generator with count=1."""
    single_request = request.model_copy(update={"question_count": 1})
    result = generate_assessment_with_ai(single_request, documents)
    return result.output.questions[0]


# ---------- Persistence helpers ----------

def persist_generated_assessment(
    db: Session,
    request: AssessmentGenerateRequest,
    result: AIAssessmentServiceResult,
) -> Assessment:
    assessment = Assessment(
        newcomer_id=request.newcomer_id,
        mentor_id=request.mentor_id,
        title=result.output.title,
        status="draft",
        mentor_notes=request.mentor_notes,
        role_context=request.role_context,
        source_document_ids=list(request.document_ids) if request.document_ids else None,
        generated_by_ai=True,
        used_fallback=result.used_fallback,
    )
    db.add(assessment)
    db.flush()

    for idx, q in enumerate(result.output.questions):
        options_json = None
        if q.options:
            options_json = [o.model_dump() for o in q.options]
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

    db.commit()
    db.refresh(assessment)
    return assessment


# ---------- Evaluation ----------

EVAL_SYSTEM_PROMPT = """
You evaluate a candidate's free-form answer against an expected model answer.
Return a JSON object:
{
  "score": float in [0, 1],
  "feedback": "one to two short sentences, constructive, candid"
}
Score 1.0 = excellent / matches model; 0.7 = solid; 0.5 = partial; 0.3 = weak; 0.0 = wrong or empty.
""".strip()


def _evaluate_free_answer(prompt: str, expected: str | None, answer: str | None) -> dict:
    if not answer:
        return {"score": 0.0, "feedback": "No answer provided."}
    if not expected:
        return {"score": 0.5, "feedback": "Answer recorded for mentor review."}

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"QUESTION:\n{prompt}\n\nEXPECTED ANSWER:\n{expected}\n\n"
                        f"CANDIDATE ANSWER:\n{answer}"
                    ),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "answer_evaluation",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "feedback": {"type": "string"},
                        },
                        "required": ["score", "feedback"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            },
        )
        parsed = json.loads(response.output_text)
        score = max(0.0, min(1.0, float(parsed.get("score", 0.5))))
        feedback = str(parsed.get("feedback", ""))[:600]
        return {"score": score, "feedback": feedback}
    except Exception:
        return {"score": 0.5, "feedback": "AI evaluation unavailable; mentor review recommended."}


def _score_mcq(question: AssessmentQuestion, selected_ids: list[str] | None) -> dict:
    if not question.options:
        return {"score": 0.0, "feedback": "Question had no options."}
    correct_ids = {o["id"] for o in question.options if o.get("is_correct")}
    selected = set(selected_ids or [])
    if not selected:
        return {"score": 0.0, "feedback": "No option selected."}
    if selected == correct_ids:
        return {"score": 1.0, "feedback": "Correct."}
    if selected & correct_ids:
        return {"score": 0.5, "feedback": "Partially correct."}
    return {"score": 0.0, "feedback": "Incorrect."}


def evaluate_submission_with_ai(db: Session, submission_id: int) -> dict:
    submission = (
        db.query(AssessmentSubmission)
        .filter(AssessmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        return {"ok": False, "reason": "submission_not_found"}

    answers = (
        db.query(AssessmentAnswer)
        .filter(AssessmentAnswer.submission_id == submission_id)
        .all()
    )

    total = 0.0
    count = 0
    weakest_tags: dict[str, list[float]] = {}

    for answer in answers:
        question = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.id == answer.question_id)
            .first()
        )
        if not question:
            continue

        if question.question_type == "mcq":
            result = _score_mcq(question, answer.selected_option_ids)
        else:
            result = _evaluate_free_answer(
                question.prompt, question.expected_answer, answer.answer_text
            )

        answer.ai_score = result["score"]
        answer.ai_feedback = result["feedback"]

        total += result["score"]
        count += 1

        tag = question.skill_tag or "general"
        weakest_tags.setdefault(tag, []).append(result["score"])

    if count > 0:
        overall = total / count
        submission.overall_score = overall

        gap_tags = sorted(
            [(tag, sum(scores) / len(scores)) for tag, scores in weakest_tags.items()],
            key=lambda x: x[1],
        )[:3]
        summary_lines = [
            f"Overall score: {overall:.0%} ({count} questions)."
        ]
        if gap_tags:
            summary_lines.append(
                "Weakest areas: "
                + ", ".join(f"{tag} ({score:.0%})" for tag, score in gap_tags)
            )
        submission.summary = " ".join(summary_lines)
    else:
        submission.overall_score = 0.0
        submission.summary = "No answers to evaluate."

    # Mark assessment as evaluated
    assessment = (
        db.query(Assessment).filter(Assessment.id == submission.assessment_id).first()
    )
    if assessment:
        assessment.status = "evaluated"

    db.commit()
    return {"ok": True, "overall_score": submission.overall_score}


def build_plan_context_from_submission(db: Session, submission_id: int) -> str:
    """Plain-text summary the plan generator can consume as mentor_notes."""
    submission = (
        db.query(AssessmentSubmission)
        .filter(AssessmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        return ""

    answers = (
        db.query(AssessmentAnswer)
        .filter(AssessmentAnswer.submission_id == submission_id)
        .all()
    )

    lines = [
        "Skill assessment results (use these to calibrate the onboarding plan):",
        submission.summary or "No summary.",
        "",
        "Per-question results:",
    ]
    for ans in answers:
        question = (
            db.query(AssessmentQuestion)
            .filter(AssessmentQuestion.id == ans.question_id)
            .first()
        )
        if not question:
            continue
        score = ans.ai_score if ans.ai_score is not None else 0.0
        tag = question.skill_tag or "general"
        lines.append(
            f"- [{tag}] {question.prompt[:100]} -> score {score:.0%}"
        )

    return "\n".join(lines)


# ---------- Helpers shared with routes ----------

def make_option_id() -> str:
    return uuid.uuid4().hex[:6]
