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
from app.models.arena import ArenaMessage, ArenaScenario, ArenaSession
from app.models.blocked_report import BlockedReport
from app.models.company_onboarding_gap import CompanyOnboardingGap
from app.models.course import Course
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.lesson import Lesson
from app.models.lesson_note import LessonNote
from app.models.mentor_digest import MentorDigest
from app.models.newcomer import NewcomerProfile
from app.models.notification import Notification
from app.models.onboarding_event import OnboardingEvent
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_reflection import OnboardingReflection
from app.models.onboarding_task import OnboardingTask
from app.models.person_contact import NewcomerRecommendedContact, PersonContact
from app.models.plan_adjustment import PlanAdjustmentSuggestion
from app.models.progress_snapshot import ProgressSnapshot
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.sprint import Sprint
from app.models.task_comment import TaskComment
from app.models.user import User
from app.models.week import Week
from app.services.rag_service import generate_chunks_for_document
from app.services.topic_classifier import classify_topic


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
Щоденник задач: шаблон для менеджера з продажів.

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
ОПИС ПРОДУКТУ v3: AI-агент онбордингу продажів.

Ідея: AI-система визначає готовність спеціаліста з продажів до роботи:
веде новачка від визначення рівня через персоналізоване навчання до
підтвердження готовності працювати з реальними лідами.

Відмінність від конкурентів:
- LMS навчають, але не підтверджують готовність;
- HRM керують процесами, але не тренують рольові навички;
- Аналітика продажів аналізує результат, але не веде онбординг.

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
поточної проблеми. Якщо керівник продажів витрачає 8 год/тиждень по $50/год,
це $1600 за місяць на одного новачка.
2. "Зараз не кращий час." Відповідь: запитайте, чи планують наймати спеціалістів з продажів
цього кварталу. Якщо так, кожен тиждень затримки коштує часу ментора.
3. "Ми вже використовуємо Notion." Відповідь: Notion зберігає знання, але не
перевіряє засвоєння і не дає рольову практику.
4. "AI не замінить ментора." Відповідь: AI не замінює ментора, а бере рутину:
повторення базових питань, тестування знань, практика стандартних заперечень.
5. "Нам потрібен пілот." Відповідь: одразу визначити команду, метрики успіху
і термін 4 або 6 тижнів.

Кейси:
- Finteco: керівник продажів витрачав 10+ год/тиждень на новачка; ROI у годинах
ментора допоміг закрити річний контракт.
- TechSales UA: HR Director купила не "онбординг", а інструмент зменшення
плинності нових спеціалістів з продажів.
- RetailGroup: угоду програли через внутрішній IT-проєкт, який не виявили.
- StartupX: proposal був занадто дорогим для seed-стадії.
- SalesForce UA: повернення після "не зараз" спрацювало, коли з'явився
тригер найму.

AI-клієнти:
- Олексій Коваль, керівник продажів: прагматик, говорить цифрами, питає ROI.
- Наталя Мороз, HR Director: турбується про employee experience.
- Дмитро Савченко, COO: питає про масштабування, безпеку, інтеграції.
- Аліна Лисенко, CEO: швидко вирішує, але не має часу на складний запуск.
""".strip()


SALES_FOUNDATIONS = """
Основи продажів для менеджера з продажів.

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


SALES_PRICE_LIST = """
Orynt AI Onboarding price list for 2026.

Use these prices when a prospect asks about price, pricing, budget, package,
license, subscription, cost, fee, quote, invoice, discount, or contract value.

Packages:
- Starter: USD 1,200 per month. Includes up to 25 newcomers, 3 mentor seats,
  knowledge-base chat, basic analytics, and email support.
- Growth: USD 2,800 per month. Includes up to 75 newcomers, 10 mentor seats,
  Arena role-play, AI signal detection, LMS/course generation, and priority support.
- Enterprise: starts at USD 6,500 per month. Includes unlimited newcomers,
  SSO/SAML, custom data retention, dedicated success manager, security review,
  and quarterly enablement workshops.
- Pilot: USD 3,000 for 30 days. Includes one sales team, up to 15 newcomers,
  seed knowledge-base setup, and a final readiness report.

Implementation:
- Standard onboarding setup: USD 1,500 one-time.
- Enterprise implementation: USD 5,000 one-time and includes an integrations workshop.
- Extra mentor seat: USD 120 per month.
- Extra newcomer pack: USD 400 per month for 10 additional newcomers.

Discount rules:
- Up to 10% discount may be offered for annual prepayment.
- Larger discounts require approval from Oleg Bondarenko and Finance.
- Do not discount before discovery. First quantify the cost of slow ramp,
  missed follow-ups, and manager time.
- If a prospect says "too expensive", ask what budget range they planned and
  compare it with the cost of delayed salesperson productivity.

How to explain value:
- Starter fits small teams proving the process.
- Growth is the default recommendation for sales teams because it includes
  Arena role-play and AI signal detection.
- Enterprise fits regulated or multi-country teams that need SSO, custom
  retention, and procurement support.
""".strip()


COMPANY_INFORMATION = """
Orynt company profile for sales conversations.

Company:
Orynt.ai builds AI onboarding software for teams that need new employees to
become productive faster. The demo company sells ReadySet.AI, a platform that
combines a knowledge base, AI Q&A, mentor dashboards, onboarding plans, courses,
assessments, and sales Arena simulations.

Positioning:
- We are not only an LMS. We connect learning content to daily onboarding tasks,
  mentor decisions, and readiness signals.
- We are not only a chatbot. Answers are grounded in company documents and can
  cite sources.
- We are not only analytics. Signals turn into mentor actions, plan adjustments,
  and meetings.

Primary ICP:
- Sales teams hiring BDRs, SDRs, AEs, or account managers.
- Companies with repeated onboarding pain, inconsistent ramp, messy
  documentation, or weak manager visibility.
- Teams where mistakes in pricing, discovery, CRM discipline, or product
  explanation can cost pipeline.

Proof points to mention:
- Reduces repeated mentor questions by making company docs searchable.
- Spots confusion early through AI signals from questions, blockers, repeated
  sources, and task progress.
- Gives newcomers realistic Arena practice before live customer conversations.
- Helps mentors see who is blocked, who is progressing fast, and which docs need cleanup.

Buying committee:
- Head of Sales cares about ramp time, pipeline quality, and manager leverage.
- HR/People cares about consistency and experience.
- RevOps cares about CRM discipline and process adoption.
- Finance cares about cost of ramp and tool consolidation.

Sales note:
When a prospect asks "what does your company do?", give the one-sentence
positioning first, then tailor proof points to their role. If they ask about
price, use the 2026 price list and avoid inventing a custom quote.
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
        "title": "Огляд архітектури команди Payments",
        "content": (
            "Команда Payments відповідає за payment-gateway, fraud-detection, settlement-service, reconciliation-service.\n"
            "Технічний стек: Python FastAPI, PostgreSQL, Redis, Kafka, Kubernetes на AWS EKS.\n"
            "Сервіси обмінюються даними через Kafka events. REST APIs використовуються лише для зовнішніх клієнтів.\n"
            "Для змін у payment-gateway обов'язкове схвалення tech lead."
        ),
        "source": "Engineering",
        "document_type": "architecture",
        "domain": "technical",
        "role_target": "backend_developer",
        "scope": "team",
    },
    {
        "title": "Посібник із deployment",
        "content": (
            "Deployment flow: merge PR після 2 схвалень, CI запускається автоматично, staging розгортається після успішного CI.\n"
            "Перевірте на staging.payments.techcorp.internal. Для production напишіть у #deploys, запустіть kubectl rollout status,\n"
            "моніторте Grafana 15 хвилин, за потреби зробіть rollback через kubectl rollout undo.\n"
            "Victor відповідає за infrastructure; Oleg дає схвалення release."
        ),
        "source": "Engineering",
        "document_type": "guide",
        "domain": "technical",
        "role_target": "backend_developer",
        "scope": "team",
    },
    {
        "title": "Чекліст code review",
        "content": (
            "Перед відкриттям PR: усі tests проходять, немає debug statements, додано unit tests, API changes задокументовано,\n"
            "migrations зворотні. Опис PR містить, що змінилося, як тестувати, і Jira link.\n"
            "Reviewers мають 24 год; опрацюйте коментарі перед merge; tech lead останнім схвалює критичні для payments зміни."
        ),
        "source": "Engineering",
        "document_type": "checklist",
        "domain": "technical",
        "role_target": "backend_developer",
        "scope": "team",
    },
    {
        "title": "Посібник із Jira workflow",
        "content": (
            "Статуси ticket: Backlog, To Do, In Progress, In Review, Done. Sprint planning щопонеділка раз на 2 тижні.\n"
            "Daily standup асинхронний у #payments-standup до 10:00. Призначайте ticket перед роботою, переводьте в In Review після відкриття PR,\n"
            "переводьте в Done після merge. Для bugs потрібні кроки відтворення та logs."
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
        "source": "Операції продажів",
        "document_type": "policy",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "team",
    },
    {
        "title": "Що має вміти менеджер з продажів",
        "content": SALES_SKILLS,
        "source": "Підтримка продажів",
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
        "title": "Щоденник задач KPI продажів",
        "content": DAILY_KPI_TEMPLATE,
        "source": "Операції продажів",
        "document_type": "checklist",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "team",
    },
    {
        "title": "Опис продукту v3 - AI-агент онбордингу продажів",
        "content": PRODUCT_DEFINITION,
        "source": "Product",
        "document_type": "reference",
        "domain": "product",
        "role_target": "all",
        "scope": "enterprise",
    },
    {
        "title": "Заперечення у продажах, кейси та AI-клієнти",
        "content": SALES_PRACTICE_LIBRARY,
        "source": "Підтримка продажів",
        "document_type": "playbook",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "role",
    },
    {
        "title": "Основи продажів: ліди, подальші дії, CRM",
        "content": SALES_FOUNDATIONS,
        "source": "Підтримка продажів",
        "document_type": "guide",
        "domain": "sales",
        "role_target": "sales_manager",
        "scope": "role",
    },
    {
        "title": "Orynt 2026 Price List",
        "content": SALES_PRICE_LIST,
        "source": "Finance",
        "document_type": "price_list",
        "domain": "finance",
        "role_target": "sales_manager,bdr,account_executive,all",
        "scope": "enterprise",
    },
    {
        "title": "Orynt Company Information",
        "content": COMPANY_INFORMATION,
        "source": "Sales Enablement",
        "document_type": "company_profile",
        "domain": "general",
        "role_target": "sales_manager,bdr,account_executive,all",
        "scope": "enterprise",
    },
]


PEOPLE = [
    {"full_name": "Oleg Bondarenko", "role": "Керівник продажів", "team": "Продажі", "email": "oleg@orynt.demo", "topics": ["sales_onboarding", "kpi", "objections", "crm"]},
    {"full_name": "Natalia Moroz", "role": "HR-директор", "team": "Люди", "email": "natalia@orynt.demo", "topics": ["employee_experience", "retention", "onboarding_quality"]},
    {"full_name": "Victor Petrenko", "role": "DevOps Engineer", "team": "Infrastructure", "email": "victor@orynt.demo", "topics": ["deployment", "kubernetes", "staging", "rollback"]},
    {"full_name": "Katia Shevchenko", "role": "Senior AE", "team": "Продажі", "email": "katia@orynt.demo", "topics": ["demo", "pricing", "competitive_intel", "enterprise_deals"]},
    {"full_name": "Ana Kovalenko", "role": "QA Engineer", "team": "Payments", "email": "ana@orynt.demo", "topics": ["testing", "qa", "bug_reporting"]},
]


SALES_PEOPLE = [
    person
    for person in PEOPLE
    if person["email"] in {"oleg@orynt.demo", "natalia@orynt.demo", "katia@orynt.demo"}
]


MARINA_TASKS = [
    {"week": 1, "day": 1, "title": "Переглянути базу онбордингу продажів", "description": "Переглянути очікування щодо ICP, outreach, CRM і роботи із запереченнями, зафіксовані під час kickoff.", "type": "reading", "status": "done", "priority": "high"},
    {"week": 1, "day": 2, "title": "Прочитати процес продажів і регламент KPI", "description": "Зрозуміти лідогенерацію, діагностичні дзвінки, потік комерційних пропозицій і щоденні норми активності.", "type": "reading", "status": "done", "priority": "high"},
    {"week": 1, "day": 3, "title": "Написати першу послідовність холодного outreach", "description": "Підготувати три короткі повідомлення для Facebook, Instagram і LinkedIn на основі ICP компанії.", "type": "outreach", "status": "done", "priority": "high"},
    {"week": 1, "day": 4, "title": "Точно заповнювати щоденну таблицю KPI", "description": "Заповнити план/факт для кожного джерела й додати посилання на репости.", "type": "crm", "status": "blocked", "priority": "high"},
    {"week": 2, "day": 1, "title": "Провести role-play із запереченням: занадто дорого", "description": "Потренувати перехід від ціни до вартості поточної проблеми.", "type": "role_play", "status": "in_progress", "priority": "high"},
    {"week": 2, "day": 2, "title": "Підготувати brief для діагностичного дзвінка", "description": "Використати поля: проблема, бюджет, роль у прийнятті рішення, дедлайн і поточне рішення.", "type": "discovery", "status": "todo", "priority": "medium"},
    {"week": 2, "day": 3, "title": "Створити cadence подальших дій для теплих лідів", "description": "Підготувати follow-up через 24 год, 3 дні й 7 днів із доданою цінністю.", "type": "follow_up", "status": "todo", "priority": "medium"},
    {"week": 3, "day": 1, "title": "Поспостерігати за презентацією пропозиції Katia", "description": "Подивитися, як досвідчений продавець працює із запереченнями й підтверджує наступні кроки.", "type": "shadowing", "status": "todo", "priority": "medium"},
]


TANYA_TASKS = [
    {"week": 1, "day": 1, "title": "Налаштувати локальне development environment", "description": "Клонувати repos, встановити dependencies, запустити backend tests локально.", "type": "setup", "status": "done", "priority": "high"},
    {"week": 1, "day": 2, "title": "Простежити request flow у payment-gateway", "description": "Провести один зовнішній API call через FastAPI, Kafka і PostgreSQL.", "type": "architecture", "status": "done", "priority": "high"},
    {"week": 1, "day": 3, "title": "Прочитати чекліст code review", "description": "Зіставити кожен пункт чекліста з першою чернеткою PR.", "type": "reading", "status": "done", "priority": "medium"},
    {"week": 2, "day": 1, "title": "Відкрити перший backend PR", "description": "Виправити невелику проблему validation у payment-gateway і запросити два reviews.", "type": "development", "status": "in_progress", "priority": "high"},
    {"week": 2, "day": 2, "title": "Опрацювати коментарі до PR", "description": "Закрити питання щодо API docs, unit tests і migrations.", "type": "code_review", "status": "in_progress", "priority": "high"},
    {"week": 2, "day": 4, "title": "Підготувати чекліст staging deployment", "description": "Пояснити deploy, monitor і rollback steps перед роботою з production.", "type": "deployment", "status": "todo", "priority": "high"},
    {"week": 3, "day": 1, "title": "Поспостерігати за production deployment", "description": "Приєднатися до Victor для rollout status, monitoring у Grafana і rollback drill.", "type": "deployment", "status": "todo", "priority": "medium"},
    {"week": 3, "day": 3, "title": "Задокументувати нотатки з першого PR", "description": "Зафіксувати architecture notes і gotchas для наступного новачка.", "type": "documentation", "status": "todo", "priority": "medium"},
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
        "team": newcomer.team if newcomer else "Продажі",
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


def _create_documents(db: Session, *, include_backend: bool = True) -> list[Document]:
    docs: list[Document] = []
    source_docs = [*SALES_DOCUMENTS, *BACKEND_DOCUMENTS] if include_backend else SALES_DOCUMENTS
    for doc_data in source_docs:
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


def _create_sales_arena_bot(
    db: Session,
    *,
    mentor: User,
    newcomer: NewcomerProfile,
    docs: list[Document],
) -> ArenaScenario:
    scenario = ArenaScenario(
        mentor_id=mentor.id,
        audience_newcomer_id=newcomer.id,
        title="Marina personal bot - pricing objection recovery",
        conversation_type="objection_handling",
        difficulty=2,
        persona={
            "name": "Iryna D.",
            "role": "Founder of a warm lead company",
            "mood": "interested but price-sensitive",
            "background": "She already likes the product, but compares it with a cheaper agency.",
        },
        goal_text=(
            "Practice moving from a price objection into quantified business value, then agree "
            "on a concrete next step without discounting too early."
        ),
        success_criteria=[
            "Acknowledge the concern without defending the price.",
            "Ask one diagnostic question before pitching.",
            "Connect the offer to the cost of the current problem.",
            "Close with a specific next step in CRM.",
        ],
        kb_source_ids=[doc.id for doc in docs],
        allow_live_coaching=True,
        is_personal_bot=True,
        description=(
            "Sales-only Arena bot for Marina, generated from the sales playbook, KPI docs, "
            "CRM discipline and objection-handling sources."
        ),
        cover_emoji="AI",
    )
    db.add(scenario)
    db.flush()
    return scenario


def _create_ai_question(
    db: Session,
    *,
    newcomer: NewcomerProfile,
    question: str,
    answer: str,
    source_doc: Document | None,
) -> AIQuestion:
    topic = classify_topic(f"{question} {answer}")
    if topic == "unknown" and any(token in f"{question} {answer}".lower() for token in ["crm", "kpi"]):
        topic = "sales"

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
            topic=topic,
            metadata_json={
                "question": question,
                "source_titles": [source_doc.title] if source_doc else [],
                "top_k": 1,
            },
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


def _delete_demo_data(db: Session) -> None:
    for model in [
        Notification,
        ArenaMessage,
        ArenaSession,
        ArenaScenario,
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
        TaskComment,
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


def reset_demo_data(db: Session) -> dict:
    try:
        _delete_demo_data(db)
        db.commit()
        return seed_demo_data(db=db)
    except Exception:
        db.rollback()
        raise


def reset_sales_demo_data(db: Session) -> dict:
    try:
        _delete_demo_data(db)
        db.commit()
        return seed_sales_demo_data(db=db)
    except Exception:
        db.rollback()
        raise


def seed_sales_demo_data(db: Session) -> dict:
    existing_mentor = db.query(User).filter(User.email == "oleg@orynt.demo").first()
    if existing_mentor:
        return _seed_response(db, already_seeded=True)

    mentor = User(email="oleg@orynt.demo", full_name="Oleg Bondarenko", role="mentor")
    marina_user = User(email="marina@orynt.demo", full_name="Marina Kovalenko", role="newcomer")
    db.add_all([mentor, marina_user])
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
    db.add(marina)
    db.flush()

    for person in SALES_PEOPLE:
        db.add(PersonContact(**person))
    db.flush()

    docs = _create_documents(db, include_backend=False)

    marina_plan, marina_tasks = _create_plan(
        db,
        newcomer=marina,
        mentor=mentor,
        title="Marina Kovalenko - sales onboarding",
        description=(
            "30-day sales ramp focused on ICP, outreach, CRM hygiene, KPI reporting, "
            "discovery calls, proposals and objection handling."
        ),
        goal=(
            "Prepare Marina to handle real cold and warm leads, keep clean CRM updates, "
            "and practice customer conversations in Arena before live calls."
        ),
        tasks=MARINA_TASKS,
    )

    blocked_task = next(task for task in marina_tasks if task.status == "blocked")
    role_play_task = next(task for task in marina_tasks if task.task_type == "role_play")
    db.add(
        BlockedReport(
            newcomer_id=marina.id,
            task_id=blocked_task.id,
            user_id=marina_user.id,
            blocker_type="crm_kpi_confusion",
            details=(
                "Marina is not yet confident translating Instagram/Facebook conversations "
                "into clean plan-versus-actual KPI rows."
            ),
            ai_suggestion=(
                "Run a short CRM walkthrough with one lead per channel, then ask Marina "
                "to update the same KPI tracker without mentor prompts."
            ),
            status="open",
        )
    )

    crm_signal = AISignal(
        newcomer_id=marina.id,
        signal_type="sales_crm_kpi_attention",
        severity="high",
        tone="attention",
        confidence=0.91,
        score=0.84,
        title="CRM/KPI discipline needs mentor attention",
        description=(
            "Marina completed outreach basics, but the blocked task and repeated KPI questions "
            "show she needs a concrete sales reporting walkthrough."
        ),
        evidence=(
            "- KPI task is blocked.\n"
            "- Questions cluster around daily activity tracking.\n"
            "- CRM examples are needed before scaling outreach volume."
        ),
        suggested_action=(
            "Pair for 15 minutes on clean CRM rows, then apply the pending week-2 plan adjustment."
        ),
        status="open",
        occurrence_count=3,
        target_task_id=blocked_task.id,
    )
    arena_signal = AISignal(
        newcomer_id=marina.id,
        signal_type="arena_low_value_framing",
        severity="medium",
        tone="attention",
        confidence=0.87,
        score=0.73,
        title="Arena practice should focus on pricing objections",
        description=(
            "Marina is ready for sales role-play, but needs a focused Arena bot before live "
            "price and timing objections."
        ),
        evidence=(
            "- Objection-handling task is still in progress.\n"
            "- Sales docs emphasize value framing before discounting.\n"
            "- Mentor can review Arena performance before assigning live calls."
        ),
        suggested_action=(
            "Use the Marina personal bot, then convert the debrief into one next sales task."
        ),
        status="open",
        occurrence_count=2,
        target_task_id=role_play_task.id,
    )
    db.add_all([crm_signal, arena_signal])
    db.flush()

    db.add(
        PlanAdjustmentSuggestion(
            newcomer_id=marina.id,
            plan_id=marina_plan.id,
            signal_id=crm_signal.id,
            title="Tighten Marina week 2 around CRM, KPI and sales role-play",
            reason=(
                "The sales-only reset keeps the demo centered on Marina's pipeline readiness: "
                "clean CRM rows, value-framed objections, and confident discovery next steps."
            ),
            suggested_changes=[
                {
                    "action": "add_task",
                    "title": "CRM walkthrough with one lead per channel",
                    "description": "Turn one Instagram, Facebook and Email lead into clean KPI tracker rows.",
                    "task_type": "crm",
                    "week_number": 2,
                    "day_number": 2,
                    "priority": "high",
                    "success_criteria": "Marina updates all KPI rows without mentor corrections.",
                },
                {
                    "action": "add_task",
                    "title": "Arena pricing objection role-play",
                    "description": "Complete the personal bot scenario and capture one improved response.",
                    "task_type": "arena",
                    "week_number": 2,
                    "day_number": 3,
                    "priority": "high",
                    "success_criteria": "Marina frames value before discussing price or timing.",
                },
            ],
            status="pending",
            target_scope="week",
        )
    )

    db.add(
        ProgressSnapshot(
            newcomer_id=marina.id,
            week_number=2,
            completed_tasks=3,
            blocked_tasks=1,
            open_signals=2,
            progress_percent=38,
            strengths=["ICP basics", "cold outreach drafts", "discovery preparation"],
            gaps=["CRM hygiene", "plan/fact KPI reporting", "price objection framing"],
            mentor_notes="Sales-only demo: keep Marina on CRM proof, objection practice and Arena coaching.",
        )
    )

    questions_created = 0
    price_doc = _find_doc(docs, "Price List")
    company_doc = _find_doc(docs, "Company Information")
    question_payloads = [
        (
            "What is the daily outreach target for a sales manager?",
            "Daily plan: Freelancehunt 20, Instagram 30, Facebook 40, Email 20, LinkedIn 10, Telegram 5; 125 contacts total.",
            docs[3] if len(docs) > 3 else docs[0],
        ),
        (
            "How should I respond when a lead says the offer is too expensive?",
            "Acknowledge the concern, ask a diagnostic question, then connect the offer to the business cost of the current problem before discussing discounting.",
            docs[-2] if len(docs) > 1 else docs[0],
        ),
        (
            "What belongs in a discovery call brief?",
            "Capture the customer's goals, current state, budget, problem, decision process and concrete next step.",
            docs[0],
        ),
        (
            "What price should I quote for a sales team that needs Arena?",
            "Use Growth as the default recommendation for sales teams: USD 2,800 per month, including Arena role-play, AI signal detection, course generation and priority support.",
            price_doc or docs[-2],
        ),
        (
            "Can I discount the price if the lead says it is too expensive?",
            "Do not discount before discovery. Annual prepayment can receive up to 10%; larger discounts require approval from Oleg Bondarenko and Finance.",
            price_doc or docs[-2],
        ),
        (
            "What does Orynt do in one sentence?",
            "Orynt.ai builds AI onboarding software that combines company knowledge, plans, courses, assessments, mentor dashboards, AI signals and Arena simulations to help teams ramp faster.",
            company_doc or docs[-1],
        ),
        (
            "Which company proof points should I mention to a Head of Sales?",
            "Lead with faster ramp, better pipeline quality, manager leverage, realistic Arena practice before live calls, and early detection of confusion or blockers.",
            company_doc or docs[-1],
        ),
    ]
    for question, answer, source_doc in question_payloads:
        _create_ai_question(
            db,
            newcomer=marina,
            question=question,
            answer=answer,
            source_doc=source_doc,
        )
        questions_created += 1

    course = _create_course(
        db,
        newcomer=marina,
        mentor=mentor,
        plan=marina_plan,
        title="First sales wins for Marina",
        summary="A focused sales course covering outreach, CRM discipline, KPI reporting, objection handling and Arena practice.",
        role_target="sales_manager",
        source_docs=docs,
        lessons=[
            {
                "title": "Convert outreach activity into clean CRM proof",
                "summary": "Move from raw channel activity to plan/fact KPI rows Oleg can trust.",
                "body": (
                    "Start with the KPI channel, then record each meaningful dialogue with source, "
                    "status, next step and blocker. Separate activity KPIs from outcome KPIs."
                ),
                "takeaways": [
                    "Track channel activity every day.",
                    "Every warm lead needs one next step.",
                    "CRM proof should be reviewable without extra explanation.",
                ],
            },
            {
                "title": "Practice pricing objections in Arena",
                "summary": "Use the personal bot to rehearse price and timing objections before live outreach.",
                "body": (
                    "Do not discount after the first objection. Acknowledge the concern, ask one "
                    "diagnostic question, then reframe around the cost of the current business problem."
                ),
                "video_url": "https://www.youtube.com/watch?v=X7oxXhfwv40",
                "takeaways": [
                    "Acknowledge before reframing.",
                    "Ask before pitching.",
                    "Close with a concrete next step.",
                ],
            },
        ],
    )

    _create_sales_arena_bot(db, mentor=mentor, newcomer=marina, docs=docs)

    now = datetime.now(timezone.utc)
    meetings = [
        ScheduledMeeting(
            newcomer_id=marina.id,
            organizer_user_id=mentor.id,
            plan_id=marina_plan.id,
            task_id=blocked_task.id,
            signal_id=crm_signal.id,
            title="Sales CRM unblock",
            agenda="Turn three real leads into clean plan/fact KPI rows and confirm the reporting habit.",
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
            task_id=role_play_task.id,
            signal_id=arena_signal.id,
            title="Arena debrief: pricing objection",
            agenda="Review Marina's personal bot practice and turn the debrief into one concrete sales task.",
            starts_at=now + timedelta(days=3, hours=1),
            ends_at=now + timedelta(days=3, hours=1, minutes=45),
            attendee_emails=[mentor.email, marina_user.email, "katia@orynt.demo"],
            teams_join_url="https://teams.microsoft.com/l/demo-marina-arena",
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
                "Sales-only reset: Marina is progressing on outreach, but needs mentor focus on CRM/KPI proof "
                "and Arena practice for pricing objections."
            ),
            highlights=[
                "Marina completed ICP basics and first outreach drafts.",
                "The course and Arena bot are ready for sales-specific coaching.",
            ],
            risks=[
                "CRM/KPI reporting is still blocked.",
                "Pricing objection framing needs practice before live calls.",
            ],
            recommended_actions=[
                "Run the sales CRM unblock meeting.",
                "Ask Marina to complete the personal Arena bot before the next outreach block.",
            ],
        )
    )

    db.commit()

    return _seed_response(
        db,
        documents_created=len(docs),
        courses_created=1 if course else 0,
        tasks_created=len(marina_tasks),
        questions_created=questions_created,
        meetings_created=len(meetings),
        signals_created=2,
        blocked_reports_created=1,
    )


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
        job_title="Менеджер з продажів / BDR",
        seniority="Junior",
        team="Продажі",
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
        title="Marina Kovalenko - онбординг продажів/BDR",
        description="30-денний план із фокусом на процес продажів, щоденну дисципліну KPI, чистоту CRM і практику заперечень.",
        goal="Підготувати Marina до роботи з реальними холодними й теплими лідами та чистими оновленнями CRM.",
        tasks=MARINA_TASKS,
    )
    tanya_plan, tanya_tasks = _create_plan(
        db,
        newcomer=tanya,
        mentor=mentor,
        title="Tanya Petrova - онбординг Backend Developer",
        description="30-денний план із фокусом на архітектуру payments, перший PR, якість review і готовність до deployment.",
        goal="Зробити Tanya впевненою у випуску backend PR і безпечній участі в staging deployment.",
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
                "Marina не впевнена, як переносити розмови з Instagram/Facebook у KPI tracker "
                "і вже два дні не оновлювала рядки план/факт."
            ),
            ai_suggestion=(
                "Заплануйте 15-хвилинний walkthrough із чистоти CRM, потім дайте Marina по одному чистому прикладу "
                "для кожного джерела перед наступним блоком outreach."
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
        title="Цикл PR review потребує уваги ментора",
        description="Tanya відкрила перший backend PR, але коментарі review концентруються навколо tests і API documentation.",
        evidence="- Перший PR у процесі.\n- Чекліст code review було відкрито.\n- Питання згадують tests, docs і очікування щодо migration.",
        suggested_action="Попрацюйте разом 20 хвилин над одним коментарем review і попросіть Tanya оновити чекліст PR перед повторним запитом review.",
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
        title="Готовність до deployment ще не підтверджена",
        description="Tanya прочитала посібник із deployment, але ще не практикувала rollout status, monitoring або rollback.",
        evidence="- Завдання з deployment checklist досі todo.\n- AI-питання фокусуються на staging, approvals і rollback.\n- Спостереження за production deploy заплановане на цей тиждень.",
        suggested_action="Залиште спостереження за production deploy, але додайте staging dry run з Victor перед будь-якою відповідальністю за release.",
        status="open",
        occurrence_count=4,
        target_task_id=next(
            task.id
            for task in tanya_tasks
            if task.title.startswith("Prepare staging") or task.title.startswith("Підготувати чекліст staging")
        ),
    )
    db.add_all([tanya_signal_1, tanya_signal_2])
    db.flush()

    db.add(
        PlanAdjustmentSuggestion(
            newcomer_id=marina.id,
            plan_id=marina_plan.id,
            signal_id=None,
            title="Адаптувати тиждень 2 Marina: CRM і відновлення після заперечень",
            reason=(
                "Marina заблокована на дисципліні KPI/CRM і досі невпевнена із ціновими запереченнями. "
                "Зменшення нового outreach на один день створить простір для практики й наведення ладу."
            ),
            suggested_changes=[
                {
                    "action": "add_task",
                    "title": "Walkthrough із чистоти CRM з Oleg",
                    "description": "Пройти один Instagram, один Facebook і один Email лід від контакту до фактичного рядка KPI.",
                    "task_type": "crm",
                    "week_number": 2,
                    "day_number": 2,
                    "priority": "high",
                    "success_criteria": "Marina може оновити всі рядки KPI без виправлень ментора.",
                },
                {
                    "action": "add_task",
                    "title": "Практика заперечень: дорого і не зараз",
                    "description": "Провести два role plays з AI-клієнтом за playbook заперечень.",
                    "task_type": "role_play",
                    "week_number": 2,
                    "day_number": 3,
                    "priority": "high",
                    "success_criteria": "Marina опрацьовує обидва заперечення через framing вартості проблеми.",
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
                strengths=["Основи ICP", "чернетки холодних повідомлень"],
                gaps=["Дисципліна CRM", "план/факт KPI", "цінові заперечення"],
                mentor_notes="Marina має добрий потенціал, але потребує конкретного прикладу CRM перед збільшенням outreach.",
            ),
            ProgressSnapshot(
                newcomer_id=tanya.id,
                week_number=2,
                completed_tasks=3,
                blocked_tasks=0,
                open_signals=2,
                progress_percent=52,
                strengths=["простеження architecture", "відповідальність за перший PR"],
                gaps=["глибина review checklist", "впевненість у deployment"],
                mentor_notes="Tanya добре просувається; сигнали потребують уваги, але це не блокери.",
            ),
        ]
    )

    questions_created = 0
    for payload in [
        (
            marina,
            "Яка денна норма контактів для менеджера з продажів?",
            "Денний план: Freelancehunt 20, Instagram 30, Facebook 40, Email 20, LinkedIn 10, Telegram 5; всього 125 контактів.",
            _find_doc(docs, "Щоденка"),
        ),
        (
            marina,
            "Що відповідати, якщо клієнт каже що дорого?",
            "Не знижуйте ціну одразу. Переведіть розмову на вартість поточної проблеми і порахуйте час ментора або втрачений результат.",
            _find_doc(docs, "Заперечення у продажах"),
        ),
        (
            marina,
            "Що має бути в діагностичному дзвінку?",
            "Потрібно зібрати цілі, стан бізнесу, бюджет, проблеми, потенціал клієнта і домовитись про наступний крок.",
            _find_doc(docs, "Регламент"),
        ),
        (
            tanya,
            "Як мені розгорнути свої зміни на staging?",
            "Зробіть merge після 2 approvals, дочекайтеся CI, перевірте staging, потім дотримуйтеся посібника з deployment для готовності до production.",
            _find_doc(docs, "deployment"),
        ),
        (
            tanya,
            "Хто схвалює зміни в payment-gateway?",
            "Для змін у payment-gateway обов'язкове схвалення tech lead; Victor допомагає з питаннями infrastructure.",
            _find_doc(docs, "Architecture"),
        ),
        (
            tanya,
            "Що має бути в описі мого PR?",
            "Додайте, що змінилося, як це тестувати, і Jira link. Переконайтеся, що tests проходять, а API changes задокументовані.",
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
            title="Перші перемоги менеджера з продажів",
            summary="Короткий рольовий курс для Marina про outreach, дисципліну CRM, звітність KPI і роботу із запереченнями.",
            role_target="sales_manager",
            source_docs=[
                doc
                for doc in [
                    _find_doc(docs, "Основи продажів"),
                    _find_doc(docs, "Заперечення у продажах"),
                    _find_doc(docs, "KPI"),
                ]
                if doc
            ],
            lessons=[
                {
                    "title": "Перенести щоденну активність у чисті докази CRM",
                    "summary": "Перетворити outreach-активність на рядки план/факт, нотатки щодо лідів і наступні кроки, яким Oleg може довіряти.",
                    "body": (
                        "Почніть із KPI каналу, потім фіксуйте кожен змістовний діалог із джерелом, статусом, "
                        "наступним кроком і блокером. Чистий запис CRM відповідає, хто цей лід, чому він підходить, що "
                        "сталося і що буде далі."
                    ),
                    "takeaways": [
                        "Відстежуйте активність каналів щодня.",
                        "Відокремлюйте activity KPI від outcome KPI.",
                        "Кожен теплий лід потребує наступного кроку.",
                    ],
                },
                {
                    "title": "Role-play з опрацювання заперечень",
                    "summary": "Потренуйте заперечення щодо ціни, таймінгу й конкурентів перед live outreach.",
                    "body": (
                        "Не давайте знижку після першого цінового заперечення. Переформулюйте розмову навколо вартості "
                        "поточної проблеми онбордингу, часу ментора й затриманої продуктивності."
                    ),
                    "video_url": "https://www.youtube.com/watch?v=X7oxXhfwv40",
                    "takeaways": [
                        "Визнайте занепокоєння.",
                        "Поставте одне діагностичне питання.",
                        "Поверніться до бізнес-впливу.",
                    ],
                },
            ],
        ),
        _create_course(
            db,
            newcomer=tanya,
            mentor=mentor,
            plan=tanya_plan,
            title="Готовність Backend Developer до release",
            summary="Сфокусований курс для Tanya про архітектуру payments, чекліст PR і staging deployment flow.",
            role_target="backend_developer",
            source_docs=[
                doc
                for doc in [
                    _find_doc(docs, "Architecture"),
                    _find_doc(docs, "code review"),
                    _find_doc(docs, "deployment"),
                ]
                if doc
            ],
            lessons=[
                {
                    "title": "Мапа архітектури Payments",
                    "summary": "Зрозуміти сервіси, яких торкається Tanya, перед зміною поведінки payment-gateway.",
                    "body": (
                        "Зміни в Payments зазвичай перетинають межі сервісів. Перед coding визначте owning "
                        "service, event contracts, вплив на database і чи потрібне схвалення tech lead."
                    ),
                    "takeaways": [
                        "Зміни в payment-gateway потребують схвалення tech lead.",
                        "Kafka events несуть більшість внутрішньої комунікації сервісів.",
                        "Документуйте API або migration changes у PR.",
                    ],
                },
                {
                    "title": "Відкрити backend PR, готовий до review",
                    "summary": "Підготувати checklist, test notes і план перевірки staging перед запитом review.",
                    "body": (
                        "Готовий до review PR містить, що змінилося, як це тестувати, Jira link, migration notes "
                        "і доказ, що CI та релевантні unit tests пройшли."
                    ),
                    "video_url": "https://www.youtube.com/watch?v=X7oxXhfwv40",
                    "takeaways": [
                        "Використовуйте чекліст PR перед запитом review.",
                        "Перевіряйте staging після CI deploy.",
                        "Ескалуйте невпевненість щодо deployment завчасно.",
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
            title="Розблокування чистоти CRM",
            agenda="Перенести три реальні ліди в рядки план/факт KPI і підтвердити звичку звітності.",
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
            title="Role-play із заперечень: ціна і таймінг",
            agenda="Потренувати два сценарії AI-клієнта з playbook заперечень.",
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
            title="Парне review першого PR",
            agenda="Разом закрити один коментар щодо test і один коментар щодо API documentation.",
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
            title="Dry run staging deployment",
            agenda="Пройти rollout status, monitoring checklist і rollback drill з Victor.",
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
                "Marina потрібна допомога з CRM/KPI перед масштабуванням outreach. Tanya рухається добре, "
                "але PR review і готовність до deployment потребують уваги цього тижня."
            ),
            highlights=[
                "Marina завершила ICP і підготовку outreach.",
                "Tanya простежила архітектуру payments і відкрила перший PR.",
            ],
            risks=[
                "Marina заблокована на звітності план/факт KPI.",
                "Tanya ще не підтвердила готовність до deployment.",
            ],
            recommended_actions=[
                "Провести розблокування чистоти CRM для Marina.",
                "Залишити staging dry run Tanya з Victor.",
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
