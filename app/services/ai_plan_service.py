import json
import httpx
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.schemas.ai_plan import AIPlanOutput, AIPlanTaskOutput, AIPlanServiceResult

http_client = httpx.Client(verify=False)
client = OpenAI(http_client=http_client, api_key=settings.OPENAI_API_KEY)



ALLOWED_TASK_TYPES = {
    "read_doc",
    "setup",
    "meet_person",
    "first_task",
    "ask_ai",
    "checkpoint",
    "hr_process",
    "technical_practice",
    "general",
}

ALLOWED_PRIORITIES = {
    "low",
    "medium",
    "high",
}


def load_prompt_template() -> str:
    prompt_path = Path("app/prompts/plan_generation.txt")
    return prompt_path.read_text(encoding="utf-8")


def build_documents_context(documents: list[Document]) -> str:
    if not documents:
        return "No documents were provided."

    parts = []

    for document in documents:
        content = document.content or ""
        trimmed_content = content[:3000]

        parts.append(
            f"""
DOCUMENT ID: {document.id}
TITLE: {document.title}
TYPE: {getattr(document, "document_type", None) or "unknown"}
SOURCE: {document.source or "manual"}
CONTENT:
{trimmed_content}
"""
        )

    return "\n\n---\n\n".join(parts)


def build_newcomer_context(newcomer: NewcomerProfile) -> str:
    user = newcomer.user

    return f"""
NEWCOMER PROFILE:
Name: {user.full_name if user else "Unknown"}
Email: {user.email if user else "Unknown"}
Job title: {newcomer.job_title}
Seniority: {newcomer.seniority}
Team: {newcomer.team}
Start date: {newcomer.start_date}
Current onboarding status: {newcomer.onboarding_status}
"""


def normalize_ai_plan(plan: AIPlanOutput) -> AIPlanOutput:
    """
    Defensive normalization.
    Even with structured outputs, we keep backend-level safeguards.
    """

    normalized_tasks = []

    for task in plan.tasks:
        task_type = task.task_type

        if task_type not in ALLOWED_TASK_TYPES:
            task_type = "general"

        priority = task.priority

        if priority not in ALLOWED_PRIORITIES:
            priority = "medium"

        task.task_type = task_type
        task.priority = priority

        normalized_tasks.append(task)

    plan.tasks = normalized_tasks

    return plan


def build_fallback_plan(newcomer: NewcomerProfile) -> AIPlanOutput:
    """
    Fallback used if the LLM fails.
    This keeps the demo stable.
    """

    return AIPlanOutput(
        title=f"30/60/90-day Onboarding Plan for {newcomer.job_title}",
        description=(
            f"Structured onboarding plan for a {newcomer.seniority} "
            f"{newcomer.job_title} joining the {newcomer.team} team."
        ),
        plan_summary=(
            "This plan helps the newcomer understand the company context, "
            "team processes, technical environment, and progressively reach autonomy."
        ),
        first_30_days_goal="Understand the team, setup the environment, and complete a first guided task.",
        days_31_60_goal="Contribute to real project work with mentor support.",
        days_61_90_goal="Reach operational autonomy and own a small workstream.",
        mentor_focus="Provide targeted support, validate understanding, and remove blockers early.",
        newcomer_focus="Learn the project context step by step and ask questions when blocked.",
        risk_areas=[
            "Information overload during the first week",
            "Unclear technical setup",
            "Not asking questions when blocked",
            "Difficulty understanding team-specific processes",
        ],
        tasks=[
            AIPlanTaskOutput(
                title="Set up local development environment",
                description="Install project dependencies, configure environment variables, and run the backend locally.",
                week_number=1,
                day_number=1,
                task_type="setup",
                priority="high",
                success_criteria="The newcomer can run the project locally without mentor help.",
            ),
            AIPlanTaskOutput(
                title="Read team and project overview",
                description="Read the main project documentation and identify the key product flows.",
                week_number=1,
                day_number=2,
                task_type="read_doc",
                priority="high",
                success_criteria="The newcomer can explain what the team owns and how the product works.",
            ),
            AIPlanTaskOutput(
                title="Mentor codebase walkthrough",
                description="Schedule a walkthrough with the mentor to understand the main modules and conventions.",
                week_number=1,
                day_number=3,
                task_type="meet_person",
                priority="medium",
                success_criteria="The newcomer knows where the main services, models, and routes are located.",
            ),
            AIPlanTaskOutput(
                title="Complete first small task",
                description="Pick a low-risk task and open the first pull request.",
                week_number=2,
                day_number=1,
                task_type="first_task",
                priority="high",
                success_criteria="The newcomer opens a first PR and receives review feedback.",
            ),
            AIPlanTaskOutput(
                title="First checkpoint with mentor",
                description="Review what is clear, what is confusing, and what should be adapted in the plan.",
                week_number=2,
                day_number=5,
                task_type="checkpoint",
                priority="medium",
                success_criteria="The mentor identifies at least one strength and one gap.",
            ),
        ],
    )


def generate_onboarding_plan_with_ai(
    newcomer: NewcomerProfile,
    documents: list[Document],
    mentor_notes: str | None = None,
) -> AIPlanServiceResult:
    system_prompt = load_prompt_template()
    newcomer_context = build_newcomer_context(newcomer)
    documents_context = build_documents_context(documents)

    user_prompt = f"""
Generate a 30/60/90-day onboarding plan.

{newcomer_context}

MENTOR NOTES:
{mentor_notes or "No mentor notes provided."}

AVAILABLE COMPANY / TEAM DOCUMENTS:
{documents_context}

TASK TYPES ALLOWED:
- read_doc
- setup
- meet_person
- first_task
- ask_ai
- checkpoint
- hr_process
- technical_practice
- general

PRIORITY VALUES ALLOWED:
- low
- medium
- high

Generate 10 to 18 tasks.
Make the first week very concrete.
Make the plan useful for a mentor dashboard and a newcomer dashboard.
"""

    schema = AIPlanOutput.model_json_schema()

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "onboarding_plan",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        raw_output = response.output_text
        parsed = json.loads(raw_output)
        plan = AIPlanOutput.model_validate(parsed)

        return AIPlanServiceResult(plan=normalize_ai_plan(plan), used_fallback=False)

    except (ValidationError, json.JSONDecodeError, Exception):
        return  AIPlanServiceResult(
                    plan=build_fallback_plan(newcomer),
                    used_fallback=True,
                )