import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import KnowledgeCategory
from app.models.scenario import ScenarioCard
from app.schemas.knowledge import KnowledgeCategoryCreate, KnowledgeCategoryUpdate

DEFAULT_CATEGORY_TREE = (
    ("语言", "language", ("英语", "日语", "韩语")),
    ("历史", "history", ("中国古代", "中国近现代", "世界历史")),
    ("政治", "politics", ("政治制度", "政治思想", "国际关系")),
    ("艺术", "art", ("绘画", "建筑", "表演艺术")),
    ("电影", "film", ("类型研究", "导演与作品", "视听语言")),
)


async def ensure_default_categories(db: AsyncSession, user_id: uuid.UUID) -> None:
    existing = await db.scalar(
        select(KnowledgeCategory.id)
        .where(KnowledgeCategory.user_id == user_id)
        .limit(1)
    )
    if existing is not None:
        return

    roots: dict[str, KnowledgeCategory] = {}
    for order, (name, domain, _) in enumerate(DEFAULT_CATEGORY_TREE):
        root = KnowledgeCategory(
            user_id=user_id,
            name=name,
            domain=domain,
            sort_order=order,
        )
        roots[domain] = root
        db.add(root)
    await db.flush()

    japanese_category: KnowledgeCategory | None = None
    for _, domain, children in DEFAULT_CATEGORY_TREE:
        for order, name in enumerate(children):
            category = KnowledgeCategory(
                user_id=user_id,
                parent_id=roots[domain].id,
                name=name,
                domain=domain,
                sort_order=order,
            )
            db.add(category)
            if domain == "language" and name == "日语":
                japanese_category = category
    await db.flush()
    if japanese_category is not None:
        result = await db.execute(
            select(ScenarioCard).where(
                ScenarioCard.user_id == user_id,
                ScenarioCard.domain == "language",
            )
        )
        for scenario in result.scalars().all():
            scenario.categories.append(japanese_category)
    await db.commit()


async def list_categories(
    db: AsyncSession, user_id: uuid.UUID
) -> list[KnowledgeCategory]:
    await ensure_default_categories(db, user_id)
    result = await db.execute(
        select(KnowledgeCategory)
        .where(
            KnowledgeCategory.user_id == user_id, KnowledgeCategory.is_active.is_(True)
        )
        .options(selectinload(KnowledgeCategory.scenarios))
        .order_by(KnowledgeCategory.sort_order, KnowledgeCategory.created_at)
    )
    return list(result.scalars().all())


def build_category_tree(categories: list[KnowledgeCategory]) -> list[dict]:
    by_id = {
        category.id: {
            "id": category.id,
            "name": category.name,
            "parent_id": category.parent_id,
            "domain": category.domain,
            "description": category.description,
            "sort_order": category.sort_order,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
            "children": [],
            "card_count": len(category.scenarios),
        }
        for category in categories
    }
    roots: list[dict] = []
    for category in categories:
        node = by_id[category.id]
        if category.parent_id and category.parent_id in by_id:
            by_id[category.parent_id]["children"].append(node)
        else:
            roots.append(node)

    def aggregate_card_count(node: dict) -> int:
        descendant_count = sum(
            aggregate_card_count(child) for child in node["children"]
        )
        node["card_count"] += descendant_count
        return node["card_count"]

    for root in roots:
        aggregate_card_count(root)
    return roots


async def get_category(
    db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID
) -> KnowledgeCategory | None:
    return await db.scalar(
        select(KnowledgeCategory).where(
            KnowledgeCategory.id == category_id,
            KnowledgeCategory.user_id == user_id,
        )
    )


async def create_category(
    db: AsyncSession, user_id: uuid.UUID, payload: KnowledgeCategoryCreate
) -> KnowledgeCategory:
    if payload.parent_id is not None:
        parent = await get_category(db, payload.parent_id, user_id)
        if parent is None:
            raise ValueError("父分类不存在")
    category = KnowledgeCategory(user_id=user_id, **payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession, category: KnowledgeCategory, payload: KnowledgeCategoryUpdate
) -> KnowledgeCategory:
    values = payload.model_dump(exclude_unset=True)
    if "parent_id" in values:
        parent_id = values["parent_id"]
        if parent_id == category.id:
            raise ValueError("分类不能成为自己的父分类")
        if parent_id is not None:
            parent = await get_category(db, parent_id, category.user_id)
            if parent is None:
                raise ValueError("父分类不存在")
    for field, value in values.items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


async def archive_category(db: AsyncSession, category: KnowledgeCategory) -> None:
    category.is_active = False
    await db.commit()
