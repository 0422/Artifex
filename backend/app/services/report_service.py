import asyncio
import logging
import uuid

from openai import OpenAIError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import llm
from app.models.chat import ChatMessage, ChatSession
from app.models.enums import ChatMessageRole, Domain, LearningEventType
from app.models.event import LearningEvent
from app.schemas.report import SessionReport, SessionReportOutput

logger = logging.getLogger(__name__)

REPORT_LLM_TIMEOUT_SECONDS = 90


async def _load_messages(db: AsyncSession, session_id: uuid.UUID) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result.scalars().all())


def _insufficient_data_report(session: ChatSession) -> SessionReport:
    return SessionReport(
        summary=f"本次已进入“{session.scenario}”场景，但没有足够的学习者发言可供分析。",
        weak_points=[],
        suggestions=["完成至少 3 轮有效对话后再生成学情分析。"],
        performance_score=None,
        no_prominent_issues=True,
        insufficient_data=True,
    )


def _degraded_report(session: ChatSession) -> SessionReport:
    return SessionReport(
        summary=f"本次已完成“{session.scenario}”场景对话，但学情分析暂时不可用。",
        weak_points=[],
        suggestions=["稍后重新查看或再完成一次场景练习。"],
        performance_score=None,
        no_prominent_issues=True,
        degraded=True,
    )


async def generate_session_report(
    db: AsyncSession, session: ChatSession
) -> SessionReport:
    if session.report is not None:
        try:
            return SessionReport.model_validate(session.report)
        except ValidationError:
            logger.warning("Regenerating invalid report for session %s", session.id)

    messages = await _load_messages(db, session.id)
    user_messages = [
        message for message in messages if message.role == ChatMessageRole.USER
    ]

    if not user_messages:
        report = _insufficient_data_report(session)
    else:
        report_input = {
            "scenario": session.scenario,
            "language": session.language,
            "difficulty": session.difficulty,
            "duration_seconds": session.duration_seconds,
            "transcript": [
                {
                    "role": message.role.value,
                    "content": message.content,
                    "correction": message.correction,
                }
                for message in messages
                if message.role in (ChatMessageRole.USER, ChatMessageRole.ASSISTANT)
            ],
        }
        try:
            raw_report = await asyncio.wait_for(
                llm.generate_session_report(report_input),
                timeout=REPORT_LLM_TIMEOUT_SECONDS,
            )
            output = SessionReportOutput.model_validate(raw_report)
            report = SessionReport(**output.model_dump())
        except (TimeoutError, OpenAIError, ValidationError, ValueError) as exc:
            logger.warning(
                "Report LLM fallback for session %s: %s",
                session.id,
                type(exc).__name__,
            )
            report = _degraded_report(session)

    report_data = report.model_dump(mode="json")
    session.report = report_data
    db.add(
        LearningEvent(
            user_id=session.user_id,
            domain=Domain.LANGUAGE,
            event_type=LearningEventType.CONVERSATION_PRACTICE,
            depth="moderate",
            duration_minutes=session.duration_seconds / 60,
            meta={
                "session_id": str(session.id),
                "scenario_id": str(session.scenario_id)
                if session.scenario_id
                else None,
                "scenario": session.scenario,
                "performance_score": report.performance_score,
                "weak_point_tags": [point.tag for point in report.weak_points],
                "report_degraded": report.degraded,
                "insufficient_data": report.insufficient_data,
            },
        )
    )
    await db.commit()
    await db.refresh(session)
    return report
