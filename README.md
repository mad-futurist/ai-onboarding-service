<div align="center">

### 🌐 Language / Мова

[🇬🇧 English](#english-version) &nbsp;·&nbsp; [🇺🇦 Українська](#українська-версія)

</div>

---

<a name="english-version"></a>

<p align="center">
  <img src="docs/logo.svg" alt="ReadySet.AI" width="320" />
</p>

<h1 align="center" style="color:#CC5500">ReadySet.AI — Onboarding Service · Backend</h1>

<p align="center">
  <a href="https://github.com/mad-futurist/ai-onboarding-service"><img alt="backend" src="https://img.shields.io/badge/Backend-FastAPI-FF8C00?style=for-the-badge&labelColor=3D2000"/></a>
  <a href="https://github.com/mad-futurist/ai-onboarding-service-frontend"><img alt="frontend" src="https://img.shields.io/badge/Frontend-Next.js%2016-CC5500?style=for-the-badge&labelColor=3D2000"/></a>
  <a href="https://ai-onboarding-service.onrender.com"><img alt="api" src="https://img.shields.io/badge/API-Render-FFAA55?style=for-the-badge&labelColor=3D2000"/></a>
</p>

<p align="center">
  <b>Backend repo:</b> <a href="https://github.com/mad-futurist/ai-onboarding-service">github.com/mad-futurist/ai-onboarding-service</a><br/>
  <b>Frontend repo:</b> <a href="https://github.com/mad-futurist/ai-onboarding-service-frontend">github.com/mad-futurist/ai-onboarding-service-frontend</a><br/>
  <b>Live API:</b> <a href="https://ai-onboarding-service.onrender.com">ai-onboarding-service.onrender.com</a> &nbsp;·&nbsp; <b>Live app:</b> <a href="https://ai-onboarding-service-frontend.vercel.app">ai-onboarding-service-frontend.vercel.app</a>
</p>

---

> **ReadySet.AI Backend** is a FastAPI service that powers an AI onboarding assistant. It turns company documentation into a role-aware knowledge engine, generates 30/60/90 plans grounded in the docs, listens to behavioral signals, and keeps a mentor in the loop on every AI action.

This repository is the **backend**. The Next.js frontend lives in [`ai-onboarding-service-frontend`](https://github.com/mad-futurist/ai-onboarding-service-frontend).

---

## 🎬 Run the demo

The demo is driven from the **frontend**: open the live app, go to the **Demo** page, and click **"Start demo mode"**. The demo calls real backend endpoints (no mock layer) — make sure the backend is running and reachable.

---

## ⚡ Killer features

| # | Feature | Why it matters |
|---|---|---|
| 1 | **AI Copilot under human control** | Every AI output is persisted as an editable, reviewable artifact (plans, adjustments, course drafts, signals). The API forces a `status` lifecycle: `proposed → reviewed → applied`. No silent auto-apply. |
| 2 | **AI live (streaming)** | Plan generation, Ask AI, and signal explanations stream incrementally — frontend renders tokens as they arrive. |
| 3 | **Plan generation for role + documents** | `ai_plan_service` composes a 30/60/90 plan phase by phase from the newcomer's role profile and a selected subset of knowledge-base documents. Prompts are constrained and outputs validated against pydantic schemas. |
| 4 | **Listening signals — role first, then questioning** | `ai_signals` start from the role's expected milestones; then layer behavioral signals (repeated questions, blocked tasks, review patterns). Every signal stores its **evidence chunks** so the mentor can audit. |
| 5 | **AI signals with evidence scoring** | `e75c48a6f8c0_add_scoring_fields_to_ai_signals` — signals carry weighted scores and reference the source events that triggered them. |
| 6 | **Course generation with mentor control** | `courses` route generates a short course from mentor-selected sources, persists a draft, requires mentor approval before publishing. |
| 7 | **RAG Ask AI** | `knowledge` + `document_chunks` + `embedding_service`: chunked docs, pgvector cosine search, prompt-grounded answers with source citations returned in the response payload. |

---

## 🧩 Classic features

- **Users, people, newcomers** — accounts, role profiles, mentor ↔ newcomer relationships.
- **Onboarding plans & tasks** — phases (1 to 24+), tasks, success criteria, status transitions.
- **Kanban / mentor review queue** — `mentor_kanban` for queueing newcomer submissions.
- **Progress snapshots** — `progress_snapshots` track momentum over time.
- **Document service** — upload, store, chunk, embed; typed documents (HR, process, technical…).
- **Notifications** — `notifications` route, role-scoped.
- **Onboarding events** — full event log (`onboarding_events`) for analytics and signals.
- **Mentor digests** — periodic AI-written summaries for the mentor.

---

## ✨ Additional features

- **Calendar / meetings** — `meetings` route, shared between mentor and newcomer.
- **Video in courses** — courses can embed video lessons (lesson notes service).
- **Teams / Slack integration** *(roadmap)*.
- **Mind map data** — Ask AI responses include a graph payload consumed by the frontend's `@xyflow/react` renderer.
- **Skill checks / assessments** — `assessments` route generates a quick test for a new hire; results trigger plan generation.
- **Blocked reports** — newcomers can flag a task as blocked; surfaces in mentor signals.
- **Company onboarding gaps** — `company_gaps` aggregates patterns across newcomers.

---

## 🛠 Technical solutions

### Stack

| Layer | Tech |
|---|---|
| Web framework | **FastAPI** + pydantic v2 |
| ORM / DB | **SQLAlchemy 2** + **PostgreSQL 16** + **pgvector** |
| Migrations | **Alembic** |
| LLM | **OpenAI** (chat + embeddings) via `llm_service` |
| Embeddings store | `pgvector` (cosine), `document_chunks` table |
| Server | **Uvicorn** (ASGI), CORS middleware for the Next.js host |
| Container | `docker-compose.yml` (pgvector/pgvector:pg16) |
| Deploy | **Render** (web service) |

### RAG pipeline

```
Document upload
   └─► chunking_service        (token-aware splits, metadata-preserving)
         └─► embedding_service (OpenAI embeddings → pgvector)
                  └─► retrieval (cosine kNN over document_chunks)
                            └─► prompt assembly (system + chunks + user)
                                      └─► llm_service (chat + streaming)
                                              └─► structured output
                                                    (validated by pydantic)
                                                       └─► persisted artifact
                                                             (status=proposed)
                                                                  └─► mentor review
```

Every AI artifact (plan, course, signal, adjustment, answer) carries:
- the **prompt template** id (`app/prompts/*.txt`),
- the **source chunks** used,
- a **status** (`proposed | reviewed | applied | rejected`),
- a **mentor decision** field once acted upon.

This is what makes the system auditable end-to-end.

### Architecture

```
[ Browser ]
     │
     ▼
[ Next.js (Vercel) ]  ── /api/* proxy ──►  [ FastAPI (Render) ]
                                                  │
                                                  ├─ PostgreSQL + pgvector
                                                  └─ OpenAI (chat + embeddings)
```

The frontend never sees the OpenAI key. All retrieval, prompt assembly, and streaming happen in the backend.

### Module layout

```
app/
├── main.py                    # FastAPI app + CORS + route registration
├── core/                      # config, settings, security helpers
├── db/                        # SQLAlchemy base, session, engine
├── models/                    # ORM models (newcomer, plan, task, ai_signal, …)
├── schemas/                   # pydantic IO schemas
├── api/routes/                # FastAPI routers (one per resource)
├── services/
│   ├── ai_plan_service.py     # plan generation (role + docs → phases/tasks)
│   ├── llm_service.py         # OpenAI client wrapper + streaming
│   ├── embedding_service.py   # OpenAI embeddings → pgvector
│   ├── chunking_service.py    # token-aware document splitter
│   ├── knowledge_recommendation_service.py  # related-doc surfacing
│   ├── company_gap_service.py # cross-newcomer pattern detection
│   ├── mentor_dashboard_service.py
│   ├── mentor_digest_service.py
│   ├── progress_snapshot_service.py
│   ├── task_detail_service.py
│   ├── person_contact_service.py
│   └── event_logger.py        # onboarding events firehose
└── prompts/                   # versioned prompt templates (plain .txt)
```

### Key routes

`users`, `people`, `newcomers`, `documents`, `onboarding_plans`, `tasks`, `ai`, `ai_signals`, `onboarding_events`, `plan_adjustments`, `mentor_dashboard`, `newcomer_dashboard`, `blocked_reports`, `company_gaps`, `mentor_digests`, `mentor_actions`, `progress_snapshots`, `onboarding_reflections`, `newcomer_kb`, `user_story`, `knowledge`, `demo`, `courses`, `meetings`, `lesson_notes`, `assessments`, `notifications`, `mentor_kanban`.

---

## 🎨 Brand palette

| Token | Hex |
|---|---|
| Blaze Orange | `#CC5500` |
| Dark Orange | `#FF8C00` |
| Sandy Orange | `#FFAA55` |
| Peach | `#FFD199` |
| Cream | `#FFF0E0` |
| Warm White | `#FFF7F0` |
| Warm Brown | `#7A5030` |
| Deep Brown | `#3D2000` |
| Obsidian | `#1A0E00` |

---

## 🚀 Run locally

```powershell
# 1. Postgres + pgvector
docker compose up -d

# 2. Python env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Env vars
cp .env.example .env
# fill in:
#   APP_NAME=ReadySet.AI
#   APP_ENV=local
#   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_onboarding
#   OPENAI_API_KEY=sk-...
#   OPENAI_MODEL=gpt-4o-mini
#   EMBEDDING_MODEL=text-embedding-3-small
#   CORS_ORIGINS=http://localhost:3000

# 4. Migrations
alembic upgrade head

# 5. Run
uvicorn app.main:app --reload
# API → http://127.0.0.1:8000  ·  docs → http://127.0.0.1:8000/docs
```

Then start the frontend (see the [frontend README](https://github.com/mad-futurist/ai-onboarding-service-frontend#-run-locally)).

---

## 🌍 Run in production

Deployed on **Render**.

1. **Web Service (Python)**
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. **Database** — provision Postgres and enable the extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. **Environment**
   ```
   APP_NAME=ReadySet.AI
   APP_ENV=production
   DATABASE_URL=postgresql+psycopg://...
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   EMBEDDING_MODEL=text-embedding-3-small
   CORS_ORIGINS=https://ai-onboarding-service-frontend.vercel.app
   ```
4. **Migrations** — run `alembic upgrade head` as a release/predeploy command.

Live API: [ai-onboarding-service.onrender.com](https://ai-onboarding-service.onrender.com).

---

<div align="right">

[🔝 Back to top](#english-version) &nbsp;·&nbsp; [🇺🇦 Українська](#українська-версія)

</div>

---
---

<a name="українська-версія"></a>

<p align="center">
  <img src="docs/logo.svg" alt="ReadySet.AI" width="320" />
</p>

<h1 align="center" style="color:#CC5500">ReadySet.AI — Сервіс онбордингу · Backend</h1>

<p align="center">
  <a href="https://github.com/mad-futurist/ai-onboarding-service"><img alt="backend" src="https://img.shields.io/badge/Backend-FastAPI-FF8C00?style=for-the-badge&labelColor=3D2000"/></a>
  <a href="https://github.com/mad-futurist/ai-onboarding-service-frontend"><img alt="frontend" src="https://img.shields.io/badge/Frontend-Next.js%2016-CC5500?style=for-the-badge&labelColor=3D2000"/></a>
  <a href="https://ai-onboarding-service.onrender.com"><img alt="api" src="https://img.shields.io/badge/API-Render-FFAA55?style=for-the-badge&labelColor=3D2000"/></a>
</p>

<p align="center">
  <b>Backend репо:</b> <a href="https://github.com/mad-futurist/ai-onboarding-service">github.com/mad-futurist/ai-onboarding-service</a><br/>
  <b>Frontend репо:</b> <a href="https://github.com/mad-futurist/ai-onboarding-service-frontend">github.com/mad-futurist/ai-onboarding-service-frontend</a><br/>
  <b>Live API:</b> <a href="https://ai-onboarding-service.onrender.com">ai-onboarding-service.onrender.com</a> &nbsp;·&nbsp; <b>Live app:</b> <a href="https://ai-onboarding-service-frontend.vercel.app">ai-onboarding-service-frontend.vercel.app</a>
</p>

---

> **ReadySet.AI Backend** — це FastAPI-сервіс, який живить AI-асистента онбордингу. Він перетворює документацію компанії на role-aware знання, генерує плани 30/60/90 на основі документів, слухає поведінкові сигнали і тримає ментора в циклі прийняття рішень.

Цей репозиторій — **backend**. Next.js frontend знаходиться в [`ai-onboarding-service-frontend`](https://github.com/mad-futurist/ai-onboarding-service-frontend).

---

## 🎬 Демо

Демо запускається з **frontend**: відкрийте live-додаток, перейдіть на **Demo** і натисніть **«Start demo mode»**. Демо викликає реальні endpoint-и бекенду — переконайтесь, що сервер працює і доступний.

---

## ⚡ Killer-функції

| # | Функція | Чому це важливо |
|---|---|---|
| 1 | **AI-копілот під контролем людини** | Кожен AI-вихід зберігається як редагований, переглядуваний артефакт (плани, adjustments, чернетки курсів, сигнали). API примусово застосовує lifecycle статусів: `proposed → reviewed → applied`. Без тихого авто-застосування. |
| 2 | **AI live (стрімінг)** | Генерація плану, Ask AI та пояснення сигналів стрімляться інкрементально — frontend рендерить токени по мірі їх надходження. |
| 3 | **Генерація плану під роль + документи** | `ai_plan_service` будує план 30/60/90 фаза за фазою з профілю ролі новачка та обраного підмножини документів. Промпти обмежені, вихід валідується pydantic-схемами. |
| 4 | **Сигнали — спочатку роль, потім запитання** | `ai_signals` стартують від milestone-ів очікуваної ролі; потім — поведінкові сигнали (повторювані запитання, заблоковані задачі, review-патерни). Кожен сигнал зберігає **чанки-докази** для аудиту ментором. |
| 5 | **AI-сигнали зі скорінгом і доказами** | `e75c48a6f8c0_add_scoring_fields_to_ai_signals` — сигнали містять зважені оцінки та посилання на джерельні події, що їх тригернули. |
| 6 | **Генерація курсів із контролем ментора** | Маршрут `courses` генерує короткий курс з обраних джерел, зберігає чернетку, вимагає схвалення ментора перед публікацією. |
| 7 | **RAG Ask AI** | `knowledge` + `document_chunks` + `embedding_service`: чанкування документів, pgvector cosine search, відповіді на основі промптів із цитатами джерел у payload відповіді. |

---

## 🧩 Класичні функції

- **Користувачі, люди, новачки** — акаунти, профілі ролей, зв'язки mentor ↔ newcomer.
- **Плани онбордингу і задачі** — фази (1–24+), задачі, критерії успіху, переходи статусів.
- **Kanban / черга рев'ю ментора** — `mentor_kanban` для черги submission-ів новачків.
- **Снапшоти прогресу** — `progress_snapshots` відстежують momentum з часом.
- **Document service** — upload, store, chunk, embed; типізовані документи (HR, process, technical…).
- **Нотифікації** — маршрут `notifications`, в межах ролі.
- **Events firehose** — повний лог подій (`onboarding_events`) для аналітики й сигналів.
- **Mentor digests** — періодичні AI-зведення для ментора.

---

## ✨ Додаткові функції

- **Календар / зустрічі** — маршрут `meetings`, спільний для mentor і newcomer.
- **Відео у курсах** — курси можуть вбудовувати відеоуроки (lesson notes service).
- **Інтеграції Teams / Slack** *(roadmap)*.
- **Mind map** — Ask AI відповіді включають graph payload, який споживає `@xyflow/react` рендерер на frontend.
- **Skill checks / assessments** — маршрут `assessments` генерує швидкий тест для нового найму; результати тригерять генерацію плану.
- **Blocked reports** — новачки можуть позначити задачу як заблоковану; з'являється в сигналах ментора.
- **Company onboarding gaps** — `company_gaps` агрегує патерни по всіх новачках.

---

## 🛠 Технічні рішення

### Стек

| Шар | Технології |
|---|---|
| Web framework | **FastAPI** + pydantic v2 |
| ORM / БД | **SQLAlchemy 2** + **PostgreSQL 16** + **pgvector** |
| Міграції | **Alembic** |
| LLM | **OpenAI** (chat + embeddings) через `llm_service` |
| Embeddings store | `pgvector` (cosine), таблиця `document_chunks` |
| Сервер | **Uvicorn** (ASGI), CORS middleware для Next.js host |
| Контейнер | `docker-compose.yml` (pgvector/pgvector:pg16) |
| Деплой | **Render** (web service) |

### RAG-пайплайн

```
Upload документа
   └─► chunking_service        (token-aware splits, зі збереженням metadata)
         └─► embedding_service (OpenAI embeddings → pgvector)
                  └─► retrieval (cosine kNN по document_chunks)
                            └─► збір промту (system + чанки + user)
                                      └─► llm_service (chat + streaming)
                                              └─► структурований вихід
                                                    (валідація pydantic)
                                                       └─► збережений артефакт
                                                             (status=proposed)
                                                                  └─► рев'ю ментора
```

Кожен AI-артефакт (план, курс, сигнал, adjustment, відповідь) містить:
- id **шаблону промту** (`app/prompts/*.txt`),
- використані **source chunks**,
- **статус** (`proposed | reviewed | applied | rejected`),
- поле **рішення ментора** після дії.

Саме це робить систему аудитованою наскрізь.

### Архітектура

```
[ Браузер ]
     │
     ▼
[ Next.js (Vercel) ]  ── /api/* проксі ──►  [ FastAPI (Render) ]
                                                  │
                                                  ├─ PostgreSQL + pgvector
                                                  └─ OpenAI (chat + embeddings)
```

Frontend ніколи не бачить OpenAI-ключ. Весь retrieval, збір промту і стрімінг відбуваються на backend.

### Структура модулів

```
app/
├── main.py                    # FastAPI app + CORS + реєстрація маршрутів
├── core/                      # config, settings, security helpers
├── db/                        # SQLAlchemy base, session, engine
├── models/                    # ORM моделі (newcomer, plan, task, ai_signal, …)
├── schemas/                   # pydantic IO схеми
├── api/routes/                # FastAPI routers (один на ресурс)
├── services/
│   ├── ai_plan_service.py     # генерація плану (роль + доки → фази/задачі)
│   ├── llm_service.py         # обгортка OpenAI client + streaming
│   ├── embedding_service.py   # OpenAI embeddings → pgvector
│   ├── chunking_service.py    # token-aware splitter документів
│   ├── knowledge_recommendation_service.py  # surfacing пов'язаних документів
│   ├── company_gap_service.py # виявлення патернів по всіх новачках
│   ├── mentor_dashboard_service.py
│   ├── mentor_digest_service.py
│   ├── progress_snapshot_service.py
│   ├── task_detail_service.py
│   ├── person_contact_service.py
│   └── event_logger.py        # firehose подій онбордингу
└── prompts/                   # версіоновані шаблони промтів (plain .txt)
```

### Ключові маршрути

`users`, `people`, `newcomers`, `documents`, `onboarding_plans`, `tasks`, `ai`, `ai_signals`, `onboarding_events`, `plan_adjustments`, `mentor_dashboard`, `newcomer_dashboard`, `blocked_reports`, `company_gaps`, `mentor_digests`, `mentor_actions`, `progress_snapshots`, `onboarding_reflections`, `newcomer_kb`, `user_story`, `knowledge`, `demo`, `courses`, `meetings`, `lesson_notes`, `assessments`, `notifications`, `mentor_kanban`.

---

## 🎨 Brand palette

| Token | Hex |
|---|---|
| Blaze Orange | `#CC5500` |
| Dark Orange | `#FF8C00` |
| Sandy Orange | `#FFAA55` |
| Peach | `#FFD199` |
| Cream | `#FFF0E0` |
| Warm White | `#FFF7F0` |
| Warm Brown | `#7A5030` |
| Deep Brown | `#3D2000` |
| Obsidian | `#1A0E00` |

---

## 🚀 Локальний запуск

```powershell
# 1. Postgres + pgvector
docker compose up -d

# 2. Python env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Env vars
cp .env.example .env
# заповніть:
#   APP_NAME=ReadySet.AI
#   APP_ENV=local
#   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_onboarding
#   OPENAI_API_KEY=sk-...
#   OPENAI_MODEL=gpt-4o-mini
#   EMBEDDING_MODEL=text-embedding-3-small
#   CORS_ORIGINS=http://localhost:3000

# 4. Міграції
alembic upgrade head

# 5. Запуск
uvicorn app.main:app --reload
# API → http://127.0.0.1:8000  ·  docs → http://127.0.0.1:8000/docs
```

Потім запустіть frontend (див. [frontend README](https://github.com/mad-futurist/ai-onboarding-service-frontend#-run-locally)).

---

## 🌍 Продакшен запуск

Деплой на **Render**.

1. **Web Service (Python)**
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. **Database** — підготуйте Postgres і увімкніть розширення:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. **Environment**
   ```
   APP_NAME=ReadySet.AI
   APP_ENV=production
   DATABASE_URL=postgresql+psycopg://...
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   EMBEDDING_MODEL=text-embedding-3-small
   CORS_ORIGINS=https://ai-onboarding-service-frontend.vercel.app
   ```
4. **Міграції** — виконайте `alembic upgrade head` як release/predeploy команду.

Live API: [ai-onboarding-service.onrender.com](https://ai-onboarding-service.onrender.com).

---

<div align="right">

[🔝 На початок](#українська-версія) &nbsp;·&nbsp; [🇬🇧 English](#english-version)

</div>
