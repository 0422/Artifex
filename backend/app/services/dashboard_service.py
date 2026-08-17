import uuid
from collections import Counter

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.models.enums import ChatSessionStatus
from app.schemas.dashboard import (
    DashboardOverview,
    DashboardSessionDetail,
    DashboardSessionItem,
    DashboardSessionPage,
    ReportStatus,
    ScenarioDistributionItem,
    WeakPointFrequency,
)
from app.schemas.report import SessionReport


def _parse_report(session: ChatSession) -> tuple[SessionReport | None, ReportStatus]:
    if session.report is None:
        return None, "missing"
    try:
        report = SessionReport.model_validate(session.report)
    except ValidationError:
        return None, "invalid"
    if report.degraded:
        return report, "degraded"
    if report.insufficient_data:
        return report, "insufficient_data"
    return report, "ready"


def _session_item(session: ChatSession) -> DashboardSessionItem:
    report, report_status = _parse_report(session)
    return DashboardSessionItem(
        id=session.id,
        scenario_id=session.scenario_id,
        scenario_title=session.scenario,
        language=session.language,
        difficulty=session.difficulty,
        duration_seconds=session.duration_seconds,
        performance_score=report.performance_score if report else None,
        weak_points_count=len(report.weak_points) if report else 0,
        report_status=report_status,
        created_at=session.created_at,
        ended_at=session.ended_at,
    )


async def get_overview(db: AsyncSession, user_id: uuid.UUID) -> DashboardOverview:
    result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.user_id == user_id,
            ChatSession.status == ChatSessionStatus.COMPLETED,
        )
        .order_by(ChatSession.created_at.desc())
    )
    sessions = list(result.scalars().all())

    scores: list[int] = []
    scenario_counts: dict[str, ScenarioDistributionItem] = {}
    weak_point_counts: Counter[tuple[str, str]] = Counter()

    for session in sessions:
        scenario_key = (
            str(session.scenario_id)
            if session.scenario_id is not None
            else f"snapshot:{session.scenario}"
        )
        if scenario_key not in scenario_counts:
            scenario_counts[scenario_key] = ScenarioDistributionItem(
                scenario_id=session.scenario_id,
                title=session.scenario,
                count=1,
            )
        else:
            scenario_counts[scenario_key].count += 1

        report, _ = _parse_report(session)
        if report is None:
            continue
        if report.performance_score is not None:
            scores.append(report.performance_score)
        unique_points = {(point.tag, point.category) for point in report.weak_points}
        weak_point_counts.update(unique_points)

    scenario_distribution = sorted(
        scenario_counts.values(), key=lambda item: (-item.count, item.title)
    )
    frequent_weak_points = [
        WeakPointFrequency(tag=tag, category=category, count=count)
        for (tag, category), count in sorted(
            weak_point_counts.items(), key=lambda item: (-item[1], item[0][0])
        )
    ][:10]

    return DashboardOverview(
        total_conversations=len(sessions),
        total_duration_seconds=sum(session.duration_seconds for session in sessions),
        scored_conversations=len(scores),
        average_performance_score=round(sum(scores) / len(scores), 1)
        if scores
        else None,
        scenario_distribution=scenario_distribution,
        frequent_weak_points=frequent_weak_points,
    )


async def get_sessions(
    db: AsyncSession, user_id: uuid.UUID, page: int, page_size: int
) -> DashboardSessionPage:
    filters = (
        ChatSession.user_id == user_id,
        ChatSession.status == ChatSessionStatus.COMPLETED,
    )
    total_result = await db.execute(
        select(func.count()).select_from(ChatSession).where(*filters)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(ChatSession)
        .where(*filters)
        .order_by(ChatSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    sessions = list(result.scalars().all())
    return DashboardSessionPage(
        items=[_session_item(session) for session in sessions],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_session_detail(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> DashboardSessionDetail | None:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
            ChatSession.status == ChatSessionStatus.COMPLETED,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    item = _session_item(session)
    report, _ = _parse_report(session)
    return DashboardSessionDetail(**item.model_dump(), report=report)
