import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal, get_db
from app.models.arena import ArenaScenario, ArenaSession, ArenaMessage
from app.models.document import Document
from app.models.newcomer import NewcomerProfile
from app.models.user import User
from app.schemas.arena import (
    ArenaDashboardRead,
    ArenaLeaderboardEntry,
    ArenaScenarioCreate,
    ArenaScenarioRead,
    ArenaSessionRead,
    ArenaSessionStart,
    MentorHintCreate,
    NewcomerArenaSummary,
    PersonalBotRequest,
)
from app.services import arena_hint_bus
from app.services.arena_actor_service import stream_actor_response
from app.services.arena_analyzer_service import (
    analyze_seller_message,
    fallback_analysis,
)
from app.services.arena_coach_service import coach_message
from app.services.arena_debrief_service import generate_debrief
from app.services.arena_personal_bot_service import (
    build_personal_bot_spec,
    generate_personal_bot,
    persist_spec,
)
from app.services.arena_streaming import sse_frame
from app.services.arena_suggestions_service import suggestions_for_newcomer


router = APIRouter(prefix="/arena", tags=["Arena"])


# ---------------------------------------------------------------------------
# Helpers


def _scenario_to_read(
    scenario: ArenaScenario,
    *,
    locked: bool = False,
    attempts: int = 0,
    last_score: Optional[float] = None,
) -> ArenaScenarioRead:
    return ArenaScenarioRead(
        id=scenario.id,
        mentor_id=scenario.mentor_id,
        audience_newcomer_id=scenario.audience_newcomer_id,
        title=scenario.title,
        conversation_type=scenario.conversation_type,
        difficulty=scenario.difficulty,
        persona=scenario.persona or {},
        goal_text=scenario.goal_text,
        success_criteria=scenario.success_criteria,
        kb_source_ids=scenario.kb_source_ids or [],
        allow_live_coaching=scenario.allow_live_coaching,
        is_personal_bot=scenario.is_personal_bot,
        description=scenario.description,
        cover_emoji=scenario.cover_emoji,
        created_at=scenario.created_at,
        locked=locked,
        attempts=attempts,
        last_score=last_score,
    )


def _compute_progression(
    db: Session, newcomer_id: int, scenarios: list[ArenaScenario]
) -> dict[int, tuple[bool, int, Optional[float]]]:
    """
    Returns map: scenario_id -> (locked, attempts, last_score)
    Unlock rule: a difficulty N scenario unlocks once the newcomer has at
    least one ended session with overall_score >= 50 on difficulty N-1
    (any scenario). Difficulty 1 is always unlocked.
    """
    sessions = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id == newcomer_id)
        .all()
    )

    by_scenario: dict[int, list[ArenaSession]] = {}
    for s in sessions:
        by_scenario.setdefault(s.scenario_id, []).append(s)

    cleared_difficulties: set[int] = {1}
    for s in sessions:
        if s.status == "ended" and (s.overall_score or 0) >= 50:
            sc = next((x for x in scenarios if x.id == s.scenario_id), None)
            if sc:
                cleared_difficulties.add(sc.difficulty)
                cleared_difficulties.add(sc.difficulty + 1)

    out: dict[int, tuple[bool, int, Optional[float]]] = {}
    for sc in scenarios:
        attempts_list = by_scenario.get(sc.id, [])
        attempts = len(attempts_list)
        last_score = None
        if attempts_list:
            ended = [s for s in attempts_list if s.status == "ended"]
            if ended:
                last_score = ended[-1].overall_score
        locked = sc.difficulty not in cleared_difficulties and not sc.is_personal_bot
        out[sc.id] = (locked, attempts, last_score)
    return out


# ---------------------------------------------------------------------------
# Scenarios


@router.post("/scenarios", response_model=ArenaScenarioRead)
def create_scenario(payload: ArenaScenarioCreate, db: Session = Depends(get_db)):
    scenario = ArenaScenario(
        mentor_id=payload.mentor_id,
        audience_newcomer_id=payload.audience_newcomer_id,
        title=payload.title,
        conversation_type=payload.conversation_type,
        difficulty=payload.difficulty,
        persona=payload.persona.model_dump(),
        goal_text=payload.goal_text,
        success_criteria=payload.success_criteria,
        kb_source_ids=payload.kb_source_ids,
        allow_live_coaching=payload.allow_live_coaching,
        is_personal_bot=payload.is_personal_bot,
        description=payload.description,
        cover_emoji=payload.cover_emoji,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return _scenario_to_read(scenario)


@router.get("/scenarios", response_model=list[ArenaScenarioRead])
def list_scenarios(
    newcomer_id: Optional[int] = None,
    mentor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ArenaScenario)
    if mentor_id is not None:
        query = query.filter(ArenaScenario.mentor_id == mentor_id)
    if newcomer_id is not None:
        query = query.filter(
            (ArenaScenario.audience_newcomer_id == None)  # noqa: E711
            | (ArenaScenario.audience_newcomer_id == newcomer_id)
        )

    scenarios = query.order_by(ArenaScenario.difficulty.asc(), ArenaScenario.id.asc()).all()

    progression = {}
    if newcomer_id is not None:
        progression = _compute_progression(db, newcomer_id, scenarios)

    out = []
    for sc in scenarios:
        locked, attempts, last_score = progression.get(sc.id, (False, 0, None))
        out.append(_scenario_to_read(sc, locked=locked, attempts=attempts, last_score=last_score))
    return out


@router.get("/scenarios/{scenario_id}", response_model=ArenaScenarioRead)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(ArenaScenario).filter(ArenaScenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _scenario_to_read(scenario)


# ---------------------------------------------------------------------------
# Sessions


@router.post("/sessions", response_model=ArenaSessionRead)
def start_session(payload: ArenaSessionStart, db: Session = Depends(get_db)):
    scenario = (
        db.query(ArenaScenario).filter(ArenaScenario.id == payload.scenario_id).first()
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    newcomer = (
        db.query(NewcomerProfile).filter(NewcomerProfile.id == payload.newcomer_id).first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    session = ArenaSession(
        scenario_id=scenario.id,
        newcomer_id=newcomer.id,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ArenaSessionRead])
def list_sessions(
    newcomer_id: Optional[int] = None,
    mentor_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(ArenaSession)
    if newcomer_id is not None:
        query = query.filter(ArenaSession.newcomer_id == newcomer_id)
    if mentor_id is not None:
        query = query.join(NewcomerProfile, NewcomerProfile.id == ArenaSession.newcomer_id).filter(
            NewcomerProfile.mentor_id == mentor_id
        )
    return (
        query.order_by(ArenaSession.id.desc()).limit(limit).all()
    )


@router.get("/sessions/{session_id}", response_model=ArenaSessionRead)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ArenaSession).filter(ArenaSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/messages")
def list_session_messages(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ArenaSession).filter(ArenaSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "order_index": m.order_index,
            "sender": m.sender,
            "content": m.content,
            "ai_analysis": m.ai_analysis,
            "color": m.color,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in sorted(session.messages, key=lambda m: m.order_index)
    ]


# ---------------------------------------------------------------------------
# Streaming chat (the core SSE multiplex)


def _next_order_index(db: Session, session_id: int) -> int:
    last = (
        db.query(ArenaMessage)
        .filter(ArenaMessage.session_id == session_id)
        .order_by(ArenaMessage.order_index.desc())
        .first()
    )
    return (last.order_index + 1) if last else 0


@router.get("/sessions/{session_id}/stream")
async def stream_turn(
    session_id: int,
    message: str = Query(..., description="The seller's latest message"),
):
    """
    SSE endpoint. Emits, interleaved:
      event: user_saved   {messageId}
      event: token        {delta}
      event: analysis     {messageId, dimension, delta, label, color, why}
      event: done         {aiMessageId}
    """
    seller_text = message.strip()
    if not seller_text:
        raise HTTPException(status_code=400, detail="message is required")

    # Fresh session per stream connection (avoid sharing the request's session
    # since this is a long-lived generator).
    db = SessionLocal()
    try:
        session = (
            db.query(ArenaSession)
            .options(joinedload(ArenaSession.scenario))
            .filter(ArenaSession.id == session_id)
            .first()
        )
        if not session:
            db.close()
            raise HTTPException(status_code=404, detail="Session not found")

        scenario = session.scenario
        history_msgs = sorted(list(session.messages), key=lambda m: m.order_index)

        # Persist newcomer message immediately
        user_msg = ArenaMessage(
            session_id=session.id,
            order_index=_next_order_index(db, session.id),
            sender="newcomer",
            content=seller_text,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        user_msg_id = user_msg.id
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        db.close()
        raise HTTPException(status_code=500, detail=f"stream init failed: {exc}")

    async def generator():
        analysis_queue: asyncio.Queue = asyncio.Queue()
        analysis_task: Optional[asyncio.Task] = None
        try:
            yield sse_frame("user_saved", {"messageId": user_msg_id})

            async def run_analysis():
                try:
                    result = await analyze_seller_message(
                        scenario, history_msgs, seller_text
                    )
                except Exception:
                    result = fallback_analysis()
                result["messageId"] = user_msg_id
                await analysis_queue.put(result)

            analysis_task = asyncio.create_task(run_analysis())

            assembled = []
            try:
                actor_iter = stream_actor_response(scenario, history_msgs, seller_text)
                async for piece in actor_iter:
                    assembled.append(piece)
                    yield sse_frame("token", {"delta": piece})
                    while not analysis_queue.empty():
                        analysis_payload = analysis_queue.get_nowait()
                        yield sse_frame("analysis", analysis_payload)
            except Exception as exc:  # noqa: BLE001
                yield sse_frame("error", {"message": f"actor failed: {exc}"})

            # Drain any pending analysis
            try:
                if analysis_task and not analysis_task.done():
                    await asyncio.wait_for(analysis_task, timeout=8)
            except asyncio.TimeoutError:
                pass
            while not analysis_queue.empty():
                yield sse_frame("analysis", analysis_queue.get_nowait())

            ai_text = "".join(assembled).strip()
            ai_msg_id = None
            if ai_text:
                db2 = SessionLocal()
                try:
                    ai_msg = ArenaMessage(
                        session_id=session_id,
                        order_index=_next_order_index(db2, session_id),
                        sender="client",
                        content=ai_text,
                    )
                    db2.add(ai_msg)
                    db2.commit()
                    db2.refresh(ai_msg)
                    ai_msg_id = ai_msg.id

                    # Persist analysis onto the newcomer message
                    if not analysis_queue.empty():
                        pass  # already drained
                    # Attempt to read the latest user message and write its analysis
                    user_row = (
                        db2.query(ArenaMessage)
                        .filter(ArenaMessage.id == user_msg_id)
                        .first()
                    )
                    if user_row and analysis_task and analysis_task.done():
                        try:
                            analysis_result = analysis_task.result()
                            user_row.ai_analysis = analysis_result
                            user_row.color = analysis_result.get("color")
                            db2.commit()
                        except Exception:
                            pass
                finally:
                    db2.close()

            yield sse_frame("done", {"aiMessageId": ai_msg_id})
        finally:
            if analysis_task and not analysis_task.done():
                analysis_task.cancel()
            db.close()

    return StreamingResponse(generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# End / Debrief


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: int, db: Session = Depends(get_db)):
    session = (
        db.query(ArenaSession)
        .options(joinedload(ArenaSession.scenario), joinedload(ArenaSession.newcomer).joinedload(NewcomerProfile.user))
        .filter(ArenaSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "ended" and session.debrief:
        return session.debrief

    debrief = await generate_debrief(db, session)
    return debrief


@router.get("/sessions/{session_id}/debrief")
def get_debrief(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ArenaSession).filter(ArenaSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.debrief:
        raise HTTPException(status_code=404, detail="Debrief not yet generated")
    # Re-attach the transcript with reviews
    review_by_id = {
        e.get("message_id"): e for e in session.debrief.get("transcript_review", [])
    }
    transcript = []
    for m in sorted(session.messages, key=lambda m: m.order_index):
        if m.sender == "client":
            continue
        review = review_by_id.get(m.id) or {}
        transcript.append(
            {
                "message_id": m.id,
                "sender": m.sender,
                "content": m.content,
                "color": review.get("color") or m.color or "neutral",
                "label": review.get("label"),
                "dimension": review.get("dimension"),
                "alternatives": review.get("alternatives") or [],
            }
        )
    return {**session.debrief, "transcript": transcript}


# ---------------------------------------------------------------------------
# Mentor hints (live coaching)


@router.post("/sessions/{session_id}/hint")
async def send_hint(session_id: int, payload: MentorHintCreate, db: Session = Depends(get_db)):
    session = db.query(ArenaSession).filter(ArenaSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="hint text is required")
    delivered = await arena_hint_bus.publish(
        session_id,
        {"text": text, "mentor_id": payload.mentor_id, "session_id": session_id},
    )
    return {"delivered_to": delivered, "text": text}


@router.get("/sessions/{session_id}/hints/stream")
async def stream_hints(session_id: int):
    queue = await arena_hint_bus.subscribe(session_id)

    async def generator():
        try:
            yield sse_frame("ready", {"sessionId": session_id})
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield sse_frame("hint", payload)
                except asyncio.TimeoutError:
                    yield b": keepalive\n\n"
        finally:
            await arena_hint_bus.unsubscribe(session_id, queue)

    return StreamingResponse(generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Personal bot


@router.post("/personal-bot", response_model=ArenaScenarioRead)
async def create_personal_bot(payload: PersonalBotRequest, db: Session = Depends(get_db)):
    newcomer = (
        db.query(NewcomerProfile).filter(NewcomerProfile.id == payload.newcomer_id).first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    scenario = await generate_personal_bot(
        db,
        newcomer,
        focus_dimensions=payload.focus_dimensions or [],
        pain_text=payload.pain_text or "",
    )
    return _scenario_to_read(scenario, locked=False, attempts=0, last_score=None)


@router.get("/personal-bot/stream")
async def stream_personal_bot(
    newcomer_id: int,
    focus: str = "",
    pain: str = "",
):
    """
    Streams phase events while the personal bot is being designed, then
    creates the scenario and emits a final 'done' frame with the scenario id.
    """
    focus_dims = [f.strip() for f in focus.split(",") if f.strip()]

    async def generator():
        phases = [
            ("reading", "Reading your last sessions"),
            ("mining", "Mining your weak spots"),
            ("forging", "Forging a persona"),
            ("polishing", "Polishing the brief"),
        ]
        for phase, label in phases:
            yield sse_frame("phase", {"phase": phase, "label": label})
            await asyncio.sleep(0.9)

        db = SessionLocal()
        try:
            newcomer = (
                db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
            )
            if not newcomer:
                yield sse_frame("error", {"message": "newcomer not found"})
                return
            scenario = await generate_personal_bot(
                db, newcomer, focus_dimensions=focus_dims, pain_text=pain
            )
            yield sse_frame(
                "done",
                {
                    "scenarioId": scenario.id,
                    "title": scenario.title,
                    "description": scenario.description,
                    "cover_emoji": scenario.cover_emoji,
                    "difficulty": scenario.difficulty,
                    "persona": scenario.persona,
                },
            )
        finally:
            db.close()

    return StreamingResponse(generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Mentor dashboard + leaderboard + newcomer summary


@router.get("/dashboard", response_model=ArenaDashboardRead)
def mentor_dashboard(mentor_id: int, db: Session = Depends(get_db)):
    newcomer_ids = [
        nid for (nid,) in db.query(NewcomerProfile.id).filter(NewcomerProfile.mentor_id == mentor_id).all()
    ]
    if not newcomer_ids:
        return ArenaDashboardRead(
            sessions_this_week=0,
            avg_score=0.0,
            weakest_team_dimension=None,
            leaderboard=[],
            recent_sessions=[],
            dimension_averages={},
            flagged_newcomer_ids=[],
        )

    sessions = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id.in_(newcomer_ids))
        .order_by(ArenaSession.id.desc())
        .limit(200)
        .all()
    )
    ended = [s for s in sessions if s.status == "ended" and s.overall_score is not None]
    avg_score = round(sum(s.overall_score for s in ended) / len(ended), 1) if ended else 0.0

    from datetime import datetime, timedelta, timezone
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    sessions_this_week = sum(1 for s in sessions if s.started_at and s.started_at >= week_ago)

    dim_totals = {d: 0.0 for d in ["opening", "discovery", "objections", "closing", "product_knowledge"]}
    dim_counts = {d: 0 for d in dim_totals}
    for s in ended:
        radar = s.radar_scores or {}
        for d in dim_totals:
            v = radar.get(d)
            if isinstance(v, (int, float)):
                dim_totals[d] += float(v)
                dim_counts[d] += 1
    dim_avgs = {
        d: round(dim_totals[d] / dim_counts[d], 1) if dim_counts[d] else 0.0
        for d in dim_totals
    }
    weakest = min(dim_avgs.items(), key=lambda x: x[1])[0] if any(dim_counts.values()) else None

    # Leaderboard
    by_newcomer: dict[int, list[ArenaSession]] = {}
    for s in ended:
        by_newcomer.setdefault(s.newcomer_id, []).append(s)
    leaderboard = []
    users_by_id = {
        u.id: u
        for u in db.query(User).filter(
            User.id.in_(
                [n.user_id for n in db.query(NewcomerProfile).filter(NewcomerProfile.id.in_(newcomer_ids)).all()]
            )
        ).all()
    }
    newcomers = {
        n.id: n for n in db.query(NewcomerProfile).filter(NewcomerProfile.id.in_(newcomer_ids)).all()
    }
    for nid, sess_list in by_newcomer.items():
        avg = sum(s.overall_score for s in sess_list) / len(sess_list)
        nc = newcomers.get(nid)
        u = users_by_id.get(nc.user_id) if nc else None
        leaderboard.append(
            ArenaLeaderboardEntry(
                newcomer_id=nid,
                name=u.full_name if u else f"Newcomer #{nid}",
                overall_score=round(avg, 1),
                sessions_played=len(sess_list),
                streak=_compute_streak(sess_list),
            )
        )
    leaderboard.sort(key=lambda e: e.overall_score, reverse=True)

    # Flagged newcomers (3+ low sessions on any dimension across last 5 of their own)
    flagged: list[int] = []
    for nid in newcomer_ids:
        nlist = sorted(
            [s for s in ended if s.newcomer_id == nid],
            key=lambda s: s.id,
            reverse=True,
        )[:5]
        if not nlist:
            continue
        for d in dim_totals:
            low = [s for s in nlist if (s.radar_scores or {}).get(d, 100) < 50]
            if len(low) >= 3:
                flagged.append(nid)
                break

    recent = sessions[:8]

    return ArenaDashboardRead(
        sessions_this_week=sessions_this_week,
        avg_score=avg_score,
        weakest_team_dimension=weakest,
        leaderboard=leaderboard[:10],
        recent_sessions=recent,
        dimension_averages=dim_avgs,
        flagged_newcomer_ids=flagged,
    )


def _compute_streak(sessions: list[ArenaSession]) -> int:
    if not sessions:
        return 0
    sorted_sessions = sorted(sessions, key=lambda s: s.id, reverse=True)
    streak = 0
    for s in sorted_sessions:
        if (s.overall_score or 0) >= 70:
            streak += 1
        else:
            break
    return streak


@router.get("/leaderboard", response_model=list[ArenaLeaderboardEntry])
def leaderboard(
    team: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    nc_query = db.query(NewcomerProfile)
    if team:
        nc_query = nc_query.filter(NewcomerProfile.team == team)
    newcomers = {n.id: n for n in nc_query.all()}
    if not newcomers:
        return []

    sessions = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id.in_(list(newcomers.keys())))
        .filter(ArenaSession.status == "ended")
        .all()
    )
    users_by_id = {
        u.id: u
        for u in db.query(User).filter(
            User.id.in_([n.user_id for n in newcomers.values()])
        ).all()
    }
    by_newcomer: dict[int, list[ArenaSession]] = {}
    for s in sessions:
        by_newcomer.setdefault(s.newcomer_id, []).append(s)

    out = []
    for nid, sess_list in by_newcomer.items():
        if not sess_list:
            continue
        avg = sum(s.overall_score or 0 for s in sess_list) / len(sess_list)
        nc = newcomers.get(nid)
        u = users_by_id.get(nc.user_id) if nc else None
        out.append(
            ArenaLeaderboardEntry(
                newcomer_id=nid,
                name=u.full_name if u else f"Newcomer #{nid}",
                overall_score=round(avg, 1),
                sessions_played=len(sess_list),
                streak=_compute_streak(sess_list),
            )
        )
    out.sort(key=lambda e: e.overall_score, reverse=True)
    return out[:limit]


@router.get("/newcomers/{newcomer_id}/summary", response_model=NewcomerArenaSummary)
def newcomer_summary(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = (
        db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    sessions = (
        db.query(ArenaSession)
        .filter(ArenaSession.newcomer_id == newcomer_id)
        .filter(ArenaSession.status == "ended")
        .order_by(ArenaSession.id.desc())
        .all()
    )

    if not sessions:
        return NewcomerArenaSummary(
            newcomer_id=newcomer_id,
            sessions_played=0,
            overall_score=0.0,
            streak=0,
            last_session_score=None,
        )

    avg_overall = round(
        sum(s.overall_score or 0 for s in sessions) / len(sessions), 1
    )
    last = sessions[0]
    badges: list[dict] = []
    for s in sessions:
        for b in s.badges_earned or []:
            badges.append(b)
    seen = set()
    unique_badges = []
    for b in badges:
        key = b.get("code")
        if key and key not in seen:
            seen.add(key)
            unique_badges.append(b)

    radar_avg = {d: 0.0 for d in ["opening", "discovery", "objections", "closing", "product_knowledge"]}
    counts = {d: 0 for d in radar_avg}
    for s in sessions:
        for d in radar_avg:
            v = (s.radar_scores or {}).get(d)
            if isinstance(v, (int, float)):
                radar_avg[d] += float(v)
                counts[d] += 1
    radar_payload = {d: int(radar_avg[d] / counts[d]) if counts[d] else 0 for d in radar_avg}

    return NewcomerArenaSummary(
        newcomer_id=newcomer_id,
        sessions_played=len(sessions),
        overall_score=avg_overall,
        streak=_compute_streak(sessions),
        last_session_score=last.overall_score,
        radar_scores=radar_payload,
        badges=unique_badges[:8],
    )


# ---------------------------------------------------------------------------
# Per-message coach (3-dot menu)


@router.post("/messages/{message_id}/coach")
async def coach_arena_message(message_id: int, db: Session = Depends(get_db)):
    message = db.query(ArenaMessage).filter(ArenaMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    session = (
        db.query(ArenaSession).filter(ArenaSession.id == message.session_id).first()
    )
    if not session or not session.scenario:
        raise HTTPException(status_code=404, detail="Session/scenario missing")
    return await coach_message(db, session, message)


# ---------------------------------------------------------------------------
# KB snippets for the sidebar quick-consult


@router.get("/sessions/{session_id}/kb-snippets")
def list_session_kb_snippets(session_id: int, db: Session = Depends(get_db)):
    session = (
        db.query(ArenaSession).filter(ArenaSession.id == session_id).first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ids: list[int] = list(session.scenario.kb_source_ids or [])
    if not ids:
        # Fallback: pick a few sales-relevant docs by domain
        docs = (
            db.query(Document)
            .filter(Document.domain.in_(["sales", "product", "finance", "general"]))
            .order_by(Document.id.desc())
            .limit(6)
            .all()
        )
    else:
        docs = db.query(Document).filter(Document.id.in_(ids)).all()

    out = []
    for d in docs:
        content = (d.content or "").strip()
        snippet = content[:280]
        out.append(
            {
                "id": d.id,
                "title": d.title,
                "document_type": d.document_type,
                "domain": d.domain,
                "source": d.source,
                "snippet": snippet,
            }
        )
    return out


@router.get("/kb-options")
def list_kb_options(domain: str | None = None, db: Session = Depends(get_db)):
    """
    Lightweight document list used by the scenario / personal-bot builders.
    """
    query = db.query(Document)
    if domain:
        query = query.filter(Document.domain == domain)
    docs = query.order_by(Document.id.desc()).limit(80).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "document_type": d.document_type,
            "domain": d.domain,
            "scope": d.scope,
            "preview": (d.content or "")[:140],
        }
        for d in docs
    ]


# ---------------------------------------------------------------------------
# Personal bot — signal-driven suggestions + spec preview + create-from-spec


@router.get("/personal-bot/suggestions")
def personal_bot_suggestions(newcomer_id: int, db: Session = Depends(get_db)):
    return suggestions_for_newcomer(db, newcomer_id)


@router.post("/personal-bot/preview")
async def personal_bot_preview(payload: dict, db: Session = Depends(get_db)):
    """
    Payload: { newcomer_id, focus_dimensions[], pain_text, source_ids[] }
    Returns the AI-generated spec WITHOUT persisting.
    """
    newcomer_id = payload.get("newcomer_id")
    if not newcomer_id:
        raise HTTPException(status_code=400, detail="newcomer_id required")
    newcomer = (
        db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    spec = await build_personal_bot_spec(
        db,
        newcomer,
        focus_dimensions=payload.get("focus_dimensions") or [],
        pain_text=payload.get("pain_text") or "",
        source_ids=list(payload.get("source_ids") or []),
    )
    return spec


@router.post("/personal-bot/from-spec", response_model=ArenaScenarioRead)
def personal_bot_from_spec(payload: dict, db: Session = Depends(get_db)):
    """
    Payload: { newcomer_id, spec, source_ids[] }
    Persists the (possibly edited) spec as a personal-bot scenario.
    """
    newcomer_id = payload.get("newcomer_id")
    spec = payload.get("spec")
    if not newcomer_id or not isinstance(spec, dict):
        raise HTTPException(status_code=400, detail="newcomer_id and spec required")
    newcomer = (
        db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    )
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    scenario = persist_spec(
        db,
        newcomer,
        spec=spec,
        source_ids=list(payload.get("source_ids") or []),
    )
    return _scenario_to_read(scenario, locked=False, attempts=0, last_score=None)
