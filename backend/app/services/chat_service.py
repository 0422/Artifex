import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from openai import OpenAIError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import llm
from app.models.chat import ChatMessage, ChatSession
from app.models.enums import (
    ChatMessageRole,
    ChatSessionStatus,
    ScenarioDifficulty,
    ScenarioLanguage,
)
from app.models.scenario import ScenarioCard
from app.schemas.chat import ChatCorrection, ChatTurnOutput
from app.services.scenario_engine import build_scenario_prompt
from app.services.scenario_service import get_scenario

logger = logging.getLogger(__name__)

CHAT_HISTORY_LIMIT = 20
CHAT_LLM_TIMEOUT_SECONDS = 60


class ScenarioUnavailableError(Exception):
    pass


class SessionNotActiveError(Exception):
    pass


@dataclass
class ChatTurnResult:
    user_message: ChatMessage
    assistant_message: ChatMessage
    correction: ChatCorrection | None
    degraded: bool = False


def _opening_message(scenario: ScenarioCard) -> str:
    if getattr(scenario, "scenario_mode", "role_play") != "role_play":
        return f"我们来讨论“{scenario.title}”。{scenario.description} 你想先从哪个角度开始？"
    if scenario.language == ScenarioLanguage.JA:
        return f"こんにちは。今日は「{scenario.title}」の場面を練習しましょう。準備ができたら始めてください。"
    return f'Hello! Let\'s practice "{scenario.title}". Start when you are ready.'


def _placeholder_reply(language: str) -> str:
    if language == ScenarioLanguage.ZH.value:
        return "这个观点值得继续展开。你能结合一个事实或例子说明理由吗？"
    if language == ScenarioLanguage.JA.value:
        return "ありがとうございます。もう少し詳しく話してください。"
    return "Thanks. Please tell me a little more."


async def start_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    scenario_id: uuid.UUID,
    difficulty: ScenarioDifficulty | None = None,
) -> tuple[ChatSession, ChatMessage]:
    scenario = await get_scenario(db, scenario_id, user_id)
    if scenario is None or not scenario.is_active:
        raise ScenarioUnavailableError(scenario_id)

    selected_difficulty = difficulty or scenario.difficulty
    session = ChatSession(
        user_id=user_id,
        scenario_id=scenario.id,
        scenario=scenario.title,
        language=scenario.language.value,
        difficulty=selected_difficulty.value,
        status=ChatSessionStatus.ACTIVE,
    )
    db.add(session)
    await db.flush()

    opening = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.ASSISTANT,
        content=_opening_message(scenario),
    )
    db.add(opening)
    await db.commit()
    await db.refresh(session)
    await db.refresh(opening)
    return session, opening


async def append_turn(
    db: AsyncSession, session: ChatSession, user_content: str
) -> ChatTurnResult:
    if session.status != ChatSessionStatus.ACTIVE:
        raise SessionNotActiveError(session.id)

    scenario = await get_scenario(db, session.scenario_id, session.user_id)
    if scenario is None:
        raise ScenarioUnavailableError(session.scenario_id)

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(CHAT_HISTORY_LIMIT)
    )
    history_messages = list(reversed(history_result.scalars().all()))
    history = [
        {"role": message.role.value, "content": message.content}
        for message in history_messages
        if message.role in (ChatMessageRole.USER, ChatMessageRole.ASSISTANT)
    ]

    user_message = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.USER,
        content=user_content,
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    degraded = False
    correction: ChatCorrection | None = None
    try:
        raw_output = await asyncio.wait_for(
            llm.generate_chat_turn(
                build_scenario_prompt(scenario, ScenarioDifficulty(session.difficulty)),
                history,
                user_content,
            ),
            timeout=CHAT_LLM_TIMEOUT_SECONDS,
        )
        output = ChatTurnOutput.model_validate(raw_output)
        correction = output.correction
        if correction is not None:
            correction.original = user_content
            if correction.corrected == user_content:
                correction = None
        reply_content = output.reply
    except (TimeoutError, OpenAIError, ValidationError, ValueError) as exc:
        logger.warning(
            "Chat LLM fallback for session %s: %s", session.id, type(exc).__name__
        )
        degraded = True
        reply_content = _placeholder_reply(session.language)

    user_message.correction = (
        correction.model_dump(mode="json") if correction is not None else None
    )
    reply = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.ASSISTANT,
        content=reply_content,
    )
    db.add(reply)
    await db.commit()
    await db.refresh(user_message)
    await db.refresh(reply)
    return ChatTurnResult(
        user_message=user_message,
        assistant_message=reply,
        correction=correction,
        degraded=degraded,
    )


async def complete_session(db: AsyncSession, session: ChatSession) -> ChatSession:
    if session.status != ChatSessionStatus.ACTIVE:
        return session

    ended_at = datetime.now(UTC)
    started_at = session.created_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)

    session.status = ChatSessionStatus.COMPLETED
    session.ended_at = ended_at
    session.duration_seconds = max(0, int((ended_at - started_at).total_seconds()))
    await db.commit()
    await db.refresh(session)
    return session


async def complete_session_by_id(
    db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None
    return await complete_session(db, session)
