import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import JWTError

from app.api.v1.chat import router
from app.core.database import get_db
from app.schemas.chat import ChatCorrection
from app.schemas.report import SessionReport


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return TestClient(app)


def test_websocket_runs_authenticated_session_lifecycle(client: TestClient) -> None:
    now = datetime.now(UTC)
    user = SimpleNamespace(id=uuid.uuid4())
    scenario_id = uuid.uuid4()
    session = SimpleNamespace(
        id=uuid.uuid4(),
        scenario_id=scenario_id,
        scenario="餐厅点餐",
        language="ja",
        difficulty="N4",
        created_at=now,
        duration_seconds=12,
        ended_at=now,
    )
    opening = SimpleNamespace(id=uuid.uuid4(), content="こんにちは。", created_at=now)
    reply = SimpleNamespace(
        id=uuid.uuid4(), content="ありがとうございます。", created_at=now
    )
    user_message = SimpleNamespace(id=uuid.uuid4())
    turn = SimpleNamespace(
        user_message=user_message,
        assistant_message=reply,
        correction=ChatCorrection(
            original="水を一つください",
            corrected="水を一杯ください",
            severity="minor",
            explanation="饮料通常使用量词「一杯」。",
        ),
        degraded=False,
    )
    report = SessionReport(
        summary="完成了餐厅点餐练习。",
        weak_points=[],
        suggestions=["继续练习量词。"],
        performance_score=82,
        no_prominent_issues=True,
    )

    with (
        patch("app.api.v1.chat.decode_token", return_value={"sub": str(user.id)}),
        patch("app.api.v1.chat.get_user_by_id", AsyncMock(return_value=user)),
        patch(
            "app.api.v1.chat.chat_service.start_session",
            AsyncMock(return_value=(session, opening)),
        ),
        patch(
            "app.api.v1.chat.chat_service.append_turn", AsyncMock(return_value=turn)
        ) as append_turn,
        patch(
            "app.api.v1.chat.chat_service.complete_session",
            AsyncMock(return_value=session),
        ) as complete_session,
        patch(
            "app.api.v1.chat.generate_session_report",
            AsyncMock(return_value=report),
        ) as generate_report,
        client.websocket_connect("/api/v1/chat/ws") as websocket,
    ):
        websocket.send_json({"type": "authenticate", "token": "access-token"})
        assert websocket.receive_json()["type"] == "authenticated"

        websocket.send_json({"type": "text_message", "content": "こんにちは"})
        assert websocket.receive_json()["code"] == "no_active_session"

        websocket.send_json({"type": "start_session", "scenario_id": str(scenario_id)})
        assert websocket.receive_json()["type"] == "session_started"
        assert websocket.receive_json()["type"] == "ai_response"

        websocket.send_json({"type": "text_message", "content": "注文します"})
        assert websocket.receive_json()["content"] == reply.content
        correction = websocket.receive_json()
        assert correction["type"] == "correction"
        assert correction["severity"] == "minor"
        assert correction["message_id"] == str(user_message.id)

        websocket.send_json({"type": "end_session"})
        assert websocket.receive_json()["type"] == "session_ended"
        assert websocket.receive_json()["type"] == "report_generating"
        report_event = websocket.receive_json()
        assert report_event["type"] == "session_report"
        assert report_event["report"]["performance_score"] == 82

    append_turn.assert_awaited_once()
    complete_session.assert_awaited_once()
    generate_report.assert_awaited_once_with(ANY, session)


def test_websocket_rejects_invalid_access_token(client: TestClient) -> None:
    with (
        patch("app.api.v1.chat.decode_token", side_effect=JWTError("invalid")),
        client.websocket_connect("/api/v1/chat/ws") as websocket,
    ):
        websocket.send_json({"type": "authenticate", "token": "invalid-token"})
        event = websocket.receive_json()

    assert event == {
        "type": "error",
        "code": "authentication_failed",
        "message": "登录凭证无效或已过期",
        "recoverable": False,
    }


def test_websocket_completes_active_session_on_disconnect(client: TestClient) -> None:
    now = datetime.now(UTC)
    user = SimpleNamespace(id=uuid.uuid4())
    session = SimpleNamespace(
        id=uuid.uuid4(),
        scenario_id=uuid.uuid4(),
        scenario="问路",
        language="ja",
        difficulty="N4",
        created_at=now,
    )
    opening = SimpleNamespace(id=uuid.uuid4(), content="こんにちは。", created_at=now)

    with (
        patch("app.api.v1.chat.decode_token", return_value={"sub": str(user.id)}),
        patch("app.api.v1.chat.get_user_by_id", AsyncMock(return_value=user)),
        patch(
            "app.api.v1.chat.chat_service.start_session",
            AsyncMock(return_value=(session, opening)),
        ),
        patch(
            "app.api.v1.chat.chat_service.complete_session",
            AsyncMock(return_value=session),
        ) as complete_session,
        client.websocket_connect("/api/v1/chat/ws") as websocket,
    ):
        websocket.send_json({"type": "authenticate", "token": "access-token"})
        websocket.receive_json()
        websocket.send_json(
            {"type": "start_session", "scenario_id": str(session.scenario_id)}
        )
        websocket.receive_json()
        websocket.receive_json()

    complete_session.assert_awaited_once()
