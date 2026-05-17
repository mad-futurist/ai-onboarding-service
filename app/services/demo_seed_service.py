from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.ai_answer_feedback import AIAnswerFeedback
from app.models.ai_conversation import AIConversation
from app.models.ai_question import AIQuestion, AIQuestionSource
from app.models.ai_signal import AISignal
from app.models.ai_signal_feedback import AISignalFeedback
from app.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentQuestion,
    AssessmentSubmission,
)
from app.models.blocked_report import BlockedReport
from app.models.company_onboarding_gap import CompanyOnboardingGap
from app.models.course import Course
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.lesson import Lesson
from app.models.lesson_note import LessonNote
from app.models.mentor_digest import MentorDigest
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_event import OnboardingEvent
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_reflection import OnboardingReflection
from app.models.onboarding_task import OnboardingTask
from app.models.person_contact import NewcomerRecommendedContact, PersonContact
from app.models.plan_adjustment import PlanAdjustmentSuggestion
from app.models.progress_snapshot import ProgressSnapshot
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.sprint import Sprint
from app.models.user import User
from app.models.week import Week
from app.services.rag_service import generate_chunks_for_document


SALES_REGULATION = """
Регламент роботи відділу продажів у 2026 році.

Мета процесу: перетворити холодного ліда у платного клієнта через структурований
цикл продажів із залученням маркетолога та спеціалістів.

Етап 1 — Лідогенерація та первинний контакт:
- менеджер здійснює холодні контакти відповідно до KPI;
- визначає, чи лід контактний та релевантний;
- якщо лід зацікавлений, пропонує короткий дзвінок-опитування на 15-20 хв.

Етап 2 — Діагностичний дзвінок:
- провести коротке інтерв'ю;
- зібрати бриф: цілі, стан бізнесу, бюджет, проблеми;
- визначити потенціал клієнта;
- систематизувати інформацію і передати маркетологу.

Етап 3 — Комерційна пропозиція:
- маркетолог або CEO Аня разом із профільним спеціалістом аналізує бриф;
- команда формує структуру рішення, пакет послуг, ціну і КП;
- менеджер отримує готову пропозицію для презентації.

Етап 4 — Презентація КП:
- менеджер домовляється про зідзвон і веде зустріч;
- маркетолог або спеціаліст підстраховує технічні питання;
- менеджер фіксує реакції, питання, заперечення і наступний крок.

Етап 5 — Закриття угоди:
- довести клієнта до фінального рішення;
- уточнити остаточні умови і вартість;
- передати дані для договору і рахунку;
- контролювати підписання договору і оплату. Оплату підтверджує CEO Аня.

Етап 6 — Передача в продакшн:
- організувати стартову зустріч з клієнтом, PM, маркетологом і спеціалістом;
- фіналізувати очікування, задачі, дедлайни і відповідальних.

KPI активності на день:
- Facebook: 25-30 повідомлень;
- Instagram: 25-30 повідомлень;
- Freelancehunt: 10-15 контактів;
- LinkedIn: 5-8 контактів;
- Telegram: 8-10 контактів;
- Email: 10-15 листів;
- 20-30 активних діалогів на день;
- 6-10 дзвінків на тиждень;
- 4+ заповнених брифів на тиждень;
- 4-6 КП або презентацій на тиждень.

KPI результату на місяць:
- мінімум 2 угоди;
- 3-4 угоди — нормальний результат;
- 5+ угод — відмінний результат;
- конверсія з брифу в угоду не нижче 20-30%.

Звітність:
- щоденний звіт: повідомлення по каналах, відповіді, активні діалоги;
- щотижневий звіт: дзвінки, брифи, презентації, КП, угоди.
""".strip()


SALES_SKILLS = """
Що має вміти менеджер з продажів.

Менеджер повинен розуміти повний цикл продажу: пошук потенційних клієнтів,
переговори, укладання угоди, підтримка довгострокових відносин.

Hard skills:
- холодні дзвінки, email-маркетинг, воронка продажів;
- знання послуг агентства: SMM, таргетована реклама Meta/TikTok/LinkedIn,
  Google Ads, дизайн;
- техніки SPIN, AIDA, робота із запереченнями;
- CAC, ROI, конверсія, середній чек, LTV;
- Google Analytics, Data Studio, Excel;
- комерційні пропозиції і фінальні звіти;
- прогнозування доходів і маржинальності;
- LinkedIn Sales Navigator, Hunter.io та інші платформи;
- переговори, договори, складні ситуації.

Soft skills:
- тайм-менеджмент і багатозадачність;
- переконання і переговори;
- просте пояснення складних речей;
- вирішення конфліктів;
- емпатія до клієнтів та колег;
- стресостійкість;
- адаптація до змін;
- креативність у залученні клієнтів.
""".strip()


SALES_JOB_DESCRIPTION = """
Посадова інструкція менеджера з продажів та роботи з клієнтами.

Підпорядкування: заступнику директора.
Місце роботи: відділ продажів та роботи з клієнтами, віддалений формат.

Основні обов'язки:
- активний пошук клієнтів через холодні дзвінки, email, соціальні мережі,
  фріланс-біржі і нетворкінг;
- вивчення ринку та конкурентів;
- первинні переговори;
- формування комерційних пропозицій відповідно до потреб клієнтів;
- високий рівень комунікації на всіх етапах співпраці;
- збір і аналіз зворотного зв'язку;
- регулярні звіти про продажі, цілі і виконання планів;
- співпраця з маркетингом для узгодження просування.

Права:
- вимагати інформацію, необхідну для виконання обов'язків;
- пропонувати покращення процесів продажу;
- приймати рішення щодо КП у межах стандартів.

Вимоги:
- вища освіта у сфері економіки, менеджменту або маркетингу;
- 1-2 роки досвіду у продажах або клієнтському сервісі;
- переговори, переконання, CRM, основи маркетингу.

Кінцевий продукт: нові підписані контракти, задоволені клієнти,
виконані плани продажів.
""".strip()


DAILY_KPI_TEMPLATE = """
Щоденка задачі: шаблон для Sales Manager.

План на день:
- ставки на Freelancehunt: 20;
- розсилка Instagram: 30;
- розсилка Facebook: 40;
- Email: 20;
- LinkedIn: 10;
- Telegram: 5;
- всього контактів: 125.

Репости:
- Instagram Trends: 1;
- Threads/Trends: 1;
- Facebook groups: 1.

Таблиця KPI має містити план і факт по кожному джерелу лідів:
Freelancehunt, Instagram, Facebook, Email, LinkedIn, Telegram, репости.
Щодня менеджер вносить факт, посилання на репости і короткий коментар
по якості діалогів.
""".strip()


PRODUCT_DEFINITION = """
PRODUCT DEFINITION v3: AI Sales Onboarding Agent.

Ідея: AI-система визначає готовність sales-спеціаліста до роботи:
веде новачка від визначення рівня через персоналізоване навчання до
підтвердження готовності працювати з реальними лідами.

Відмінність від конкурентів:
- LMS навчають, але не підтверджують готовність;
- HRM керують процесами, але не тренують рольові навички;
- Sales Analytics аналізують результат, але не ведуть онбординг.

Наш підхід:
- тест при першому вході;
- персоналізований план навчання під роль і рівень;
- AI-чат з відповідями з внутрішніх документів;
- моніторинг прогресу без відчуття стеження;
- підтвердження готовності до реальної роботи.

MVP:
- BDR Марина і ментор Олег як основний сценарій;
- тест при вході;
- 30/60/90 план;
- RAG-чат;
- завантаження документів;
- картки прогресу;
- дайджест для ментора.

Базова корисна база знань:
основи продажів, холодні ліди, теплі ліди, етапи продажу, скрипти,
заперечення, follow-up, кваліфікація, CRM-дисципліна, KPI, розвиток
від junior до middle і senior.
""".strip()


SALES_PRACTICE_LIBRARY = """
Практична база: заперечення, кейси, AI-клієнти.

Заперечення:
1. "Це дорого для нас зараз." Відповідь: порівняйте ціну продукту з вартістю
поточної проблеми. Якщо Head of Sales витрачає 8 год/тиждень по $50/год,
це $1600 за місяць на одного новачка.
2. "Зараз не кращий час." Відповідь: запитайте, чи планують наймати Sales
цього кварталу. Якщо так, кожен тиждень затримки коштує часу ментора.
3. "Ми вже використовуємо Notion." Відповідь: Notion зберігає знання, але не
перевіряє засвоєння і не дає рольову практику.
4. "AI не замінить ментора." Відповідь: AI не замінює ментора, а бере рутину:
повторення базових питань, тестування знань, практика стандартних заперечень.
5. "Нам потрібен пілот." Відповідь: одразу визначити команду, метрики успіху
і термін 4 або 6 тижнів.

Кейси:
- Finteco: Head of Sales витрачав 10+ год/тиждень на новачка; ROI у годинах
ментора допоміг закрити річний контракт.
- TechSales UA: HR Director купила не "онбординг", а інструмент зменшення
плинності нових Sales.
- RetailGroup: угоду програли через внутрішній IT-проєкт, який не виявили.
- StartupX: proposal був занадто дорогим для seed-стадії.
- SalesForce UA: повернення після "не зараз" спрацювало, коли з'явився
тригер найму.

AI-клієнти:
- Олексій Коваль, Head of Sales: прагматик, говорить цифрами, питає ROI.
- Наталя Мороз, HR Director: турбується про employee experience.
- Дмитро Савченко, COO: питає про масштабування, безпеку, інтеграції.
- Аліна Лисенко, CEO: швидко вирішує, але не має часу на складний запуск.
""".strip()


SALES_FOUNDATIONS = """
Основи продажів для Sales Manager.

Холодний лід — людина або компанія, яка ще не проявила явного інтересу.
Мета першого контакту: не продати одразу, а отримати відповідь і короткий
діагностичний дзвінок.

Теплий лід — контакт, який відповів, залишив заявку або взаємодіяв з контентом.
Для теплого ліда важливо швидко уточнити потребу, контекст, бюджет і наступний крок.

Кваліфікація:
- проблема;
- роль людини у прийнятті рішення;
- бюджет або діапазон;
- дедлайн;
- поточне рішення;
- наступний крок.

Follow-up:
- перший follow-up через 24 години після контакту;
- другий через 2-3 дні з додатковою цінністю;
- третій через 5-7 днів з простим питанням про релевантність;
- після зустрічі завжди фіксувати summary, домовленості і дату наступного кроку.

Розвиток:
- junior: виконує скрипт і KPI під контролем;
- middle: самостійно веде цикл до КП;
- senior: працює зі складними угодами, покращує процес і навчає інших.
""".strip()


BACKEND_DOCUMENTS = [
    {
        "title": "Company Handbook",
        "content": (
            "Welcome to TechCorp. Core values: ownership, collaboration, continuous learning.\n"
            "Working hours are flexible with core hours 10:00-16:00. Slack is async, Google Meet is sync.\n"
            "Vacation: 20 days/year, request through HR portal at least 2 weeks in advance.\n"
            "Pointage: log hours in Jira daily and submit weekly timesheet Friday 17:00."
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
            "Payments owns payment-gateway, fraud-detection, settlement-service, reconciliation-service.\n"
            "Tech stack: Python FastAPI, PostgreSQL, Redis, Kafka, Kubernetes on AWS EKS.\n"
            "Services communicate via Kafka events. REST APIs are only for external clients.\n"
            "Tech lead approval is mandatory for payment-gateway changes."
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
            "Deployment flow: merge PR after 2 approvals, CI runs automatically, staging deploys after CI passes.\n"
            "Verify on staging.payments.techcorp.internal. For production, post in #deploys, run kubectl rollout status,\n"
            "monitor Grafana for 15 minutes, rollback with kubectl rollout undo if needed.\n"
            "Victor handles infrastructure; Oleg gives release approval."
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
            "Before opening a PR: all tests pass, no debug statements, unit tests added, API changes documented,\n"
            "migrations reversible. PR description includes what changed, how to test, and Jira link.\n"
            "Reviewers have 24h; address comments before merging; tech lead approves payment-critical changes last."
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
            "Ticket statuses: Backlog, To Do, In Progress, In Review, Done. Sprint planning every 2 weeks Monday.\n"
            "Daily standup is async in #payments-standup by 10:00. Assign ticket before work, move to In Review when PR opens,\n"
            "move to Done after merge. Bugs require reproduction steps and logs."
        ),
        "source": "Engineering",
        "document_type": "guide",
        "domain": "process",
        "role_target": "backend_developer",
        "scope": "team",
    },
]


SALES_DOCUMENTS = [
    {
        "title": "Регламент роботи відділу продажів 2026",
        "content": SALES_REGULATION,
        "source": "Sales Ops",
        "document_type": "policy",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "team",
    },
    {
        "title": "Що має вміти Sales Manager",
        "content": SALES_SKILLS,
        "source": "Sales Enablement",
        "document_type": "reference",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "role",
    },
    {
        "title": "Посадова інструкція менеджера з продажів",
        "content": SALES_JOB_DESCRIPTION,
        "source": "HR",
        "document_type": "handbook",
        "domain": "hr",
        "role_target": "sales_manager",
        "scope": "role",
    },
    {
        "title": "Щоденка задачі Sales KPI",
        "content": DAILY_KPI_TEMPLATE,
        "source": "Sales Ops",
        "document_type": "checklist",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "team",
    },
    {
        "title": "Product Definition v3 - AI Sales Onboarding Agent",
        "content": PRODUCT_DEFINITION,
        "source": "Product",
        "document_type": "reference",
        "domain": "product",
        "role_target": "all",
        "scope": "enterprise",
    },
    {
        "title": "Sales Objections, Cases and AI Clients",
        "content": SALES_PRACTICE_LIBRARY,
        "source": "Sales Enablement",
        "document_type": "playbook",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "role",
    },
    {
        "title": "Sales Foundations: Leads, Follow-up, CRM",
        "content": SALES_FOUNDATIONS,
        "source": "Sales Enablement",
        "document_type": "guide",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "role",
    },
]


PEOPLE = [
    {"full_name": "Oleg Bondarenko", "role": "Head of Sales", "team": "Sales", "email": "oleg@orynt.demo", "topics": ["sales_onboarding", "kpi", "objections", "crm"]},
    {"full_name": "Natalia Moroz", "role": "HR Director", "team": "People", "email": "natalia@orynt.demo", "topics": ["employee_experience", "retention", "onboarding_quality"]},
    {"full_name": "Victor Petrenko", "role": "DevOps Engineer", "team": "Infrastructure", "email": "victor@orynt.demo", "topics": ["deployment", "kubernetes", "staging", "rollback"]},
    {"full_name": "Katia Shevchenko", "role": "Senior AE", "team": "Sales", "email": "katia@orynt.demo", "topics": ["demo", "pricing", "competitive_intel", "enterprise_deals"]},
    {"full_name": "Ana Kovalenko", "role": "QA Engineer", "team": "Payments", "email": "ana@orynt.demo", "topics": ["testing", "qa", "bug_reporting"]},
]


MARINA_TASKS = [
    {"week": 1, "day": 1, "title": "Review sales onboarding baseline", "description": "Review ICP, outreach, CRM, and objection-handling expectations already captured during kickoff.", "type": "reading", "status": "done", "priority": "high"},
    {"week": 1, "day": 2, "title": "Read sales process and KPI regulation", "description": "Understand lead generation, diagnostic calls, proposal flow, and daily activity norms.", "type": "reading", "status": "done", "priority": "high"},
    {"week": 1, "day": 3, "title": "Write first cold outreach sequence", "description": "Draft three short messages for Facebook, Instagram and LinkedIn using the company ICP.", "type": "outreach", "status": "done", "priority": "high"},
    {"week": 1, "day": 4, "title": "Log daily KPI table accurately", "description": "Fill plan/fact for every source and attach repost links.", "type": "crm", "status": "blocked", "priority": "high"},
    {"week": 2, "day": 1, "title": "Run objection role-play: too expensive", "description": "Practice moving from price to cost of current problem.", "type": "role_play", "status": "in_progress", "priority": "high"},
    {"week": 2, "day": 2, "title": "Prepare diagnostic call brief", "description": "Use problem, budget, decision role, deadline and current solution fields.", "type": "discovery", "status": "todo", "priority": "medium"},
    {"week": 2, "day": 3, "title": "Create follow-up cadence for warm leads", "description": "Draft 24h, 3-day and 7-day follow-ups with value add.", "type": "follow_up", "status": "todo", "priority": "medium"},
    {"week": 3, "day": 1, "title": "Shadow Katia on a proposal presentation", "description": "Watch how a senior seller handles objections and confirms next steps.", "type": "shadowing", "status": "todo", "priority": "medium"},
]


TANYA_TASKS = [
    {"week": 1, "day": 1, "title": "Set up local development environment", "description": "Clone repos, install dependencies, run backend tests locally.", "type": "setup", "status": "done", "priority": "high"},
    {"week": 1, "day": 2, "title": "Trace payment-gateway request flow", "description": "Follow one external API call through FastAPI, Kafka and PostgreSQL.", "type": "architecture", "status": "done", "priority": "high"},
    {"week": 1, "day": 3, "title": "Read code review checklist", "description": "Map every checklist item to the first PR draft.", "type": "reading", "status": "done", "priority": "medium"},
    {"week": 2, "day": 1, "title": "Open first backend PR", "description": "Fix a small payment-gateway validation issue and request two reviews.", "type": "development", "status": "in_progress", "priority": "high"},
    {"week": 2, "day": 2, "title": "Resolve PR comments", "description": "Address API docs, unit tests and migration questions.", "type": "code_review", "status": "in_progress", "priority": "high"},
    {"week": 2, "day": 4, "title": "Prepare staging deployment checklist", "description": "Explain deploy, monitor and rollback steps before touching production.", "type": "deployment", "status": "todo", "priority": "high"},
    {"week": 3, "day": 1, "title": "Shadow production deployment", "description": "Join Victor for rollout status, Grafana monitoring and rollback drill.", "type": "deployment", "status": "todo", "priority": "medium"},
    {"week": 3, "day": 3, "title": "Document first PR learning notes", "description": "Capture architecture notes and gotchas for the next newcomer.", "type": "documentation", "status": "todo", "priority": "medium"},
]


def _full_name(newcomer: NewcomerProfile) -> str:
    return newcomer.user.full_name if newcomer.user else f"Newcomer #{newcomer.id}"


def _persona(role: str, user: User, newcomer: NewcomerProfile | None = None) -> dict:
    return {
        "role": role,
        "user_id": user.id,
        "newcomer_id": newcomer.id if newcomer else None,
        "name": user.full_name,
        "email": user.email,
        "job_title": newcomer.job_title if newcomer else user.role,
        "team": newcomer.team if newcomer else "Sales",
    }


def _seed_response(
    db: Session,
    *,
    already_seeded: bool = False,
    documents_created: int = 0,
    courses_created: int = 0,
    tasks_created: int = 0,
    questions_created: int = 0,
    meetings_created: int = 0,
    signals_created: int = 0,
    blocked_reports_created: int = 0,
) -> dict:
    mentor = (
        db.query(User)
        .filter(User.role == "mentor")
        .order_by(User.id.asc())
        .first()
    )
    newcomers = (
        db.query(NewcomerProfile)
        .join(User, NewcomerProfile.user_id == User.id)
        .order_by(NewcomerProfile.id.asc())
        .all()
    )
    default_newcomer = newcomers[0] if newcomers else None
    personas = []
    if mentor:
        personas.append(_persona("mentor", mentor))
    for newcomer in newcomers:
        if newcomer.user:
            personas.append(_persona("newcomer", newcomer.user, newcomer))
    first_signal = db.query(AISignal).order_by(AISignal.id.asc()).first()
    first_plan = db.query(OnboardingPlan).order_by(OnboardingPlan.id.asc()).first()
    return {
        "already_seeded": already_seeded,
        "mentor_id": mentor.id if mentor else None,
        "newcomer_id": default_newcomer.id if default_newcomer else None,
        "newcomer_user_id": default_newcomer.user_id if default_newcomer else None,
        "newcomer_ids": [n.id for n in newcomers],
        "personas": personas,
        "plan_id": first_plan.id if first_plan else None,
        "signal_id": first_signal.id if first_signal else None,
        "documents_created": documents_created,
        "courses_created": courses_created,
        "tasks_created": tasks_created,
        "questions_created": questions_created,
        "meetings_created": meetings_created,
        "signals_created": signals_created,
        "blocked_reports_created": blocked_reports_created,
    }


def _create_documents(db: Session) -> list[Document]:
    docs: list[Document] = []
    for doc_data in [*SALES_DOCUMENTS, *BACKEND_DOCUMENTS]:
        doc = Document(source_type="text", external_url=None, **doc_data)
        db.add(doc)
        docs.append(doc)
    db.commit()
    for doc in docs:
        db.refresh(doc)
        try:
            generate_chunks_for_document(db=db, document=doc)
        except Exception:
            db.rollback()
    return docs


def _first_chunk(db: Session, document: Document | None) -> DocumentChunk | None:
    if not document:
        return None
    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc(), DocumentChunk.id.asc())
        .first()
    )


def _find_doc(docs: list[Document], text: str) -> Document | None:
    text_lower = text.lower()
    return next((doc for doc in docs if text_lower in doc.title.lower()), None)


def _create_plan(
    db: Session,
    *,
    newcomer: NewcomerProfile,
    mentor: User,
    title: str,
    description: str,
    goal: str,
    tasks: list[dict],
) -> tuple[OnboardingPlan, list[OnboardingTask]]:
    start = newcomer.start_date or date.today()
    plan = OnboardingPlan(
        newcomer_id=newcomer.id,
        mentor_id=mentor.id,
        title=title,
        description=description,
        period_label="First 30 days",
        period_start=start,
        period_end=start + timedelta(days=29),
        goal=goal,
        status="active",
        generated_by_ai=True,
        mentor_approved=True,
    )
    db.add(plan)
    db.flush()

    sprint = Sprint(
        plan_id=plan.id,
        index=1,
        title="Days 1-30 ramp",
        description=goal,
        start_day=1,
        end_day=30,
    )
    db.add(sprint)
    db.flush()

    weeks: dict[int, Week] = {}
    for week_index in sorted({item["week"] for item in tasks}):
        week = Week(
            plan_id=plan.id,
            sprint_id=sprint.id,
            index=week_index,
            title=f"Week {week_index}",
            summary=f"Week {week_index} focus for {_full_name(newcomer)}",
            goals=[item["title"] for item in tasks if item["week"] == week_index][:3],
        )
        db.add(week)
        db.flush()
        weeks[week_index] = week

    created: list[OnboardingTask] = []
    for item in tasks:
        week = weeks[item["week"]]
        task = OnboardingTask(
            plan_id=plan.id,
            week_id=week.id,
            sprint_id=sprint.id,
            title=item["title"],
            description=item["description"],
            week_number=item["week"],
            day_number=item["day"],
            task_type=item["type"],
            status=item["status"],
            priority=item["priority"],
            success_criteria=item.get("success_criteria") or f"Done when {_full_name(newcomer).split()[0]} can explain and apply this without mentor prompting.",
            acceptance_criteria=item.get("acceptance_criteria"),
            examples=item.get("examples"),
            links=item.get("links"),
        )
        db.add(task)
        db.flush()
        created.append(task)
        db.add(
            OnboardingEvent(
                newcomer_id=newcomer.id,
                user_id=newcomer.user_id,
                event_type="task_status_changed",
                entity_type="onboarding_task",
                entity_id=task.id,
                topic=task.task_type,
                metadata_json={"task_title": task.title, "status": task.status},
            )
        )
    return plan, created


def _create_course(
    db: Session,
    *,
    newcomer: NewcomerProfile,
    mentor: User,
    plan: OnboardingPlan,
    title: str,
    summary: str,
    role_target: str,
    source_docs: list[Document],
    lessons: list[dict],
) -> Course:
    now = datetime.now(timezone.utc)
    source_document_ids = [doc.id for doc in source_docs if doc]
    course = Course(
        plan_id=plan.id,
        newcomer_id=newcomer.id,
        mentor_id=mentor.id,
        title=title,
        summary=summary,
        role_target=role_target,
        status="published",
        generated_by_ai=True,
        source_document_ids=source_document_ids,
        approved_at=now,
        published_at=now,
    )
    db.add(course)
    db.flush()

    for index, item in enumerate(lessons, start=1):
        db.add(
            Lesson(
                course_id=course.id,
                index=index,
                title=item["title"],
                summary=item.get("summary"),
                body=item.get("body"),
                video_url=item.get("video_url"),
                source_document_ids=item.get("source_document_ids", source_document_ids),
                takeaways=item.get("takeaways"),
            )
        )
    return course


def _create_ai_question(
    db: Session,
    *,
    newcomer: NewcomerProfile,
    question: str,
    answer: str,
    source_doc: Document | None,
) -> AIQuestion:
    ai_question = AIQuestion(
        user_id=newcomer.user_id,
        newcomer_id=newcomer.id,
        question=question,
        answer=answer,
        status="answered",
    )
    db.add(ai_question)
    db.flush()
    db.add(
        OnboardingEvent(
            newcomer_id=newcomer.id,
            user_id=newcomer.user_id,
            event_type="ai_question_asked",
            entity_type="ai_question",
            entity_id=ai_question.id,
            topic="sales" if "CRM" in answer or "KPI" in answer else "deployment",
        )
    )
    chunk = _first_chunk(db, source_doc)
    if source_doc and chunk:
        db.add(
            AIQuestionSource(
                question_id=ai_question.id,
                document_id=source_doc.id,
                chunk_id=chunk.id,
                title=source_doc.title,
                content_preview=chunk.content[:300],
                similarity=0.88,
            )
        )
    return ai_question


def _create_assessment(
    db: Session,
    *,
    newcomer: NewcomerProfile,
    mentor: User,
    title: str,
    questions: list[dict],
) -> Assessment:
    assessment = Assessment(
        newcomer_id=newcomer.id,
        mentor_id=mentor.id,
        title=title,
        status="published",
        mentor_notes="Seeded demo readiness check.",
        role_context=newcomer.job_title,
        generated_by_ai=True,
        used_fallback=False,
        published_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.flush()
    for index, item in enumerate(questions):
        db.add(
            AssessmentQuestion(
                assessment_id=assessment.id,
                order_index=index,
                question_type=item["type"],
                prompt=item["prompt"],
                options=item.get("options"),
                expected_answer=item.get("expected_answer"),
                skill_tag=item["skill_tag"],
                difficulty=item.get("difficulty", "medium"),
            )
        )
    return assessment


def reset_demo_data(db: Session) -> dict:
    try:
        for model in [
            AISignalFeedback,
            AIAnswerFeedback,
            AIQuestionSource,
            AssessmentAnswer,
            AssessmentSubmission,
            AssessmentQuestion,
            ScheduledMeeting,
            BlockedReport,
            PlanAdjustmentSuggestion,
            AISignal,
            ProgressSnapshot,
            OnboardingReflection,
            OnboardingEvent,
            NewcomerRecommendedContact,
            LessonNote,
            Lesson,
            Course,
            OnboardingTask,
            Week,
            Sprint,
            OnboardingPlan,
            MentorDigest,
            CompanyOnboardingGap,
            Assessment,
            AIQuestion,
            AIConversation,
            DocumentChunk,
            Document,
            PersonContact,
            NewcomerProfile,
            User,
        ]:
            db.query(model).delete(synchronize_session=False)
        db.commit()
        return seed_demo_data(db=db)
    except Exception:
        db.rollback()
        raise


def seed_demo_data(db: Session) -> dict:
    existing_mentor = db.query(User).filter(User.email == "oleg@orynt.demo").first()
    if existing_mentor:
        return _seed_response(db, already_seeded=True)

    mentor = User(email="oleg@orynt.demo", full_name="Oleg Bondarenko", role="mentor")
    marina_user = User(email="marina@orynt.demo", full_name="Marina Kovalenko", role="newcomer")
    tanya_user = User(email="tanya@orynt.demo", full_name="Tanya Petrova", role="newcomer")
    db.add_all([mentor, marina_user, tanya_user])
    db.flush()

    marina = NewcomerProfile(
        user_id=marina_user.id,
        mentor_id=mentor.id,
        job_title="Sales Manager / BDR",
        seniority="Junior",
        team="Sales",
        start_date=date.today() - timedelta(days=10),
        onboarding_status="active",
    )
    tanya = NewcomerProfile(
        user_id=tanya_user.id,
        mentor_id=mentor.id,
        job_title="Backend Developer",
        seniority="Middle",
        team="Payments",
        start_date=date.today() - timedelta(days=12),
        onboarding_status="active",
    )
    db.add_all([marina, tanya])
    db.flush()

    for person in PEOPLE:
        db.add(PersonContact(**person))
    db.flush()

    docs = _create_documents(db)

    marina_plan, marina_tasks = _create_plan(
        db,
        newcomer=marina,
        mentor=mentor,
        title="Marina Kovalenko - Sales/BDR Onboarding",
        description="30-day plan focused on sales process, daily KPI discipline, CRM hygiene, and objection practice.",
        goal="Make Marina ready to handle real cold and warm leads with clean CRM updates.",
        tasks=MARINA_TASKS,
    )
    tanya_plan, tanya_tasks = _create_plan(
        db,
        newcomer=tanya,
        mentor=mentor,
        title="Tanya Petrova - Backend Developer Onboarding",
        description="30-day plan focused on payments architecture, first PR, review quality, and deployment readiness.",
        goal="Make Tanya confident to ship a backend PR and safely participate in staging deployment.",
        tasks=TANYA_TASKS,
    )

    blocked_task = next(task for task in marina_tasks if task.status == "blocked")
    db.add(
        BlockedReport(
            newcomer_id=marina.id,
            task_id=blocked_task.id,
            user_id=marina_user.id,
            blocker_type="crm_kpi_confusion",
            details=(
                "Marina is unsure how to map Instagram/Facebook conversations into the KPI tracker "
                "and has not updated plan/fact rows for two days."
            ),
            ai_suggestion=(
                "Schedule a 15-minute CRM hygiene walkthrough, then give Marina one clean example "
                "for each source before the next outreach block."
            ),
            status="open",
        )
    )

    tanya_signal_1 = AISignal(
        newcomer_id=tanya.id,
        signal_type="code_review_attention",
        severity="medium",
        tone="attention",
        confidence=0.84,
        score=0.71,
        title="PR review loop needs mentor attention",
        description="Tanya opened the first backend PR, but review comments are clustering around tests and API documentation.",
        evidence="- First PR is in progress.\n- Code review checklist was opened.\n- Questions mention tests, docs and migration expectations.",
        suggested_action="Pair for 20 minutes on one review comment and ask Tanya to update the PR checklist before re-requesting review.",
        status="open",
        occurrence_count=3,
        target_task_id=next(task.id for task in tanya_tasks if task.task_type == "code_review"),
    )
    tanya_signal_2 = AISignal(
        newcomer_id=tanya.id,
        signal_type="deployment_readiness_attention",
        severity="high",
        tone="attention",
        confidence=0.89,
        score=0.82,
        title="Deployment readiness is not yet proven",
        description="Tanya read the deployment guide but has not yet practiced rollout status, monitoring or rollback.",
        evidence="- Deployment checklist task is still todo.\n- AI questions focus on staging, approvals and rollback.\n- Production deploy shadowing is scheduled later this week.",
        suggested_action="Keep production deploy shadowing, but add a staging dry run with Victor before any release responsibility.",
        status="open",
        occurrence_count=4,
        target_task_id=next(task.id for task in tanya_tasks if task.title.startswith("Prepare staging")),
    )
    db.add_all([tanya_signal_1, tanya_signal_2])
    db.flush()

    db.add(
        PlanAdjustmentSuggestion(
            newcomer_id=marina.id,
            plan_id=marina_plan.id,
            signal_id=None,
            title="Adapt Marina Week 2: CRM and objection recovery",
            reason=(
                "Marina is blocked on KPI/CRM discipline and is still shaky on price objections. "
                "Reducing new outreach volume for one day creates room for practice and cleanup."
            ),
            suggested_changes=[
                {
                    "action": "add_task",
                    "title": "CRM hygiene walkthrough with Oleg",
                    "description": "Walk through one Instagram, one Facebook and one Email lead from contact to KPI fact row.",
                    "task_type": "crm",
                    "week_number": 2,
                    "day_number": 2,
                    "priority": "high",
                    "success_criteria": "Marina can update all KPI rows without mentor correction.",
                },
                {
                    "action": "add_task",
                    "title": "Objection practice: expensive and not now",
                    "description": "Run two AI-client role plays using the objection playbook.",
                    "task_type": "role_play",
                    "week_number": 2,
                    "day_number": 3,
                    "priority": "high",
                    "success_criteria": "Marina handles both objections with problem-cost framing.",
                },
            ],
            status="pending",
            target_scope="week",
        )
    )

    db.add_all(
        [
            ProgressSnapshot(
                newcomer_id=marina.id,
                week_number=2,
                completed_tasks=3,
                blocked_tasks=1,
                open_signals=0,
                progress_percent=38,
                strengths=["ICP basics", "cold message drafting"],
                gaps=["CRM discipline", "KPI plan/fact", "price objections"],
                mentor_notes="Marina is promising but needs a concrete CRM example before more outreach volume.",
            ),
            ProgressSnapshot(
                newcomer_id=tanya.id,
                week_number=2,
                completed_tasks=3,
                blocked_tasks=0,
                open_signals=2,
                progress_percent=52,
                strengths=["architecture tracing", "first PR ownership"],
                gaps=["review checklist depth", "deployment confidence"],
                mentor_notes="Tanya is progressing well; the signals are attention items, not blockers.",
            ),
        ]
    )

    questions_created = 0
    for payload in [
        (
            marina,
            "Яка денна норма контактів для Sales Manager?",
            "Денний план: Freelancehunt 20, Instagram 30, Facebook 40, Email 20, LinkedIn 10, Telegram 5; всього 125 контактів.",
            _find_doc(docs, "Щоденка"),
        ),
        (
            marina,
            "Що відповідати, якщо клієнт каже що дорого?",
            "Не знижуйте ціну одразу. Переведіть розмову на вартість поточної проблеми і порахуйте час ментора або втрачений результат.",
            _find_doc(docs, "Objections"),
        ),
        (
            marina,
            "Що має бути в діагностичному дзвінку?",
            "Потрібно зібрати цілі, стан бізнесу, бюджет, проблеми, потенціал клієнта і домовитись про наступний крок.",
            _find_doc(docs, "Регламент"),
        ),
        (
            tanya,
            "How do I deploy my changes to staging?",
            "Merge after 2 approvals, wait for CI, verify staging, then follow the deployment guide for production readiness.",
            _find_doc(docs, "Deployment"),
        ),
        (
            tanya,
            "Who approves payment-gateway changes?",
            "Tech lead approval is mandatory for payment-gateway changes; Victor supports infrastructure questions.",
            _find_doc(docs, "Architecture"),
        ),
        (
            tanya,
            "What should be in my PR description?",
            "Include what changed, how to test it, and a Jira link. Make sure tests pass and API changes are documented.",
            _find_doc(docs, "Code Review"),
        ),
    ]:
        _create_ai_question(
            db,
            newcomer=payload[0],
            question=payload[1],
            answer=payload[2],
            source_doc=payload[3],
        )
        questions_created += 1

    courses = [
        _create_course(
            db,
            newcomer=marina,
            mentor=mentor,
            plan=marina_plan,
            title="Sales Manager First Wins",
            summary="A short role course for Marina covering outreach, CRM discipline, KPI reporting, and objection handling.",
            role_target="sales_manager",
            source_docs=[
                doc
                for doc in [
                    _find_doc(docs, "Sales Foundations"),
                    _find_doc(docs, "Sales Objections"),
                    _find_doc(docs, "KPI"),
                ]
                if doc
            ],
            lessons=[
                {
                    "title": "Map daily activity into clean CRM evidence",
                    "summary": "Turn outreach activity into plan/fact rows, lead notes, and next steps Oleg can trust.",
                    "body": (
                        "Start from the channel KPI, then record each meaningful dialogue with source, status, "
                        "next step, and blocker. A clean CRM entry answers who the lead is, why they fit, what "
                        "happened, and what happens next."
                    ),
                    "takeaways": [
                        "Track channel activity daily.",
                        "Separate activity KPI from outcome KPI.",
                        "Every warm lead needs a next step.",
                    ],
                },
                {
                    "title": "Objection handling role-play",
                    "summary": "Practice price, timing, and competitor objections before live outreach.",
                    "body": (
                        "Do not discount on the first price objection. Reframe the conversation around the cost "
                        "of the current onboarding problem, mentor time, and delayed productivity."
                    ),
                    "video_url": "https://www.youtube.com/watch?v=ysz5S6PUM-U",
                    "takeaways": [
                        "Acknowledge the concern.",
                        "Ask one diagnostic question.",
                        "Return to business impact.",
                    ],
                },
            ],
        ),
        _create_course(
            db,
            newcomer=tanya,
            mentor=mentor,
            plan=tanya_plan,
            title="Backend Developer Release Readiness",
            summary="A focused course for Tanya covering the payments architecture, PR checklist, and staging deployment flow.",
            role_target="backend_developer",
            source_docs=[
                doc
                for doc in [
                    _find_doc(docs, "Architecture"),
                    _find_doc(docs, "Code Review"),
                    _find_doc(docs, "Deployment"),
                ]
                if doc
            ],
            lessons=[
                {
                    "title": "Payments architecture map",
                    "summary": "Understand the services Tanya touches before changing payment-gateway behavior.",
                    "body": (
                        "Payments changes usually cross service boundaries. Before coding, identify the owning "
                        "service, event contracts, database impact, and whether tech lead approval is required."
                    ),
                    "takeaways": [
                        "Payment-gateway changes require tech lead approval.",
                        "Kafka events carry most internal service communication.",
                        "Document API or migration changes in the PR.",
                    ],
                },
                {
                    "title": "Open a review-ready backend PR",
                    "summary": "Prepare the checklist, test notes, and staging verification plan before asking for review.",
                    "body": (
                        "A review-ready PR includes what changed, how to test it, the Jira link, migration notes, "
                        "and evidence that CI and relevant unit tests passed."
                    ),
                    "video_url": "https://www.youtube.com/watch?v=ysz5S6PUM-U",
                    "takeaways": [
                        "Use the PR checklist before requesting review.",
                        "Verify staging after CI deploys.",
                        "Escalate deployment uncertainty early.",
                    ],
                },
            ],
        ),
    ]

    now = datetime.now(timezone.utc)
    meetings = [
        ScheduledMeeting(
            newcomer_id=marina.id,
            organizer_user_id=mentor.id,
            plan_id=marina_plan.id,
            task_id=blocked_task.id,
            title="CRM hygiene unblock",
            agenda="Map three real leads into KPI plan/fact rows and confirm the reporting habit.",
            starts_at=now + timedelta(days=1, hours=2),
            ends_at=now + timedelta(days=1, hours=2, minutes=30),
            attendee_emails=[mentor.email, marina_user.email],
            teams_join_url="https://teams.microsoft.com/l/demo-marina-crm",
            status="confirmed",
        ),
        ScheduledMeeting(
            newcomer_id=marina.id,
            organizer_user_id=mentor.id,
            plan_id=marina_plan.id,
            title="Objection role-play: price and timing",
            agenda="Practice two AI-client scenarios from the objection playbook.",
            starts_at=now + timedelta(days=3, hours=1),
            ends_at=now + timedelta(days=3, hours=1, minutes=45),
            attendee_emails=[mentor.email, marina_user.email, "katia@orynt.demo"],
            teams_join_url="https://teams.microsoft.com/l/demo-marina-objections",
            status="proposed",
        ),
        ScheduledMeeting(
            newcomer_id=tanya.id,
            organizer_user_id=mentor.id,
            plan_id=tanya_plan.id,
            task_id=next(task.id for task in tanya_tasks if task.task_type == "code_review"),
            signal_id=tanya_signal_1.id,
            title="First PR review pairing",
            agenda="Resolve one test comment and one API documentation comment together.",
            starts_at=now + timedelta(days=1, hours=5),
            ends_at=now + timedelta(days=1, hours=5, minutes=30),
            attendee_emails=[mentor.email, tanya_user.email],
            teams_join_url="https://teams.microsoft.com/l/demo-tanya-pr",
            status="confirmed",
        ),
        ScheduledMeeting(
            newcomer_id=tanya.id,
            organizer_user_id=mentor.id,
            plan_id=tanya_plan.id,
            task_id=next(task.id for task in tanya_tasks if task.task_type == "deployment"),
            signal_id=tanya_signal_2.id,
            title="Staging deployment dry run",
            agenda="Run rollout status, monitoring checklist and rollback drill with Victor.",
            starts_at=now + timedelta(days=4, hours=3),
            ends_at=now + timedelta(days=4, hours=4),
            attendee_emails=[mentor.email, tanya_user.email, "victor@orynt.demo"],
            teams_join_url="https://teams.microsoft.com/l/demo-tanya-deploy",
            status="proposed",
        ),
    ]
    db.add_all(meetings)

    db.add(
        MentorDigest(
            mentor_id=mentor.id,
            week_start=date.today() - timedelta(days=date.today().weekday()),
            week_end=date.today() - timedelta(days=date.today().weekday()) + timedelta(days=6),
            summary=(
                "Marina needs CRM/KPI help before scaling outreach. Tanya is moving well, "
                "but PR review and deployment readiness need attention this week."
            ),
            highlights=[
                "Marina completed ICP and outreach drafting.",
                "Tanya traced payments architecture and opened a first PR.",
            ],
            risks=[
                "Marina is blocked on KPI plan/fact reporting.",
                "Tanya has not yet proven deployment readiness.",
            ],
            recommended_actions=[
                "Run Marina CRM hygiene unblock.",
                "Keep Tanya staging dry run with Victor.",
            ],
        )
    )

    db.commit()

    return _seed_response(
        db,
        documents_created=len(docs),
        courses_created=len(courses),
        tasks_created=len(marina_tasks) + len(tanya_tasks),
        questions_created=questions_created,
        meetings_created=len(meetings),
        signals_created=2,
        blocked_reports_created=1,
    )
