from sqlalchemy.orm import Session

from app.models.ai_signal import AISignal
from app.models.arena import ArenaSession
from app.models.newcomer import NewcomerProfile


RADAR_DIMENSIONS = [
    "opening",
    "discovery",
    "objections",
    "closing",
    "product_knowledge",
]


def suggestions_for_newcomer(db: Session, newcomer_id: int) -> dict:
    """
    Looks at the newcomer's recent arena sessions + active arena signals
    and returns ranked focus dimensions + signal-driven reasons.
    """
    newcomer = (
        db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    )
    if not newcomer:
        return {
            "newcomer_id": newcomer_id,
            "focus_dimensions": [],
            "reasons": [],
            "sessions_count": 0,
            "open_arena_signals": [],
        }

    sessions = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id == newcomer_id)
        .filter(ArenaSession.status == "ended")
        .order_by(ArenaSession.id.desc())
        .limit(8)
        .all()
    )

    dim_totals = {d: 0.0 for d in RADAR_DIMENSIONS}
    dim_counts = {d: 0 for d in RADAR_DIMENSIONS}
    for s in sessions:
        radar = s.radar_scores or {}
        for d in RADAR_DIMENSIONS:
            v = radar.get(d)
            if isinstance(v, (int, float)):
                dim_totals[d] += float(v)
                dim_counts[d] += 1

    averages = {
        d: round(dim_totals[d] / dim_counts[d], 1) if dim_counts[d] else 0.0
        for d in RADAR_DIMENSIONS
    }

    # Open arena signals — these tell us what mentor side already flagged
    open_arena_signals = (
        db.query(AISignal)
        .filter(AISignal.newcomer_id == newcomer_id)
        .filter(AISignal.status == "open")
        .filter(AISignal.signal_type.like("arena_low_%"))
        .order_by(AISignal.id.desc())
        .all()
    )

    reasons: list[dict] = []
    weighted: dict[str, float] = {d: 0.0 for d in RADAR_DIMENSIONS}

    # Signals dominate the recommendation
    for sig in open_arena_signals:
        dim = sig.signal_type.replace("arena_low_", "")
        if dim in weighted:
            weighted[dim] += 2.0
            reasons.append(
                {
                    "dimension": dim,
                    "source": "signal",
                    "text": sig.title,
                    "evidence": sig.evidence or "",
                }
            )

    # Session averages also matter — lower avg = more priority
    for d in RADAR_DIMENSIONS:
        if dim_counts[d] == 0:
            continue
        deficit = max(0.0, (60.0 - averages[d]) / 60.0)
        weighted[d] += deficit
        if averages[d] < 55:
            reasons.append(
                {
                    "dimension": d,
                    "source": "trend",
                    "text": f"{d.replace('_', ' ').title()} average is {averages[d]} across last {dim_counts[d]} sessions.",
                    "evidence": "",
                }
            )

    # Choose top 3 with non-zero weight
    ranked = sorted(
        ((d, w) for d, w in weighted.items() if w > 0),
        key=lambda x: x[1],
        reverse=True,
    )
    focus_dimensions = [d for d, _ in ranked[:3]]
    if not focus_dimensions:
        # Default: if no signal/trend pressure yet, pick the two lowest with data
        scored = [(d, averages[d]) for d in RADAR_DIMENSIONS if dim_counts[d] > 0]
        scored.sort(key=lambda x: x[1])
        focus_dimensions = [d for d, _ in scored[:2]]

    return {
        "newcomer_id": newcomer_id,
        "focus_dimensions": focus_dimensions,
        "reasons": reasons[:6],
        "sessions_count": len(sessions),
        "dimension_averages": averages,
        "open_arena_signals": [
            {
                "id": s.id,
                "signal_type": s.signal_type,
                "title": s.title,
                "severity": s.severity,
                "occurrence_count": s.occurrence_count or 1,
            }
            for s in open_arena_signals
        ],
    }
