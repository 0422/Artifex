# 2026-09-30 原先注册即建的 5 条默认日语场景已注释掉：场景现由知识库统一承载
# （雅思共享真题库 + 用户自建），auth_service.register_user 不再调用 create_seed_scenarios，
# 对话页初始为空、由用户自行选择。
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ScenarioDifficulty, ScenarioLanguage
from app.models.knowledge import KnowledgeCategory
from app.models.scenario import ScenarioCard
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate

# SEED_SCENARIOS = (
#     {
#         "title": "餐厅点餐",
#         "description": "在餐厅阅读菜单、询问菜品并完成点餐。",
#         "language": ScenarioLanguage.JA,
#         "difficulty": ScenarioDifficulty.N4,
#     },
#     {
#         "title": "便利店购物",
#         "description": "在便利店寻找商品、询问价格并完成结账。",
#         "language": ScenarioLanguage.JA,
#         "difficulty": ScenarioDifficulty.N5,
#     },
#     {
#         "title": "问路",
#         "description": "向路人询问目的地并确认路线和交通方式。",
#         "language": ScenarioLanguage.JA,
#         "difficulty": ScenarioDifficulty.N4,
#     },
#     {
#         "title": "自我介绍",
#         "description": "介绍自己的背景、兴趣、学习目标并回应追问。",
#         "language": ScenarioLanguage.JA,
#         "difficulty": ScenarioDifficulty.N4,
#     },
#     {
#         "title": "商务会议",
#         "description": "在会议中表达观点、确认信息并协商下一步行动。",
#         "language": ScenarioLanguage.JA,
#         "difficulty": ScenarioDifficulty.N3,
#     },
# )



class SharedReadOnlyError(PermissionError):
    """官方共享题库（user_id 为空）对所有用户只读，尝试改写时抛出。"""


def _visible_scenarios(user_id: uuid.UUID):
    """本人私有 + 官方共享。绝不能放宽成「所有用户的私有场景」。"""
    return or_(ScenarioCard.user_id == user_id, ScenarioCard.user_id.is_(None))


def _visible_categories(user_id: uuid.UUID):
    return or_(KnowledgeCategory.user_id == user_id, KnowledgeCategory.user_id.is_(None))


async def _category_and_descendant_ids(
    db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID
) -> list[uuid.UUID]:
    # 2026-09-30 递归收集子分类时要包含官方共享分类（雅思口语→Part→类别全是共享行），
    # 否则点「Part 1」取不到底下的真题。
    result = await db.execute(
        select(KnowledgeCategory.id, KnowledgeCategory.parent_id).where(
            _visible_categories(user_id),
            KnowledgeCategory.is_active.is_(True),
        )
    )
    children: dict[uuid.UUID | None, list[uuid.UUID]] = {}
    for current_id, parent_id in result.all():
        children.setdefault(parent_id, []).append(current_id)
    ids: list[uuid.UUID] = []
    pending = [category_id]
    while pending:
        current = pending.pop()
        if current in ids:
            continue
        ids.append(current)
        pending.extend(children.get(current, []))
    return ids

# async def create_seed_scenarios(
#     db: AsyncSession, user_id: uuid.UUID
# ) -> list[ScenarioCard]:
#     scenarios = [ScenarioCard(user_id=user_id, **seed) for seed in SEED_SCENARIOS]
#     db.add_all(scenarios)
#     await db.flush()
#     return scenarios


async def list_scenarios(
    db: AsyncSession,
    user_id: uuid.UUID,
    include_inactive: bool = False,
    domain: str | None = None,
    category_id: uuid.UUID | None = None,
    query: str | None = None,
) -> list[ScenarioCard]:
    stmt = (
        select(ScenarioCard)
        # 2026-09-30 官方共享真题 + 本人私有场景；不含其他用户的私有场景
        .where(_visible_scenarios(user_id))
        .options(selectinload(ScenarioCard.categories))
    )
    if not include_inactive:
        stmt = stmt.where(ScenarioCard.is_active.is_(True))
    if domain:
        stmt = stmt.where(ScenarioCard.domain == domain)
    if category_id:
        category_ids = await _category_and_descendant_ids(db, category_id, user_id)
        stmt = stmt.join(ScenarioCard.categories).where(
            KnowledgeCategory.id.in_(category_ids)
        )
    if query:
        stmt = stmt.where(
            ScenarioCard.title.ilike(f"%{query}%")
            | ScenarioCard.description.ilike(f"%{query}%")
        )
    stmt = stmt.distinct().order_by(
        ScenarioCard.is_active.desc(), ScenarioCard.created_at.desc()
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_scenario(
    db: AsyncSession, scenario_id: uuid.UUID, user_id: uuid.UUID
) -> ScenarioCard | None:
    stmt = (
        select(ScenarioCard)
        .where(
            ScenarioCard.id == scenario_id,
            # 2026-09-30 放宽到官方共享，否则点共享真题进不了对话
            _visible_scenarios(user_id),
        )
        .options(selectinload(ScenarioCard.categories))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_scenario(
    db: AsyncSession, user_id: uuid.UUID, payload: ScenarioCreate
) -> ScenarioCard:
    values = payload.model_dump()
    category_ids = values.pop("category_ids", [])
    scenario = ScenarioCard(user_id=user_id, **values)
    db.add(scenario)
    await db.flush()
    if category_ids:
        # 2026-09-30 允许把自建场景挂到官方共享分类下（雅思真题类别全是共享行）
        result = await db.execute(
            select(KnowledgeCategory).where(
                _visible_categories(user_id),
                KnowledgeCategory.id.in_(category_ids),
                KnowledgeCategory.is_active.is_(True),
            )
        )
        scenario.categories = list(result.scalars().all())
    await db.commit()
    return await _reload_scenario(db, scenario.id)


async def _reload_scenario(db: AsyncSession, scenario_id: uuid.UUID) -> ScenarioCard:
    """按 id 重新查询并预加载 categories。

    2026-09-30 不能用 db.refresh()：commit() 后所有属性 expired，而 refresh()
    只重载列属性、不重载 relationship。之后读 scenario.categories 会触发
    lazy load，在 async session 下直接抛 MissingGreenlet——表现为新建/编辑
    场景返回 500。GET /scenarios 走了 selectinload 所以从没暴露这个问题。
    """
    result = await db.execute(
        select(ScenarioCard)
        .where(ScenarioCard.id == scenario_id)
        .options(selectinload(ScenarioCard.categories))
    )
    return result.scalar_one()


async def update_scenario(
    db: AsyncSession, scenario: ScenarioCard, payload: ScenarioUpdate
) -> ScenarioCard:
    if scenario.user_id is None:
        raise SharedReadOnlyError("官方题库为只读，不可修改")
    values = payload.model_dump(exclude_unset=True)
    category_ids = values.pop("category_ids", None)
    for field, value in values.items():
        setattr(scenario, field, value)
    if category_ids is not None:
        result = await db.execute(
            select(KnowledgeCategory).where(
                _visible_categories(scenario.user_id),
                KnowledgeCategory.id.in_(category_ids),
                KnowledgeCategory.is_active.is_(True),
            )
        )
        scenario.categories = list(result.scalars().all())
    await db.commit()
    return await _reload_scenario(db, scenario.id)


async def deactivate_scenario(db: AsyncSession, scenario: ScenarioCard) -> None:
    # 2026-09-30 官方共享真题不允许被停用，否则一人操作全站题库消失
    if scenario.user_id is None:
        raise SharedReadOnlyError("官方题库为只读，不可删除")
    if scenario.is_active:
        scenario.is_active = False
        await db.commit()
