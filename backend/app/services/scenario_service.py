import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ScenarioDifficulty, ScenarioLanguage
from app.models.knowledge import KnowledgeCategory
from app.models.scenario import ScenarioCard
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate

SEED_SCENARIOS = (
    {
        "title": "餐厅点餐",
        "description": "在餐厅阅读菜单、询问菜品并完成点餐。",
        "language": ScenarioLanguage.JA,
        "difficulty": ScenarioDifficulty.N4,
    },
    {
        "title": "便利店购物",
        "description": "在便利店寻找商品、询问价格并完成结账。",
        "language": ScenarioLanguage.JA,
        "difficulty": ScenarioDifficulty.N5,
    },
    {
        "title": "问路",
        "description": "向路人询问目的地并确认路线和交通方式。",
        "language": ScenarioLanguage.JA,
        "difficulty": ScenarioDifficulty.N4,
    },
    {
        "title": "自我介绍",
        "description": "介绍自己的背景、兴趣、学习目标并回应追问。",
        "language": ScenarioLanguage.JA,
        "difficulty": ScenarioDifficulty.N4,
    },
    {
        "title": "商务会议",
        "description": "在会议中表达观点、确认信息并协商下一步行动。",
        "language": ScenarioLanguage.JA,
        "difficulty": ScenarioDifficulty.N3,
    },
)


async def _category_and_descendant_ids(
    db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID
) -> list[uuid.UUID]:
    result = await db.execute(
        select(KnowledgeCategory.id, KnowledgeCategory.parent_id).where(
            KnowledgeCategory.user_id == user_id,
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


async def create_seed_scenarios(
    db: AsyncSession, user_id: uuid.UUID
) -> list[ScenarioCard]:
    scenarios = [ScenarioCard(user_id=user_id, **seed) for seed in SEED_SCENARIOS]
    db.add_all(scenarios)
    await db.flush()
    return scenarios


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
        .where(ScenarioCard.user_id == user_id)
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
            ScenarioCard.user_id == user_id,
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
        result = await db.execute(
            select(KnowledgeCategory).where(
                KnowledgeCategory.user_id == user_id,
                KnowledgeCategory.id.in_(category_ids),
                KnowledgeCategory.is_active.is_(True),
            )
        )
        scenario.categories = list(result.scalars().all())
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def update_scenario(
    db: AsyncSession, scenario: ScenarioCard, payload: ScenarioUpdate
) -> ScenarioCard:
    values = payload.model_dump(exclude_unset=True)
    category_ids = values.pop("category_ids", None)
    for field, value in values.items():
        setattr(scenario, field, value)
    if category_ids is not None:
        result = await db.execute(
            select(KnowledgeCategory).where(
                KnowledgeCategory.user_id == scenario.user_id,
                KnowledgeCategory.id.in_(category_ids),
                KnowledgeCategory.is_active.is_(True),
            )
        )
        scenario.categories = list(result.scalars().all())
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def deactivate_scenario(db: AsyncSession, scenario: ScenarioCard) -> None:
    if scenario.is_active:
        scenario.is_active = False
        await db.commit()
