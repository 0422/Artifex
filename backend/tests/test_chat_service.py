import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.models.enums import (
    ChatMessageRole,
    ChatSessionStatus,
    ScenarioDifficulty,
    ScenarioLanguage,
)
from app.schemas.chat import ChatCorrection
from app.services import chat_service


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_start_session_persists_title_snapshot_and_opening(db: MagicMock) -> None:
    user_id = uuid.uuid4()
    scenario = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        title="餐厅点餐",
        description="练习点餐。",
        language=ScenarioLanguage.JA,
        difficulty=ScenarioDifficulty.N4,
        is_active=True,
    )

    with patch.object(chat_service, "get_scenario", AsyncMock(return_value=scenario)):
        session, opening = await chat_service.start_session(
            db, user_id, scenario.id, ScenarioDifficulty.N3
        )

    assert session.scenario_id == scenario.id
    assert session.scenario == "餐厅点餐"
    assert session.language == "ja"
    assert session.difficulty == "N3"
    assert opening.role == ChatMessageRole.ASSISTANT
    assert "餐厅点餐" in opening.content
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_session_rejects_inactive_scenario(db: MagicMock) -> None:
    scenario = SimpleNamespace(is_active=False)
    with (
        patch.object(chat_service, "get_scenario", AsyncMock(return_value=scenario)),
        pytest.raises(chat_service.ScenarioUnavailableError),
    ):
        await chat_service.start_session(db, uuid.uuid4(), uuid.uuid4())

    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_append_turn_persists_user_and_assistant_messages(db: MagicMock) -> None:
    user_id = uuid.uuid4()
    scenario = SimpleNamespace(
        id=uuid.uuid4(),
        title="Coffee shop",
        description="Order a drink.",
        language=ScenarioLanguage.EN,
        difficulty=ScenarioDifficulty.A2,
        is_active=True,
    )
    session = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        scenario_id=scenario.id,
        status=ChatSessionStatus.ACTIVE,
        language="en",
        difficulty="A2",
    )
    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=history_result)

    with (
        patch.object(chat_service, "get_scenario", AsyncMock(return_value=scenario)),
        patch.object(
            chat_service.llm,
            "generate_chat_turn",
            AsyncMock(
                return_value={
                    "reply": "Certainly. What size would you like?",
                    "correction": None,
                }
            ),
        ) as generate_turn,
    ):
        turn = await chat_service.append_turn(db, session, "I would like some coffee.")

    messages = [call.args[0] for call in db.add.call_args_list]
    assert messages[0].role == ChatMessageRole.USER
    assert messages[0].content == "I would like some coffee."
    assert turn.assistant_message.role == ChatMessageRole.ASSISTANT
    assert turn.assistant_message.content == "Certainly. What size would you like?"
    assert turn.correction is None
    assert turn.degraded is False
    assert generate_turn.await_args.args[1] == []
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_append_turn_stores_progressive_correction(db: MagicMock) -> None:
    user_id = uuid.uuid4()
    scenario = SimpleNamespace(
        id=uuid.uuid4(),
        title="餐厅点餐",
        description="练习点餐。",
        language=ScenarioLanguage.JA,
        difficulty=ScenarioDifficulty.N4,
        is_active=True,
    )
    session = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        scenario_id=scenario.id,
        status=ChatSessionStatus.ACTIVE,
        language="ja",
        difficulty="N4",
    )
    previous = SimpleNamespace(
        role=ChatMessageRole.ASSISTANT,
        content="何を注文しますか？",
    )
    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = [previous]
    db.execute = AsyncMock(return_value=history_result)

    with (
        patch.object(chat_service, "get_scenario", AsyncMock(return_value=scenario)),
        patch.object(
            chat_service.llm,
            "generate_chat_turn",
            AsyncMock(
                return_value={
                    "reply": "かしこまりました。お飲み物はいかがですか？",
                    "correction": {
                        "original": "水を一つください",
                        "corrected": "水を一杯ください",
                        "severity": "minor",
                        "explanation": "饮料通常使用量词「一杯」。",
                    },
                }
            ),
        ) as generate_turn,
    ):
        turn = await chat_service.append_turn(db, session, "水を一つください")

    assert turn.correction == ChatCorrection(
        original="水を一つください",
        corrected="水を一杯ください",
        severity="minor",
        explanation="饮料通常使用量词「一杯」。",
    )
    assert turn.user_message.correction["severity"] == "minor"
    assert generate_turn.await_args.args[1] == [
        {"role": "assistant", "content": "何を注文しますか？"}
    ]


@pytest.mark.asyncio
async def test_append_turn_falls_back_when_llm_output_is_invalid(db: MagicMock) -> None:
    scenario = SimpleNamespace(
        id=uuid.uuid4(),
        title="问路",
        description="询问路线。",
        language=ScenarioLanguage.JA,
        difficulty=ScenarioDifficulty.N4,
        is_active=True,
    )
    session = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        scenario_id=scenario.id,
        status=ChatSessionStatus.ACTIVE,
        language="ja",
        difficulty="N4",
    )
    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=history_result)

    with (
        patch.object(chat_service, "get_scenario", AsyncMock(return_value=scenario)),
        patch.object(
            chat_service.llm,
            "generate_chat_turn",
            AsyncMock(return_value={"reply": "", "correction": None}),
        ),
    ):
        turn = await chat_service.append_turn(db, session, "駅はどこですか？")

    assert turn.degraded is True
    assert turn.correction is None
    assert (
        turn.assistant_message.content
        == "ありがとうございます。もう少し詳しく話してください。"
    )


@pytest.mark.asyncio
async def test_complete_session_is_idempotent(db: MagicMock) -> None:
    session = SimpleNamespace(
        id=uuid.uuid4(),
        status=ChatSessionStatus.ACTIVE,
        created_at=datetime.now(UTC) - timedelta(seconds=5),
        ended_at=None,
        duration_seconds=0,
    )

    await chat_service.complete_session(db, session)
    first_duration = session.duration_seconds
    await chat_service.complete_session(db, session)

    assert session.status == ChatSessionStatus.COMPLETED
    assert first_duration >= 5
    assert session.duration_seconds == first_duration
    db.commit.assert_awaited_once()


def test_chat_session_ended_at_is_timezone_aware() -> None:
    assert ChatSession.__table__.c.ended_at.type.timezone is True
