from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

from app.core.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.db.base import Base

from app.models.user import User
from app.models.newcomer import NewcomerProfile
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.onboarding_plan import OnboardingPlan
from app.models.onboarding_task import OnboardingTask
from app.models.sprint import Sprint
from app.models.week import Week
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.ai_question import AIQuestion, AIQuestionSource
from app.models.ai_signal import AISignal
from app.models.onboarding_event import OnboardingEvent
from app.models.plan_adjustment import PlanAdjustmentSuggestion
from app.models.blocked_report import BlockedReport
from app.models.person_contact import PersonContact, NewcomerRecommendedContact
from app.models.company_onboarding_gap import CompanyOnboardingGap
from app.models.mentor_digest import MentorDigest
from app.models.ai_answer_feedback import AIAnswerFeedback
from app.models.ai_signal_feedback import AISignalFeedback
from app.models.progress_snapshot import ProgressSnapshot
from app.models.onboarding_reflection import OnboardingReflection
from app.models.lesson_note import LessonNote
from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentSubmission,
    AssessmentAnswer,
)

target_metadata = Base.metadata
# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
