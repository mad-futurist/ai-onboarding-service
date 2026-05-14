from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.models.blocked_report import BlockedReport
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_task import OnboardingTask
from app.services.llm_service import generate_answer


def draft_mentor_message(
    db: Session,
    newcomer_id: int,
    signal_id: int | None = None,
    blocked_report_id: int | None = None,
    tone: str = "supportive",
) -> dict:
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )
    if not newcomer:
        raise ValueError("Newcomer not found")

    newcomer_name = newcomer.user.full_name if newcomer.user else f"Newcomer #{newcomer_id}"

    signal = None
    signal_title = None
    signal_context = ""

    if signal_id:
        signal = db.query(AISignal).filter(AISignal.id == signal_id).first()
        if signal:
            signal_title = signal.title
            signal_context = (
                f"Context: {signal.description}\n"
                f"Evidence: {signal.evidence}\n"
                f"Suggested action: {signal.suggested_action}"
            )

    if blocked_report_id:
        report = (
            db.query(BlockedReport)
            .filter(
                BlockedReport.id == blocked_report_id,
                BlockedReport.newcomer_id == newcomer_id,
            )
            .first()
        )
        if report:
            task = None
            if report.task_id:
                task = db.query(OnboardingTask).filter(OnboardingTask.id == report.task_id).first()
            signal_title = f"Blocked: {task.title if task else report.blocker_type.replace('_', ' ')}"
            signal_context = (
                f"Context: The newcomer reported a blocker of type {report.blocker_type}.\n"
                f"Task: {task.title if task else 'General blocker'}\n"
                f"Comment: {report.details or 'No extra comment'}\n"
                f"Suggested action: {report.ai_suggestion or 'Offer help and clarify the next step.'}"
            )

    tone_instructions = {
        "supportive": "warm and encouraging, showing empathy",
        "direct": "clear and direct, focused on next steps",
        "casual": "friendly and informal, like a colleague",
    }
    tone_desc = tone_instructions.get(tone, "warm and encouraging")

    prompt = (
        f"Write a short Slack message from a tech lead mentor to {newcomer_name}, "
        f"a newcomer in the team. The tone should be {tone_desc}.\n"
    )
    if signal_context:
        prompt += f"\n{signal_context}\n"
    prompt += (
        "\nThe message should:\n"
        "- Not feel like a performance review\n"
        "- Offer help or suggest a short meeting\n"
        "- Be 2-3 sentences maximum\n"
        "- Feel human and personal\n"
        "\nMessage:"
    )

    message = generate_answer(prompt)

    return {
        "message": message.strip(),
        "newcomer_name": newcomer_name,
        "signal_title": signal_title,
    }
