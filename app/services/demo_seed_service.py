from sqlalchemy.orm import Session

from app.models.ai_question import AIQuestion, AIQuestionSource
from app.models.ai_signal import AISignal
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_event import OnboardingEvent
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.person_contact import PersonContact
from app.models.plan_adjustment import PlanAdjustmentSuggestion
from app.models.user import User
from app.services.rag_service import generate_chunks_for_document


DOCUMENTS = [
    {
        "title": "Company Handbook",
        "content": (
            "Welcome to TechCorp! This handbook covers our culture, values, and key policies.\n\n"
            "Core values: ownership, collaboration, continuous learning.\n\n"
            "Working hours: flexible, core hours 10:00-16:00.\n\n"
            "Communication: Slack for async, Google Meet for sync. Always default to async.\n\n"
            "Vacation policy: 20 days/year, request via HR portal at least 2 weeks in advance.\n\n"
            "Sick leave: notify your manager and HR same day. No limit for genuine illness.\n\n"
            "Pointage: log hours in Jira daily, submit weekly timesheet by Friday 17:00."
        ),
        "source": "HR",
        "document_type": "handbook",
        "domain": "hr",
        "role_target": "all",
        "scope": "enterprise",
    },
    {
        "title": "Payments Team Architecture Overview",
        "content": (
            "The Payments team owns the payment processing microservices.\n\n"
            "Main services: payment-gateway, fraud-detection, settlement-service, reconciliation-service.\n\n"
            "Tech stack: Python (FastAPI), PostgreSQL, Redis, Kafka.\n\n"
            "All services communicate via Kafka events. REST APIs are only for external clients.\n\n"
            "Deployment: Kubernetes on AWS EKS. Each service has its own Docker image.\n\n"
            "Code review: minimum 2 approvals required. Tech lead approval mandatory for payment-gateway changes.\n\n"
            "On-call: rotating weekly. See PagerDuty for current on-call schedule."
        ),
        "source": "Engineering",
        "document_type": "architecture",
        "domain": "technical",
        "role_target": "backend_developer",
        "scope": "team",
    },
    {
        "title": "Deployment Guide",
        "content": (
            "How to deploy to staging and production.\n\n"
            "Step 1: Merge PR after 2 approvals.\n"
            "Step 2: CI pipeline runs automatically. Check GitHub Actions for status.\n"
            "Step 3: After CI passes, staging deploy triggers automatically.\n"
            "Step 4: Verify your changes on staging.payments.techcorp.internal\n"
            "Step 5: For production deploy, post in #deploys: 'Deploying payment-gateway v1.2.3'\n"
            "Step 6: Run: kubectl rollout status deployment/payment-gateway -n payments\n"
            "Step 7: Monitor Grafana dashboard for 15 minutes after production deploy.\n"
            "Step 8: If issues arise, rollback: kubectl rollout undo deployment/payment-gateway -n payments\n\n"
            "Contacts: Victor (DevOps) for infrastructure issues, Marko (Tech Lead) for release approval."
        ),
        "source": "Engineering",
        "document_type": "guide",
        "domain": "technical",
        "role_target": "backend_developer",
        "scope": "team",
    },
    {
        "title": "Code Review Checklist",
        "content": (
            "Before opening a PR:\n"
            "[ ] All tests pass locally\n"
            "[ ] No print/debug statements left\n"
            "[ ] New code has unit tests\n"
            "[ ] API changes are documented in OpenAPI spec\n"
            "[ ] Database migrations are reversible\n\n"
            "PR description must include:\n"
            "- What this PR does\n"
            "- How to test it\n"
            "- Link to Jira ticket\n\n"
            "Review process:\n"
            "1. Author posts PR in #payments-reviews Slack channel\n"
            "2. Reviewers have 24h to review\n"
            "3. Address all comments before merging\n"
            "4. Tech lead approves last for payment-critical changes"
        ),
        "source": "Engineering",
        "document_type": "checklist",
        "domain": "technical",
        "role_target": "backend_developer",
        "scope": "team",
    },
    {
        "title": "Jira Workflow Guide",
        "content": (
            "How we use Jira in the Payments team.\n\n"
            "Ticket statuses: Backlog → To Do → In Progress → In Review → Done\n\n"
            "Sprint planning: every 2 weeks on Monday.\n\n"
            "Daily standup: async in #payments-standup Slack, post by 10:00.\n\n"
            "Story points: 1=hours, 2=half day, 3=1 day, 5=2-3 days, 8=week.\n\n"
            "When taking a ticket: assign to yourself and move to In Progress.\n"
            "When opening PR: move ticket to In Review and link PR.\n"
            "When merged: move ticket to Done.\n\n"
            "Bug reports: use the Bug template in Jira. Add reproduction steps and logs."
        ),
        "source": "Engineering",
        "document_type": "guide",
        "domain": "process",
        "role_target": "all",
        "scope": "team",
    },
]

PEOPLE = [
    {"full_name": "Marko Ivanov", "role": "Tech Lead", "team": "Payments", "email": "marko@techcorp.com", "topics": ["code_review", "architecture", "deployment", "release_approval"]},
    {"full_name": "Victor Petrenko", "role": "DevOps Engineer", "team": "Infrastructure", "email": "victor@techcorp.com", "topics": ["deployment", "kubernetes", "docker", "infrastructure", "staging"]},
    {"full_name": "Julia Kovalenko", "role": "HR Manager", "team": "HR", "email": "julia@techcorp.com", "topics": ["hr_process", "vacation", "pointage", "sick_leave", "onboarding"]},
    {"full_name": "Ana Shevchenko", "role": "QA Engineer", "team": "Payments", "email": "ana@techcorp.com", "topics": ["testing", "qa", "test_automation", "bug_reporting"]},
]

PLAN_TASKS = [
    # Week 1
    {"title": "Set up local development environment", "description": "Clone repos, install dependencies, run the app locally", "week_number": 1, "task_type": "setup", "priority": "high", "status": "done"},
    {"title": "Read Payments architecture overview", "description": "Understand the main services, tech stack, and data flow", "week_number": 1, "task_type": "reading", "priority": "high", "status": "done"},
    {"title": "Join Slack channels and Jira", "description": "#payments, #deploys, #payments-reviews, #payments-standup", "week_number": 1, "task_type": "access", "priority": "high", "status": "done"},
    {"title": "Meet Marko Ivanov (Tech Lead)", "description": "30-min intro meeting to understand team priorities", "week_number": 1, "task_type": "meeting", "priority": "medium", "status": "done"},
    {"title": "Read Company Handbook", "description": "HR policies, vacation, pointage, values", "week_number": 1, "task_type": "reading", "priority": "medium", "status": "done"},
    # Week 2
    {"title": "Read Code Review Checklist", "description": "Understand PR expectations before opening first PR", "week_number": 2, "task_type": "reading", "priority": "high", "status": "done"},
    {"title": "Pick first backend ticket from Jira", "description": "Good-first-issue in the payment-gateway service", "week_number": 2, "task_type": "development", "priority": "high", "status": "in_progress"},
    {"title": "Open first PR", "description": "Fix or small feature in payment-gateway", "week_number": 2, "task_type": "development", "priority": "high", "status": "in_progress"},
    {"title": "Understand deployment flow", "description": "Read deployment guide, understand staging and production process", "week_number": 2, "task_type": "deployment", "priority": "high", "status": "blocked"},
    {"title": "Shadow a production deployment", "description": "Watch Victor or Marko do a real deploy", "week_number": 2, "task_type": "deployment", "priority": "medium", "status": "todo"},
]

AI_QUESTIONS = [
    {"question": "How do I deploy my changes to staging?", "answer": "To deploy to staging: 1) Merge your PR after 2 approvals. 2) CI pipeline triggers automatically. 3) After CI passes, staging deploys automatically to staging.payments.techcorp.internal. 4) Verify your changes there. For more details, see the Deployment Guide."},
    {"question": "Who approves the production deployment?", "answer": "Production deployments require notification in the #deploys Slack channel. Marko Ivanov (Tech Lead) gives final approval for payment-gateway changes. Victor Petrenko (DevOps) handles the infrastructure side."},
    {"question": "What is the rollback process if something goes wrong after deploy?", "answer": "If issues arise after a production deploy, run: kubectl rollout undo deployment/payment-gateway -n payments. Then monitor the Grafana dashboard and notify the team in #deploys. Victor (DevOps) can assist with infrastructure issues."},
    {"question": "How do I check if the staging pipeline passed?", "answer": "Check GitHub Actions in your PR for CI/CD status. The staging deploy is automatic after CI passes. You can verify on staging.payments.techcorp.internal. If the pipeline is red, check the Actions logs for the failing step."},
]


def seed_demo_data(db: Session) -> dict:
    existing_mentor = db.query(User).filter(User.email == "marko@techcorp.com").first()
    if existing_mentor:
        return {"already_seeded": True, "mentor_id": existing_mentor.id}

    # 1. Users
    mentor = User(email="marko@techcorp.com", full_name="Marko Ivanov", role="mentor")
    newcomer_user = User(email="tanya@techcorp.com", full_name="Tanya Petrova", role="newcomer")
    db.add_all([mentor, newcomer_user])
    db.flush()

    # 2. NewcomerProfile
    from datetime import date, timedelta
    start_date = date.today() - timedelta(days=12)
    newcomer = NewcomerProfile(
        user_id=newcomer_user.id,
        mentor_id=mentor.id,
        job_title="Backend Developer",
        seniority="middle",
        team="Payments",
        start_date=start_date,
        onboarding_status="active",
    )
    db.add(newcomer)
    db.flush()

    # 3. People contacts
    for p in PEOPLE:
        existing = db.query(PersonContact).filter(PersonContact.email == p["email"]).first()
        if not existing:
            contact = PersonContact(**p)
            db.add(contact)
    db.flush()

    # 4. Documents
    created_docs = []
    for doc_data in DOCUMENTS:
        doc = Document(**doc_data)
        db.add(doc)
        db.flush()
        created_docs.append(doc)
        try:
            generate_chunks_for_document(db=db, document=doc)
        except Exception:
            pass

    # 5. Plan
    plan = OnboardingPlan(
        newcomer_id=newcomer.id,
        mentor_id=mentor.id,
        title="Tanya Petrova — Backend Developer Onboarding (Payments)",
        description="30/60/90-day onboarding plan for backend developer joining the Payments team.",
        status="active",
        generated_by_ai=True,
        mentor_approved=True,
    )
    db.add(plan)
    db.flush()

    # 6. Tasks
    created_tasks = []
    for t in PLAN_TASKS:
        task = OnboardingTask(
            plan_id=plan.id,
            title=t["title"],
            description=t["description"],
            week_number=t["week_number"],
            task_type=t["task_type"],
            priority=t["priority"],
            status=t["status"],
        )
        db.add(task)
        db.flush()
        created_tasks.append(task)

        db.add(OnboardingEvent(
            newcomer_id=newcomer.id,
            user_id=newcomer_user.id,
            event_type="task_status_changed",
            entity_type="onboarding_task",
            entity_id=task.id,
            topic=t["task_type"],
            metadata_json={"task_title": t["title"], "status": t["status"]},
        ))

    # 7. AI Questions
    deployment_doc = next((d for d in created_docs if "Deployment" in d.title), None)
    created_questions = []
    for q_data in AI_QUESTIONS:
        q = AIQuestion(
            user_id=newcomer_user.id,
            newcomer_id=newcomer.id,
            question=q_data["question"],
            answer=q_data["answer"],
            status="answered",
        )
        db.add(q)
        db.flush()
        created_questions.append(q)

        db.add(OnboardingEvent(
            newcomer_id=newcomer.id,
            user_id=newcomer_user.id,
            event_type="ai_question_asked",
            entity_type="ai_question",
            entity_id=q.id,
            topic="deployment",
        ))

        if deployment_doc:
            source = AIQuestionSource(
                question_id=q.id,
                document_id=deployment_doc.id,
                chunk_id=1,
                title=deployment_doc.title,
                content_preview=deployment_doc.content[:200],
                similarity=0.85,
            )
            db.add(source)

    # 8. AI Signal
    signal = AISignal(
        newcomer_id=newcomer.id,
        signal_type="deployment_confusion",
        severity="high",
        confidence=0.88,
        score=0.82,
        title="Possible deployment process confusion",
        description=(
            "Tanya asked 4 questions related to deployment, staging, and release flow. "
            "The deployment task is currently blocked. This may indicate friction before first production deploy."
        ),
        evidence=(
            "- 4 questions related to deployment/release/staging.\n"
            "- Question: \"How do I deploy my changes to staging?\"\n"
            "- Question: \"Who approves the production deployment?\"\n"
            "- 1 deployment-related task is blocked: \"Understand deployment flow\"\n"
            "- Source 'Deployment Guide' used 4 times."
        ),
        suggested_action=(
            "Schedule a 15-minute deployment walkthrough with Victor (DevOps) before first production deploy. "
            "Focus on staging pipeline, release approval, rollback, and post-deploy monitoring."
        ),
        status="open",
        occurrence_count=4,
    )
    db.add(signal)
    db.flush()

    # 9. Plan Adjustment
    adjustment = PlanAdjustmentSuggestion(
        newcomer_id=newcomer.id,
        plan_id=plan.id,
        signal_id=signal.id,
        title="Adapt Week 2: Add deployment practice",
        reason=(
            "Tanya shows strong progress in API and SQL work but has friction with deployment. "
            "Reducing reading tasks and adding hands-on deployment practice will unblock her."
        ),
        suggested_changes=[
            {"action": "add", "title": "Deployment pairing session with Victor", "task_type": "deployment", "week_number": 2, "priority": "high"},
            {"action": "add", "title": "Staging deploy simulation", "task_type": "deployment", "week_number": 2, "priority": "high"},
            {"action": "modify", "title": "Move first production deploy milestone by 3 days", "task_type": "deployment", "week_number": 3},
        ],
        status="pending",
    )
    db.add(adjustment)

    db.commit()

    return {
        "mentor_id": mentor.id,
        "newcomer_id": newcomer.id,
        "newcomer_user_id": newcomer_user.id,
        "plan_id": plan.id,
        "signal_id": signal.id,
        "documents_created": len(created_docs),
        "tasks_created": len(created_tasks),
        "questions_created": len(created_questions),
    }
