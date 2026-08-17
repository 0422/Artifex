import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.report import SessionReport, WeakPoint
from app.services import dashboard_service


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def weak_point(tag: str = "grammar:countable-noun-plural") -> WeakPoint:
    return WeakPoint(
        category="grammar",
        tag=tag,
        description="复数形式遗漏。",
        example="two coffee",
        suggestion="练习可数名词复数。",
    )


def make_session(
    *,
    scenario_id: uuid.UUID | None,
    scenario: str,
    duration: int,
    score: int | None,
    points: list[WeakPoint] | None = None,
    degraded: bool = False,
    report_override=None,
    created_offset: int = 0,
) -> SimpleNamespace:
    report = SessionReport(
        summary="完成了练习。",
        weak_points=points or [],
        suggestions=["继续练习。"],
        performance_score=score,
        no_prominent_issues=not points,
        degraded=degraded,
    ).model_dump(mode="json")
    if report_override is not None:
        report = report_override
    now = datetime.now(UTC) - timedelta(minutes=created_offset)
    return SimpleNamespace(
        id=uuid.uuid4(),
        scenario_id=scenario_id,
        scenario=scenario,
        language="en",
        difficulty="A2",
        duration_seconds=duration,
        report=report,
        created_at=now,
        ended_at=now + timedelta(seconds=duration),
    )


@pytest.mark.asyncio
async def test_overview_uses_explicit_statistical_denominators(db: MagicMock) -> None:
    shared_scenario_id = uuid.uuid4()
    point = weak_point()
    sessions = [
        make_session(
            scenario_id=shared_scenario_id,
            scenario="Coffee shop order",
            duration=180,
            score=80,
            points=[point, point],
        ),
        make_session(
            scenario_id=shared_scenario_id,
            scenario="Old coffee shop title",
            duration=240,
            score=90,
            points=[point],
            created_offset=10,
        ),
        make_session(
            scenario_id=None,
            scenario="Legacy session",
            duration=60,
            score=None,
            degraded=True,
            created_offset=20,
        ),
    ]
    result = MagicMock()
    result.scalars.return_value.all.return_value = sessions
    db.execute = AsyncMock(return_value=result)

    overview = await dashboard_service.get_overview(db, uuid.uuid4())

    assert overview.total_conversations == 3
    assert overview.total_duration_seconds == 480
    assert overview.scored_conversations == 2
    assert overview.average_performance_score == 85.0
    assert overview.scenario_distribution[0].scenario_id == shared_scenario_id
    assert overview.scenario_distribution[0].title == "Coffee shop order"
    assert overview.scenario_distribution[0].count == 2
    assert overview.frequent_weak_points[0].tag == point.tag
    assert overview.frequent_weak_points[0].count == 2


@pytest.mark.asyncio
async def test_session_history_is_paginated_and_handles_invalid_report(
    db: MagicMock,
) -> None:
    session = make_session(
        scenario_id=uuid.uuid4(),
        scenario="问路",
        duration=120,
        score=75,
        report_override={"legacy": "invalid"},
    )
    total_result = MagicMock()
    total_result.scalar_one.return_value = 1
    sessions_result = MagicMock()
    sessions_result.scalars.return_value.all.return_value = [session]
    db.execute = AsyncMock(side_effect=[total_result, sessions_result])

    page = await dashboard_service.get_sessions(db, uuid.uuid4(), 2, 10)

    assert page.total == 1
    assert page.page == 2
    assert page.page_size == 10
    assert page.items[0].report_status == "invalid"
    assert page.items[0].performance_score is None


@pytest.mark.asyncio
async def test_session_detail_returns_none_for_unknown_or_unowned_session(
    db: MagicMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    detail = await dashboard_service.get_session_detail(db, uuid.uuid4(), uuid.uuid4())

    assert detail is None
