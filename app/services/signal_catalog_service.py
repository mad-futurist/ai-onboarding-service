from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SignalCatalogItem:
    signal_type: str
    title: str
    tone: str
    severity: str
    when: str
    evidence: str
    suggested_action: str
    mvp_trigger: str


@dataclass(frozen=True)
class SignalCatalogGroup:
    tone: str
    label: str
    description: str
    items: list[SignalCatalogItem]


SIGNAL_CATALOG: list[SignalCatalogGroup] = [
    SignalCatalogGroup(
        tone="positive",
        label="Good signals",
        description="Healthy onboarding momentum worth reinforcing.",
        items=[
            SignalCatalogItem(
                signal_type="fast_completion",
                title="Fast task completion",
                tone="positive",
                severity="low",
                when="A task is moved to done within 24 hours of creation.",
                evidence="Task title, created date, updated date, elapsed hours.",
                suggested_action="Offer a stretch task or pull the next milestone forward.",
                mvp_trigger="Set any onboarding task to done soon after it was created.",
            ),
            SignalCatalogItem(
                signal_type="steady_progress",
                title="Steady onboarding progress",
                tone="positive",
                severity="low",
                when="At least three tasks are done and no task is currently blocked.",
                evidence="Completed task count and absence of blockers.",
                suggested_action="Keep the current plan pace and add optional depth if useful.",
                mvp_trigger="Mark 3 tasks done and keep blocked tasks at 0.",
            ),
        ],
    ),
    SignalCatalogGroup(
        tone="attention",
        label="Attention signals",
        description="Early friction that should be clarified before it becomes blocking.",
        items=[
            SignalCatalogItem(
                signal_type="deployment_friction",
                title="Deployment friction",
                tone="attention",
                severity="medium",
                when="The newcomer asks repeated deployment questions or uses deployment docs repeatedly.",
                evidence="Recent AI questions, repeated sources, and related task changes.",
                suggested_action="Schedule a focused deployment walkthrough.",
                mvp_trigger="Ask 2+ deployment questions in the AI assistant.",
            ),
            SignalCatalogItem(
                signal_type="knowledge_friction",
                title="Knowledge base friction",
                tone="attention",
                severity="medium",
                when="The same source appears repeatedly or AI answers receive repeated negative feedback.",
                evidence="Repeated source titles and negative answer feedback count.",
                suggested_action="Review the source and create a shorter role-specific guide.",
                mvp_trigger="Ask questions that repeatedly cite the same source, or send 3 negative feedbacks.",
            ),
            SignalCatalogItem(
                signal_type="deployment_heavy_plan",
                title="Deployment-heavy plan",
                tone="attention",
                severity="medium",
                when="The plan contains three or more deployment-related tasks.",
                evidence="Deployment task count and task titles.",
                suggested_action="Merge similar tasks into one end-to-end exercise.",
                mvp_trigger="Create or keep 3 deployment tasks in the plan.",
            ),
            SignalCatalogItem(
                signal_type="plan_stall",
                title="Plan stall risk",
                tone="attention",
                severity="medium",
                when="Several tasks are queued or in progress, but no task is done yet.",
                evidence="Open task count and zero completed tasks.",
                suggested_action="Pick one starter task with the newcomer and define the next concrete action.",
                mvp_trigger="Create 3+ todo/in-progress tasks and keep done tasks at 0.",
            ),
            SignalCatalogItem(
                signal_type="task_stuck_in_review",
                title="Task stuck in review",
                tone="attention",
                severity="medium",
                when="A task has been in review for more than 3 days without a decision.",
                evidence="Task title, time since the move to in_review.",
                suggested_action="Review the submission today or schedule a 15-minute sync with the newcomer.",
                mvp_trigger="Move a task to in_review and leave it there for 3+ days.",
            ),
        ],
    ),
    SignalCatalogGroup(
        tone="critical",
        label="Blocking signals",
        description="Signals that can stop the newcomer from progressing independently.",
        items=[
            SignalCatalogItem(
                signal_type="blocked_task",
                title="Blocked task",
                tone="critical",
                severity="high",
                when="One or more onboarding tasks are marked as blocked.",
                evidence="Blocked task count and task titles.",
                suggested_action="Clarify instructions, assign a helper, or adapt the plan.",
                mvp_trigger="Mark any onboarding task as blocked.",
            ),
            SignalCatalogItem(
                signal_type="access_friction",
                title="Access or permissions blocker",
                tone="critical",
                severity="high",
                when="Access questions repeat or an access-related task/report is blocked.",
                evidence="Access questions, blocked task events, or blocked reports.",
                suggested_action="Check accounts, repository access, VPN, and tool invitations.",
                mvp_trigger="Ask 2+ access questions, or report an access blocker.",
            ),
            SignalCatalogItem(
                signal_type="empty_plan_blocker",
                title="Missing onboarding plan",
                tone="critical",
                severity="high",
                when="The newcomer has no actionable tasks in their onboarding plan.",
                evidence="Zero onboarding tasks found for the newcomer.",
                suggested_action="Generate or assign a first-week plan before expecting autonomous progress.",
                mvp_trigger="Create a newcomer without tasks, then run signal detection.",
            ),
            SignalCatalogItem(
                signal_type="task_review_bounce",
                title="Task bounced from review repeatedly",
                tone="critical",
                severity="high",
                when="A task has been returned from review at least twice.",
                evidence="Number of review return comments on the task.",
                suggested_action="Pair on the task in real time and clarify acceptance criteria.",
                mvp_trigger="Return a task from review with a comment at least twice.",
            ),
        ],
    ),
]


def list_signal_catalog() -> list[dict]:
    return [
        {
            "tone": group.tone,
            "label": group.label,
            "description": group.description,
            "items": [asdict(item) for item in group.items],
        }
        for group in SIGNAL_CATALOG
    ]
