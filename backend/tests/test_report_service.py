import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ChatMessageRole, Domain, LearningEventType
from app.models.event import LearningEvent
from app.schemas.report import SessionReport
from app.services import report_service


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def make_session(report=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        scenario_id=uuid.uuid4(),
        scenario="餐厅点餐",
        language="ja",
        difficulty="N4",
        duration_seconds=240,
        report=report,
    )


def set_messages(db: MagicMock, messages: list[SimpleNamespace]) -> None:
    result = MagicMock()
    result.scalars.return_value.all.return_value = messages
    db.execute = AsyncMock(return_value=result)


@pytest.mark.asyncio
async def test_generate_report_persists_report_and_learning_event(
    db: MagicMock,
) -> None:
    session = make_session()
    messages = [
        SimpleNamespace(
            role=ChatMessageRole.ASSISTANT,
            content="何を注文しますか？",
            correction=None,
        ),
        SimpleNamespace(
            role=ChatMessageRole.USER,
            content="水を一つください。",
            correction={"severity": "minor"},
        ),
    ]
    set_messages(db, messages)
    llm_output = {
        "summary": "用户完成了点餐任务，表达清楚。",
        "weak_points": [
            {
                "category": "grammar",
                "tag": "grammar:counter-cups",
                "description": "饮料量词使用不准确。",
                "example": "水を一つください。",
                "suggestion": "练习杯、瓶等饮料量词。",
            }
        ],
        "suggestions": ["复习常见饮料量词。"],
        "performance_score": 82,
        "no_prominent_issues": False,
    }

    with patch.object(
        report_service.llm,
        "generate_session_report",
        AsyncMock(return_value=llm_output),
    ):
        report = await report_service.generate_session_report(db, session)

    assert report.performance_score == 82
    assert session.report["weak_points"][0]["tag"] == "grammar:counter-cups"
    event = db.add.call_args.args[0]
    assert isinstance(event, LearningEvent)
    assert event.domain == Domain.LANGUAGE
    assert event.event_type == LearningEventType.CONVERSATION_PRACTICE
    assert event.duration_minutes == 4
    assert event.meta["performance_score"] == 82
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_report_without_user_messages_skips_llm(db: MagicMock) -> None:
    session = make_session()
    set_messages(
        db,
        [
            SimpleNamespace(
                role=ChatMessageRole.ASSISTANT,
                content="こんにちは。",
                correction=None,
            )
        ],
    )

    with patch.object(
        report_service.llm, "generate_session_report", AsyncMock()
    ) as generate:
        report = await report_service.generate_session_report(db, session)

    assert report.insufficient_data is True
    assert report.performance_score is None
    generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_report_returns_existing_report_idempotently(
    db: MagicMock,
) -> None:
    existing = SessionReport(
        summary="已生成报告。",
        suggestions=["继续练习。"],
        performance_score=88,
        no_prominent_issues=True,
    )
    session = make_session(existing.model_dump(mode="json"))

    report = await report_service.generate_session_report(db, session)

    assert report == existing
    db.execute.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_generate_report_falls_back_on_invalid_llm_output(db: MagicMock) -> None:
    session = make_session()
    set_messages(
        db,
        [
            SimpleNamespace(
                role=ChatMessageRole.USER,
                content="こんにちは。",
                correction=None,
            )
        ],
    )

    with patch.object(
        report_service.llm,
        "generate_session_report",
        AsyncMock(return_value={"summary": ""}),
    ):
        report = await report_service.generate_session_report(db, session)

    assert report.degraded is True
    assert report.performance_score is None
