import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenType, decode_token
from app.models.chat import ChatSession
from app.models.user import User
from app.schemas.chat import (
    AiResponseEvent,
    AuthenticatedEvent,
    AuthenticateMessage,
    ChatErrorEvent,
    CorrectionEvent,
    EndSessionMessage,
    ReportGeneratingEvent,
    SessionEndedEvent,
    SessionReportEvent,
    SessionStartedEvent,
    StartSessionMessage,
    TextMessage,
    chat_command_adapter,
)
from app.services import chat_service
from app.services.auth_service import get_user_by_id
from app.services.report_service import generate_session_report

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

AUTH_TIMEOUT_SECONDS = 10


async def _send_event(websocket: WebSocket, event) -> None:
    await websocket.send_json(event.model_dump(mode="json"))


async def _send_error(
    websocket: WebSocket,
    code: str,
    message: str,
    *,
    recoverable: bool = True,
) -> None:
    await _send_event(
        websocket,
        ChatErrorEvent(code=code, message=message, recoverable=recoverable),
    )


async def _authenticate(websocket: WebSocket, db: AsyncSession) -> User | None:
    try:
        raw_message = await asyncio.wait_for(
            websocket.receive_json(), timeout=AUTH_TIMEOUT_SECONDS
        )
        message = AuthenticateMessage.model_validate(raw_message)
        payload = decode_token(message.token, TokenType.ACCESS)
        user_id = uuid.UUID(payload["sub"])
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise ValueError("user not found")
    except asyncio.TimeoutError:
        await _send_error(
            websocket, "authentication_timeout", "鉴权超时", recoverable=False
        )
    except WebSocketDisconnect:
        return None
    except (ValidationError, JWTError, ValueError, KeyError):
        await _send_error(
            websocket,
            "authentication_failed",
            "登录凭证无效或已过期",
            recoverable=False,
        )
    else:
        await _send_event(websocket, AuthenticatedEvent(user_id=user.id))
        return user

    await websocket.close(code=4401)
    return None


@router.websocket("/ws")
async def chat_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
) -> None:
    await websocket.accept()
    user = await _authenticate(websocket, db)
    if user is None:
        return

    active_session: ChatSession | None = None
    active_session_id: uuid.UUID | None = None
    try:
        while True:
            try:
                raw_message = await websocket.receive_json()
                command = chat_command_adapter.validate_python(raw_message)
            except (ValidationError, json.JSONDecodeError):
                await _send_error(websocket, "invalid_message", "消息格式无效")
                continue

            if isinstance(command, StartSessionMessage):
                if active_session is not None:
                    await _send_error(
                        websocket, "session_already_active", "请先结束当前会话"
                    )
                    continue
                try:
                    active_session, opening = await chat_service.start_session(
                        db,
                        user.id,
                        command.scenario_id,
                        command.difficulty,
                    )
                except chat_service.ScenarioUnavailableError:
                    await _send_error(
                        websocket, "scenario_unavailable", "场景不存在或已停用"
                    )
                    continue

                active_session_id = active_session.id

                await _send_event(
                    websocket,
                    SessionStartedEvent(
                        session_id=active_session.id,
                        scenario_id=active_session.scenario_id,
                        scenario_title=active_session.scenario,
                        language=active_session.language,
                        difficulty=active_session.difficulty,
                        started_at=active_session.created_at,
                    ),
                )
                await _send_event(
                    websocket,
                    AiResponseEvent(
                        message_id=opening.id,
                        content=opening.content,
                        created_at=opening.created_at,
                    ),
                )
                continue

            if active_session is None:
                await _send_error(websocket, "no_active_session", "请先开始会话")
                continue

            if isinstance(command, TextMessage):
                turn = await chat_service.append_turn(
                    db, active_session, command.content
                )
                await _send_event(
                    websocket,
                    AiResponseEvent(
                        message_id=turn.assistant_message.id,
                        content=turn.assistant_message.content,
                        created_at=turn.assistant_message.created_at,
                        degraded=turn.degraded,
                    ),
                )
                if turn.correction is not None:
                    await _send_event(
                        websocket,
                        CorrectionEvent(
                            message_id=turn.user_message.id,
                            **turn.correction.model_dump(),
                        ),
                    )
                continue

            if isinstance(command, EndSessionMessage):
                active_session = await chat_service.complete_session(db, active_session)
                await _send_event(
                    websocket,
                    SessionEndedEvent(
                        session_id=active_session.id,
                        duration_seconds=active_session.duration_seconds,
                        ended_at=active_session.ended_at,
                    ),
                )
                await _send_event(
                    websocket,
                    ReportGeneratingEvent(session_id=active_session.id),
                )
                report = await generate_session_report(db, active_session)
                await _send_event(
                    websocket,
                    SessionReportEvent(
                        session_id=active_session.id,
                        report=report,
                    ),
                )
                active_session = None
                active_session_id = None

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unexpected chat WebSocket failure")
        await db.rollback()
        if active_session_id is not None:
            try:
                await chat_service.complete_session_by_id(
                    db, active_session_id, user.id
                )
            except Exception:
                logger.exception("Failed to recover failed chat session")
                await db.rollback()
        active_session = None
        active_session_id = None
        try:
            await _send_error(
                websocket, "internal_error", "会话服务暂时不可用", recoverable=False
            )
            await websocket.close(code=1011)
        except RuntimeError:
            pass
    finally:
        if active_session is not None:
            try:
                await chat_service.complete_session(db, active_session)
            except Exception:
                logger.exception("Failed to complete disconnected chat session")
                await db.rollback()
