"""Capture 模块业务逻辑（P0-1 内容捕获与知识提取）。

流水线（对应技术架构 §3.2.2）：
  extract_clean_text → llm_extract_concepts → vector_search_relations
  → save_concepts → trigger_card_generation
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import llm
from app.ai.embedding import embed_text
from app.core.database import async_session_factory
from app.models.capture import Capture
from app.models.card import Card
from app.models.concept import ConceptEdge, ConceptNode
from app.models.enums import CaptureStatus, CardType, ConceptRelationType, Domain
from app.services.concept_graph_service import find_related_concepts

# 领域 -> 卡片类型的默认映射
_DOMAIN_CARD_TYPE = {
    Domain.LANGUAGE: CardType.VOCABULARY,
    Domain.HUMANITIES: CardType.CONCEPT,
    Domain.SKILL: CardType.TECHNIQUE,
}


async def create_capture(
    db: AsyncSession,
    user_id: uuid.UUID,
    domain: Domain,
    source_type,
    raw_content: str,
    source_url: str | None,
) -> Capture:
    """落库一条 pending 状态的 Capture 记录。"""
    capture = Capture(
        user_id=user_id,
        domain=domain,
        source_type=source_type,
        source_url=source_url,
        raw_content=raw_content,
        status=CaptureStatus.PENDING,
    )
    db.add(capture)
    await db.commit()
    await db.refresh(capture)
    return capture


async def process_capture(capture_id: uuid.UUID) -> None:
    """后台流水线：提取概念 → 语义关联 → 存概念 → 生成卡片。

    独立开启 DB 会话（供 BackgroundTasks / Celery 调用，与请求生命周期解耦）。
    """
    async with async_session_factory() as db:
        capture = await db.get(Capture, capture_id)
        if capture is None:
            return

        capture.status = CaptureStatus.PROCESSING
        await db.commit()

        try:
            # 1. LLM 提取摘要 + 概念
            result = await llm.extract_concepts(capture.raw_content or "")
            capture.summary = result.get("summary")
            concepts_data = result.get("concepts", [])

            for item in concepts_data:
                label = item.get("label", "").strip()
                definition = item.get("definition", "").strip()
                if not label:
                    continue

                # 2. 概念向量化（当前 embedding 未接入，返回 None）
                embedding = await embed_text(f"{label}: {definition}")

                # 3. 语义关联搜索（embedding 为 None 时返回空）
                related = await find_related_concepts(db, capture.user_id, embedding)

                # 4. 存概念节点
                node = ConceptNode(
                    user_id=capture.user_id,
                    capture_id=capture.id,
                    domain=capture.domain,
                    label=label,
                    definition=definition,
                    embedding=embedding,
                )
                db.add(node)
                await db.flush()

                # 4b. 为关联概念建边
                for rel in related:
                    db.add(
                        ConceptEdge(
                            source_id=node.id,
                            target_id=rel.id,
                            relation_type=ConceptRelationType.EXTENDS,
                            is_ai_generated=True,
                        )
                    )

                # 5. 触发卡片生成
                card_result = await llm.generate_cards(label, definition)
                for card_item in card_result.get("cards", []):
                    front = card_item.get("front_content", "").strip()
                    back = card_item.get("back_content", "").strip()
                    if not front or not back:
                        continue
                    db.add(
                        Card(
                            user_id=capture.user_id,
                            domain=capture.domain,
                            card_type=_DOMAIN_CARD_TYPE.get(capture.domain, CardType.CONCEPT),
                            front_content=front,
                            back_content=back,
                            source_concept_id=node.id,
                        )
                    )

            capture.status = CaptureStatus.COMPLETED
            await db.commit()

        except Exception:
            await db.rollback()
            # 单独把状态置为 failed
            capture = await db.get(Capture, capture_id)
            if capture is not None:
                capture.status = CaptureStatus.FAILED
                await db.commit()
            raise


async def get_capture(db: AsyncSession, capture_id: uuid.UUID, user_id: uuid.UUID) -> Capture | None:
    capture = await db.get(Capture, capture_id)
    if capture is None or capture.user_id != user_id:
        return None
    return capture


async def get_capture_concepts(db: AsyncSession, capture_id: uuid.UUID) -> list[ConceptNode]:
    stmt = (
        select(ConceptNode)
        .where(ConceptNode.capture_id == capture_id)
        .options(selectinload(ConceptNode.cards), selectinload(ConceptNode.outgoing_edges))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
