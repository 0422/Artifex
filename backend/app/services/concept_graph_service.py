"""知识图谱服务：概念的语义关联搜索。

对应技术架构 §3.2.2 Relation Mapper / §3.2.7 Concept Graph Module。
语义关联依赖 embedding；当前 embedding 未接入（中转站不支持），
find_related_concepts 会直接返回空列表，不阻塞主链路。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding import EMBEDDING_ENABLED
from app.models.concept import ConceptNode

# cosine 相似度阈值（技术架构 §3.2.2：> 0.75 视为关联）
SIMILARITY_THRESHOLD = 0.75
TOP_K = 5


async def find_related_concepts(
    db: AsyncSession,
    user_id: uuid.UUID,
    embedding: list[float] | None,
    exclude_id: uuid.UUID | None = None,
) -> list[ConceptNode]:
    """基于向量相似度找出用户已有的关联概念。

    embedding 为 None 或服务未启用时返回空列表（语义关联功能暂不可用）。
    """
    if not EMBEDDING_ENABLED or embedding is None:
        return []

    # pgvector cosine 距离：距离 = 1 - cosine_similarity，阈值 0.75 相似度 => 距离 < 0.25
    stmt = (
        select(ConceptNode)
        .where(ConceptNode.user_id == user_id)
        .where(ConceptNode.embedding.is_not(None))
        .where(ConceptNode.embedding.cosine_distance(embedding) < (1 - SIMILARITY_THRESHOLD))
        .order_by(ConceptNode.embedding.cosine_distance(embedding))
        .limit(TOP_K)
    )
    if exclude_id is not None:
        stmt = stmt.where(ConceptNode.id != exclude_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())
